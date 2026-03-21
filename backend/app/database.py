from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
from app.config import settings
from typing import Optional

# Evitar que SQLAlchemy se queje de thread-safety con SQLite (en FastAPI cada worker tiene su propia conexión, pero por si acaso disable check_same_thread)
engine = create_engine(
    settings.DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Modelos DB
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    google_id = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    picture = Column(String)
    # Tokens de API para acceder a sus recursos
    google_access_token = Column(String, nullable=True)
    google_refresh_token = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Note(Base):
    __tablename__ = "notes"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
class EventCache(Base):
    __tablename__ = "event_cache"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    event_id = Column(String, index=True)
    summary = Column(String)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    # Guardamos el JSON crudo por si necesitamos campos originales
    raw_data = Column(JSON)
    synced_at = Column(DateTime, default=datetime.utcnow)

# NOTA: La tabla vectorial para el RAG de SQLite se creará/administrará
# mediante queries raw en sqlite3 / sqlite_utils dado que SQLAlchemy 
# no soporta nativamente la extensión vss.

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    # Crea las tablas de SQLAlchemy
    Base.metadata.create_all(bind=engine)
