import pytest
import os
import sqlite3
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db

# Mock de base de datos para pruebas
@pytest.fixture(scope="session")
def test_db():
    # Usamos una ruta relativa dentro del proyecto para evitar líos de permisos en /tmp
    db_path = os.path.join(os.getcwd(), "data", "test_marcoai.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    if os.path.exists(db_path):
        os.remove(db_path)
    
    # IMPORTANTE: Configuramos la URL de la base de datos ANTES de importar app.main
    from app.config import settings
    settings.DATABASE_URL = f"sqlite:///{db_path}"
    
    # Ahora importamos e inicializamos
    from app.rag.engine import init_rag_db
    import app.rag.engine
    app.rag.engine.DB_PATH = db_path
    
    from app.database import init_db
    
    init_rag_db() # Motor RAG (tablas raw)
    init_db()     # SQLAlchemy (tablas modelos)
    
    yield db_path
    
    if os.path.exists(db_path):
        os.remove(db_path)

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture
def mock_user():
    return {"id": 1, "username": "testuser", "email": "test@example.com"}
