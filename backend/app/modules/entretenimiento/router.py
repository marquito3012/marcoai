from fastapi import APIRouter, Depends
from typing import List
from app.database import User
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/entretenimiento", tags=["entretenimiento"])

@router.get("/radar")
def get_lanzamientos(current_user: User = Depends(get_current_user)):
    """Radar de lanzamientos de juegos o series (Mock base)"""
    return [
         {"titulo": "GTA VI", "fecha": "2026-10-15", "tipo": "juego"},
         {"titulo": "El Problema de los 3 Cuerpos Temp 2", "fecha": "2026-06-20", "tipo": "serie"}
    ]

@router.get("/ofertas")
def get_ofertas(current_user: User = Depends(get_current_user)):
    """Ofertas escrapeadas o sacadas de APIs gratuitas"""
    return [
         {"tienda": "Steam", "juego": "Hollow Knight", "precio": "7.50€", "descuento": "50%"}
    ]
