"""
MarcoAI – FastAPI Application Entry Point

Responsibilities:
  - Boot the async SQLite database (create tables if missing).
  - Configure CORS to allow the React frontend (credentials=True for cookies).
  - Mount all API routers under /api/v1.
  - Expose a /health endpoint so Docker can verify the container.
"""
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.deps import get_current_user
from app.api.routes.auth import router as auth_router
from app.api.routes.calendar import router as calendar_router
from app.api.routes.gmail import router as gmail_router
from app.api.routes.chat import router as chat_router
from app.api.routes.finance import router as finance_router
from app.api.routes.llm import router as llm_router
from app.core.config import settings
from app.db.base import Base, engine
from app.db.models import User
from app.services.llm_gateway import AllProvidersExhausted, TaskTier, gateway
from sqlalchemy import text


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create all DB tables including vector tables. Shutdown: dispose the engine."""
    # 1. Ensure standard tables exist
    async with engine.begin() as conn:
        import app.db.models as _models  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)
        
        # Manual migration for finance module (Fase 7 stability)
        try:
            # Check columns in transactions
            result = await conn.execute(text("PRAGMA table_info(transactions)"))
            columns = [row[1] for row in result.fetchall()]
            
            if "created_at" not in columns:
                print("⚡ Migrating: Adding created_at to transactions...")
                # SQLite workaround: add as nullable first to avoid "non-constant default" error on some versions
                await conn.execute(text("ALTER TABLE transactions ADD COLUMN created_at DATETIME"))
            
            if "updated_at" not in columns:
                print("⚡ Migrating: Adding updated_at to transactions...")
                await conn.execute(text("ALTER TABLE transactions ADD COLUMN updated_at DATETIME"))
                
            if "deleted_at" not in columns:
                print("⚡ Migrating: Adding deleted_at to transactions...")
                await conn.execute(text("ALTER TABLE transactions ADD COLUMN deleted_at DATETIME"))
                
        except Exception as e:
            print(f"⚠️ Migration warning: {e}")
    
    # 2. Robustly create SQLite-vec virtual tables using a sync connection
    # This bypasses aiosqlite/sqlalchemy wrapper issues for extension loading.
    import sqlite3
    import sqlite_vec
    
    # Extract file path from sqlite+aiosqlite:////path/to/db
    db_url = str(settings.database_url)
    db_path = db_url.split(":///")[-1] if ":///" in db_url else "marcoai.db"
    
    try:
        with sqlite3.connect(db_path) as s_conn:
            s_conn.enable_load_extension(True)
            sqlite_vec.load(s_conn)
            s_conn.execute('''
                CREATE VIRTUAL TABLE IF NOT EXISTS vec_document_chunks USING vec0(
                    chunk_id INTEGER PRIMARY KEY,
                    embedding float[768],
                    document_id TEXT,
                    chunk_index INTEGER,
                    content TEXT
                );
            ''')
            print(f"✅ RAG Virtual tables initialized successfully at {db_path}")
    except Exception as e:
        print(f"⚠️ Warning: Could not initialize RAG tables synchronously: {e}")

    yield
    await engine.dispose()


app = FastAPI(
    title="MarcoAI – Personal AI Orchestrator",
    description=(
        "Self-hosted, privacy-first personal AI assistant "
        "running on a Raspberry Pi 3."
    ),
    version="0.2.0",
    lifespan=lifespan,
)

# ── CORS ───────────────────────────────────────────────────────────────────────
# allow_credentials=True is REQUIRED for HttpOnly cookie-based auth.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── v1 API router ──────────────────────────────────────────────────────────────
api_v1 = APIRouter(prefix="/api/v1")

# Auth
api_v1.include_router(auth_router)
# Calendar (Google Calendar CRUD)
api_v1.include_router(calendar_router)
# Chat (SSE streaming + JSON fallback)
api_v1.include_router(chat_router)
# Finance (Transacciones, balance, resumen)
api_v1.include_router(finance_router)
# LLM Gateway test
api_v1.include_router(llm_router)
# Gmail
api_v1.include_router(gmail_router)

from app.api.routes.documents import router as documents_router
from app.api.routes.habits import router as habits_router

api_v1.include_router(documents_router)
api_v1.include_router(habits_router)

app.include_router(api_v1)

# ── Health & root ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["Meta"])
async def health_check():
    return {"status": "ok", "version": app.version}


@app.get("/", tags=["Meta"])
async def root():
    return {
        "message": "MarcoAI backend is running.",
        "docs": "/docs",
    }
