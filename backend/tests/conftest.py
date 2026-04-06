"""
Pytest configuration and fixtures.
Memory-efficient test setup.
"""
import pytest
from unittest.mock import Mock, MagicMock
from contextlib import contextmanager
import sqlite3


class MockDatabaseManager:
    """
    Mock DatabaseManager for testing.
    Wraps a raw sqlite3.Connection with the expected interface.
    """
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    @contextmanager
    def connection(self):
        """Context manager for connections."""
        yield self._conn

    @contextmanager
    def transaction(self):
        """Context manager for transactions with automatic commit/rollback."""
        try:
            yield self._conn
            self._conn.commit()
        except Exception as e:
            self._conn.rollback()
            raise e


@pytest.fixture
def mock_db():
    """Create an in-memory SQLite database for testing."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    # Create minimal schema for tests
    conn.executescript("""
        CREATE TABLE users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL
        );

        CREATE TABLE finance_transactions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            type TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            description TEXT,
            date TEXT NOT NULL
        );

        CREATE TABLE habits (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            frequency TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE habit_completions (
            id TEXT PRIMARY KEY,
            habit_id TEXT NOT NULL,
            date TEXT NOT NULL,
            completed INTEGER NOT NULL DEFAULT 1,
            UNIQUE(habit_id, date)
        );

        CREATE TABLE shopping_list (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            item TEXT NOT NULL,
            quantity TEXT,
            purchased INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE conversations (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            embedding BLOB
        );
    """)

    # Wrap in MockDatabaseManager to provide .transaction() and .connection() methods
    mock_db_manager = MockDatabaseManager(conn)

    yield mock_db_manager

    conn.close()


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    from unittest.mock import MagicMock
    settings = MagicMock()
    settings.llm_api_order = ["groq"]
    settings.groq_api_key = "test-key"
    settings.max_memory_mb = 512
    return settings


@pytest.fixture
def sample_user():
    """Sample user data for tests."""
    return {
        "id": "test-user-123",
        "email": "test@example.com",
    }
