import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.auth.dependencies import get_current_user
import unittest.mock

# Mock de la autenticación para que siempre devuelva el mock_user
async def mock_get_current_user():
    return {"id": 1, "username": "testuser"}

@pytest.fixture
def override_auth():
    app.dependency_overrides[get_current_user] = mock_get_current_user
    yield
    app.dependency_overrides.clear()

def test_get_habitos_endpoint(client, override_auth):
    # Mockeamos la respuesta de get_habitos del motor RAG
    with unittest.mock.patch("app.rag.engine.get_habitos") as mock_get:
        mock_get.return_value = [{"nombre": "Correr", "completado": False}]
        
        response = client.get("/api/lifestyle/habitos")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["nombre"] == "Correr"

def test_toggle_habito_endpoint(client, override_auth):
    # Mockeamos toggle_habit
    with unittest.mock.patch("app.rag.engine.toggle_habit") as mock_toggle:
        mock_toggle.return_value = True
        
        response = client.post("/api/lifestyle/habitos/toggle", json={"nombre": "Correr"})
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["completado"] is True

def test_toggle_habito_missing_name(client, override_auth):
    response = client.post("/api/lifestyle/habitos/toggle", json={})
    assert response.status_code == 200 # El router devuelve 200 con error en JSON
    assert "error" in response.json()
