"""
MarcoAI – Async SQLAlchemy engine configured for SQLite + WAL mode.

WAL (Write-Ahead Logging) allows concurrent reads while writes are in
progress and dramatically reduces SD card wear compared to the default
DELETE journal mode.
"""
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# ── Engine ────────────────────────────────────────────────────────────────────
engine = create_async_engine(
    settings.database_url,
    echo=False,          # set True temporarily to debug SQL
    future=True,
    connect_args={
        "check_same_thread": False,
        "timeout": 20,
    },
)


@event.listens_for(engine.sync_engine, "connect")
def _set_sqlite_pragmas(dbapi_connection, _connection_record):
    """Enable WAL mode, other optimisations, and vector extensions on every new connection."""
    import sqlite_vec
    
    # In SQLAlchemy 2.0 with aiosqlite, dbapi_connection is an AsyncAdapt wrapper.
    # We need to find the underlying sqlite3.Connection to load the extension.
    raw_conn = dbapi_connection
    
    # Aggressively unwrap to find the true sqlite3.Connection
    # This handles both _ConnectionFairy and AsyncAdapt/aiosqlite wrappers
    visited = set()
    while raw_conn not in visited:
        visited.add(raw_conn)
        found = False
        for attr in ["dbapi_connection", "_connection", "connection"]:
            if hasattr(raw_conn, attr):
                inner = getattr(raw_conn, attr)
                if inner is not None and inner is not raw_conn:
                    raw_conn = inner
                    found = True
                    break
        if not found:
            break
    
    try:
        # Check if we finally found a real sqlite3 connection (or something that looks like it)
        if hasattr(raw_conn, "enable_load_extension"):
            raw_conn.enable_load_extension(True)
            sqlite_vec.load(raw_conn)
            raw_conn.enable_load_extension(False)
    except Exception:
        pass

    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA synchronous=NORMAL;")   # safe & faster than FULL
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.execute("PRAGMA cache_size=-8000;")      # 8 MB page cache
    cursor.execute("PRAGMA temp_store=MEMORY;")    # temp tables in RAM
    cursor.close()


# ── Session factory ───────────────────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


# ── Base model for all ORM tables ─────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ── FastAPI dependency ────────────────────────────────────────────────────────
async def get_db() -> AsyncSession:
    """Yield a database session; auto-closes when the request finishes."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
