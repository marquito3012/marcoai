"""
Memory-efficient SQLite database with sqlite-vec support.
Optimized for Raspberry Pi 3 (1GB RAM) with minimal connection pooling.
"""
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

from .config import Settings, get_settings


class DatabaseManager:
    """
    Singleton database manager with lazy initialization.
    Uses a single connection per thread to minimize memory overhead.
    """

    _instance: Optional["DatabaseManager"] = None
    _lock = threading.Lock()
    _local = threading.local()

    def __new__(cls) -> "DatabaseManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_initialized"):
            self._settings = get_settings()
            self._db_path = Path(self._settings.data_dir) / "marcoai.db"
            self._initialized = True

    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local connection with optimized settings."""
        if not hasattr(self._local, "connection") or self._local.connection is None:
            self._local.connection = sqlite3.connect(
                str(self._db_path),
                check_same_thread=False,
                isolation_level=None,  # Autocommit mode
            )
            # Memory-efficient PRAGMA settings
            conn = self._local.connection
            conn.execute("PRAGMA journal_mode=WAL")  # Better concurrency
            conn.execute(f"PRAGMA cache_size=-{self._settings.sqlite_cache_size}")  # 2MB cache
            conn.execute("PRAGMA temp_store=MEMORY")  # Store temp tables in RAM
            conn.execute("PRAGMA synchronous=NORMAL")  # Balance safety/speed
            conn.execute("PRAGMA foreign_keys=ON")
            conn.row_factory = sqlite3.Row  # Dict-like rows
        return self._local.connection

    @contextmanager
    def connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager for database connections."""
        conn = self._get_connection()
        try:
            yield conn
        except Exception as e:
            conn.rollback()
            raise e

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager for transactions with automatic commit/rollback."""
        conn = self._get_connection()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e

    def init_schema(self) -> None:
        """Initialize database schema - idempotent."""
        with self.connection() as conn:
            # Enable sqlite-vec extension
            conn.enable_load_extension(True)
            try:
                conn.execute("SELECT load_extension('sqlite_vec')")
            except sqlite3.OperationalError:
                # sqlite-vec not available, continue without RAG
                pass
            finally:
                conn.enable_load_extension(False)

            # Core tables
            conn.executescript(SCHEMA_SQL)


# Global schema SQL - memory optimized with minimal indexes
SCHEMA_SQL = """
-- Users table (required for multi-user isolation)
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    google_sub TEXT UNIQUE,
    created_at TEXT DEFAULT (datetime('now')),
    last_active TEXT DEFAULT (datetime('now'))
);

-- RAG: Conversation history with vector embeddings
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    embedding BLOB,  -- sqlite-vec vector (384 float32 = 1536 bytes)
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_created ON conversations(created_at);

-- Finance: Expenses and income
CREATE TABLE IF NOT EXISTS finance_transactions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('expense', 'income')),
    category TEXT NOT NULL,
    amount REAL NOT NULL,
    description TEXT,
    date TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_finance_user ON finance_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_finance_date ON finance_transactions(date);
CREATE INDEX IF NOT EXISTS idx_finance_type ON finance_transactions(type);

-- Habits: Binary habit tracking with streaks
CREATE TABLE IF NOT EXISTS habits (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    frequency TEXT NOT NULL,  -- JSON: {"type": "daily"|"weekdays", "days": [0,1,2]}
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_habits_user ON habits(user_id);

CREATE TABLE IF NOT EXISTS habit_completions (
    id TEXT PRIMARY KEY,
    habit_id TEXT NOT NULL,
    date TEXT NOT NULL,
    completed INTEGER NOT NULL DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (habit_id) REFERENCES habits(id) ON DELETE CASCADE,
    UNIQUE(habit_id, date)
);
CREATE INDEX IF NOT EXISTS idx_habit_completions_habit ON habit_completions(habit_id);
CREATE INDEX IF NOT EXISTS idx_habit_completions_date ON habit_completions(date);

-- Food: Shopping list
CREATE TABLE IF NOT EXISTS shopping_list (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    item TEXT NOT NULL,
    quantity TEXT,
    purchased INTEGER NOT NULL DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_shopping_user ON shopping_list(user_id);

-- Food: Meal plan
CREATE TABLE IF NOT EXISTS meal_plan (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    week_start DATE NOT NULL,
    day INTEGER NOT NULL CHECK (day BETWEEN 0 AND 6),  -- 0=Monday, 6=Sunday
    meal_type TEXT NOT NULL CHECK (meal_type IN ('breakfast', 'lunch', 'dinner', 'snack')),
    description TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(user_id, week_start, day, meal_type)
);
CREATE INDEX IF NOT EXISTS idx_meal_plan_user ON meal_plan(user_id);

-- Leisure: Events to attend
CREATE TABLE IF NOT EXISTS leisure_events (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    event_date TEXT NOT NULL,
    location TEXT,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_leisure_user ON leisure_events(user_id);
CREATE INDEX IF NOT EXISTS idx_leisure_date ON leisure_events(event_date);

-- Leisure: Tracked game deals
CREATE TABLE IF NOT EXISTS game_deals (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    title TEXT NOT NULL,
    store TEXT NOT NULL,
    price REAL NOT NULL,
    discount_percent INTEGER,
    url TEXT,
    checked_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_game_deals_user ON game_deals(user_id);

-- Memory: User preferences (lightweight key-value store)
CREATE TABLE IF NOT EXISTS user_preferences (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,  -- JSON-encoded
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(user_id, key)
);
CREATE INDEX IF NOT EXISTS idx_preferences_user ON user_preferences(user_id);
"""


def get_db() -> Generator[DatabaseManager, None, None]:
    """Dependency injection for database connections."""
    db = DatabaseManager()
    try:
        yield db
    finally:
        pass  # Connection persists in thread-local storage
