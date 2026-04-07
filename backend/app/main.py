"""
Marco AI - FastAPI Application Entry Point
Memory-efficient modular monolith for Raspberry Pi 3
"""
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .database import DatabaseManager, get_db

# Import module routers
from .modules.calendar.router import router as calendar_router
from .modules.finance.router import router as finance_router
from .modules.habits.router import router as habits_router
from .modules.food.router import router as food_router
from .modules.leisure.router import router as leisure_router
from .modules.rag.router import router as rag_router
from .auth.router import router as auth_router

# Configure logging for low overhead
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan manager with minimal overhead."""
    # Startup
    settings = get_settings()
    logger.info(f"Starting {settings.app_name}...")

    # Initialize database
    db = DatabaseManager()
    db.init_schema()
    logger.info("Database initialized")

    yield

    # Shutdown (cleanup if needed)
    logger.info("Shutting down...")


# Create FastAPI app with minimal middleware
app = FastAPI(
    title="Marco AI",
    description="Personal AI Assistant for Raspberry Pi",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Include module routers
app.include_router(auth_router)          # /auth/login, /auth/callback, /auth/me
app.include_router(calendar_router, prefix="/api")
app.include_router(finance_router, prefix="/api")
app.include_router(habits_router, prefix="/api")
app.include_router(food_router, prefix="/api")
app.include_router(leisure_router, prefix="/api")
app.include_router(rag_router, prefix="/api")

# Serve static frontend assets (CSS, JS)
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# Health check - minimal
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# Chat endpoint - main interaction point
@app.post("/api/chat")
async def chat(request: Request):
    """
    Main chat endpoint with tool-calling orchestrator.
    Memory-efficient: streams response, no history buffering.
    """
    from .agent.orchestrator import ReActOrchestrator

    try:
        body = await request.json()
        user_input = body.get("message", "")
        user_id = body.get("user_id")

        if not user_id:
            raise HTTPException(status_code=400, detail="user_id required")

        if not user_input:
            raise HTTPException(status_code=400, detail="message required")

        # Process through orchestrator
        db = next(get_db())
        orchestrator = ReActOrchestrator(db=db)
        response = await orchestrator.process(
            user_input=user_input,
            user_id=user_id,
        )

        return JSONResponse(content=response)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"}
        )


# Root endpoint — serve the SPA (requires auth)
@app.get("/")
async def root(request: Request):
    """Root endpoint — redirects to /auth/login if not authenticated."""
    from .auth.router import get_session
    if not get_session(request):
        return RedirectResponse(url="/auth/login")
    return FileResponse(str(STATIC_DIR / "index.html"))
