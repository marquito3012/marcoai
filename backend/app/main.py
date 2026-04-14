"""
MarcoAI – FastAPI Application Entry Point

Responsibilities:
  - Boot the async SQLite database (create tables if missing).
  - Configure CORS to allow the React frontend.
  - Mount all API routers under /api/v1.
  - Expose a /health endpoint so Docker can verify the container.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.db.base import Base, engine

# ── Future routers will be imported and included here ─────────────────────────
# from app.api.routes import auth, chat, finance, calendar, mail, files, habits


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create DB tables. Shutdown: dispose engine."""
    async with engine.begin() as conn:
        # Import models so metadata is populated before create_all
        import app.db.models as _models  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="MarcoAI – Personal AI Orchestrator",
    description="Self-hosted, privacy-first AI assistant running on a Raspberry Pi 3.",
    version="0.1.0",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["Meta"])
async def health_check():
    return {"status": "ok", "version": app.version}


# ── Root ─────────────────────────────────────────────────────────────────────
@app.get("/", tags=["Meta"])
async def root():
    return {"message": "MarcoAI backend is running. Use /docs for the API explorer."}
