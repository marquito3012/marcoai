from fastapi import APIRouter, Depends
from typing import List
from app.database import User
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/lifestyle", tags=["lifestyle"])

import json
from app.rag.engine import get_connection

@router.get("/comidas")
def get_meal_plan(current_user: User = Depends(get_current_user)):
    """Busca comidas o dieta en el cerebro del usuario."""
    comidas = []
    lista_compra = []
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT metadata FROM documents WHERE user_id = ?", (current_user.id,))
        rows = c.fetchall()
        for row in rows:
            meta = json.loads(row[0])
            if meta.get("tipo") == "comida" or meta.get("type") == "comida":
                comidas.append(meta.get("nombre") or meta.get("titulo") or "Comida guardada")
            elif meta.get("tipo") == "compra" or meta.get("type") == "compra":
                items = meta.get("items")
                if isinstance(items, list):
                     lista_compra.extend(items)
                else:
                     lista_compra.append(meta.get("nombre", "Artículo de compra"))
        conn.close()
    except Exception as e:
        print("Error fetch comidas:", e)

    return {
        "comidas": comidas,
        "lista_compra": lista_compra
    }
    
@router.get("/habitos")
async def get_habitos_endpoint(current_user: User = Depends(get_current_user)):
    """Recupera hábitos del Cerebro del usuario."""
    from app.rag.engine import get_habitos as db_get_habitos
    try:
        habitos = await db_get_habitos(current_user.id)
        return habitos
    except Exception as e:
        print(f"❌ ERROR get_habitos: {e}")
        return []
        print("Error fetch habitos:", e)
        
    return habitos

@router.post("/habitos/toggle")
async def toggle_habito_endpoint(req: dict, current_user: User = Depends(get_current_user)):
    """Endpoint para alternar el estado de un hábito."""
    from app.rag.engine import toggle_habit
    habit_name = req.get("nombre")
    if not habit_name:
        return {"error": "Falta el nombre del hábito"}
    
    new_state = await toggle_habit(current_user.id, habit_name)
    return {"success": True, "completado": new_state}
