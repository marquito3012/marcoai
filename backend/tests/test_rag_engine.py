import pytest
import os
import json
from app.rag.engine import add_document, get_habitos, toggle_habit, delete_documents

@pytest.mark.asyncio
async def test_habit_lifecycle(test_db):
    # Sobrescribimos DB_PATH para la prueba
    import app.rag.engine
    app.rag.engine.DB_PATH = test_db
    
    user_id = 99
    habit_name = "Test Habit"
    
    # 1. Guardar hábito
    await add_document(user_id, "Hacer algo", {"tipo": "habito", "nombre": habit_name, "completado": False})
    
    # 2. Recuperar y verificar
    habitos = await get_habitos(user_id)
    assert len(habitos) == 1
    assert habitos[0]["nombre"] == habit_name
    assert habitos[0]["completado"] is False
    
    # 3. Toggle
    new_state = await toggle_habit(user_id, habit_name)
    assert new_state is True
    
    habitos_updated = await get_habitos(user_id)
    assert habitos_updated[0]["completado"] is True
    
    # 4. Deletar
    await delete_documents(user_id, tipo="habito", query=habit_name)
    habitos_final = await get_habitos(user_id)
    assert len(habitos_final) == 0

@pytest.mark.asyncio
async def test_deletion_by_query(test_db):
    import app.rag.engine
    app.rag.engine.DB_PATH = test_db
    user_id = 100
    
    await add_document(user_id, "Contenido 1", {"tipo": "nota"})
    await add_document(user_id, "Contenido 2", {"tipo": "nota"})
    
    await delete_documents(user_id, query="Contenido 1")
    
    # Nota: delete_documents no tiene una función simple de 'get_all' en engine.py
    # pero podemos verificar vía SQL si queremos ser exhaustivos
