from fastapi import APIRouter, Depends
from typing import List
from app.database import User
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/dashboard")
def get_admin_dashboard(current_user: User = Depends(get_current_user)):
    """Resumen administrativo: Suscripciones, Presupuesto (Mocks por ahora)"""
    return {
        "suscripciones": [
             {"nombre": "Netflix", "costo": 15.99, "renovacion": "2026-04-01"},
             {"nombre": "Google One", "costo": 1.99, "renovacion": "2026-03-25"}
        ],
        "presupuesto_restante": 1250.00
    }
