from fastapi import APIRouter, Depends
from typing import List
from app.database import User
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/lifestyle", tags=["lifestyle"])

@router.get("/comidas")
def get_meal_plan(current_user: User = Depends(get_current_user)):
    """Plan de comidas de la semana (Mock base)"""
    return {
        "lunes": "Pollo a la plancha con arroz",
        "martes": "Ensalada de Atún",
        "lista_compra": ["Pollo", "Arroz", "Atún", "Lechuga"]
    }
    
@router.get("/habitos")
def get_habitos(current_user: User = Depends(get_current_user)):
    """Seguimiento de hábitos diarios"""
    return [
         {"nombre": "Leer 30 mins", "completado": True},
         {"nombre": "Beber 2L Agua", "completado": False}
    ]
