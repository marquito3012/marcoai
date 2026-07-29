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
    
    # Unwrap SQLAlchemy's AdaptedConnection → aiosqlite.Connection → sqlite3.Connection
    raw = dbapi_connection
    for attr in ("_connection", "_conn"):
        if hasattr(raw, attr):
            inner = getattr(raw, attr)
            if inner is not None and inner is not raw:
                raw = inner
    # Now `raw` should be the sqlite3.Connection (or aiosqlite.Connection)
    try:
        if hasattr(raw, "enable_load_extension"):
            raw.enable_load_extension(True)
            sqlite_vec.load(raw)
            raw.enable_load_extension(False)
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
