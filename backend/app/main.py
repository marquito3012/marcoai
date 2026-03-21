from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db
from app.rag.engine import init_rag_db

from app.auth import router as auth_router
from app.agents import router as agent_router
from app.modules.tiempo import router as tiempo_router
from app.modules.conocimiento import router as conocimiento_router
from app.modules.admin import router as admin_router
from app.modules.lifestyle import router as lifestyle_router
from app.modules.entretenimiento import router as entretenimiento_router

# Configuración Inicial
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Agente Personal Multiusuario para RPi3"
)

app.include_router(auth_router.router, prefix="/api")
app.include_router(agent_router.router, prefix="/api")
app.include_router(tiempo_router.router, prefix="/api")
app.include_router(conocimiento_router.router, prefix="/api")
app.include_router(admin_router.router, prefix="/api")
app.include_router(lifestyle_router.router, prefix="/api")
app.include_router(entretenimiento_router.router, prefix="/api")


# CORS
origins = [
    settings.FRONTEND_URL,
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    init_db()
    init_rag_db()
    print("Base de datos inicializada o verificada.")

@app.get("/")
def read_root():
    return {"message": "Marco AI Backend is running."}

@app.get("/health")
def health_check():
    return {"status": "ok"}
