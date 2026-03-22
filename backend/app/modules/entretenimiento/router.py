from fastapi import APIRouter, Depends
from typing import List
from app.database import User
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/entretenimiento", tags=["entretenimiento"])

import json
from app.rag.engine import get_connection

@router.get("/radar")
def get_lanzamientos(current_user: User = Depends(get_current_user)):
    """Busca elementos del radar de lanzamientos de juegos o series en el cerebro"""
    radar = []
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT metadata FROM documents WHERE user_id = ?", (current_user.id,))
        rows = c.fetchall()
        for row in rows:
            meta = json.loads(row[0])
            if meta.get("tipo") == "radar" or meta.get("type") == "radar":
                radar.append({
                    "titulo": meta.get("titulo") or meta.get("nombre", "Sin título"),
                    "fecha": meta.get("fecha", "Por confirmar"),
                    "tipo": meta.get("categoria") or meta.get("tipo_radar", "interés")
                })
        conn.close()
    except Exception as e:
        print("Error fetch radar:", e)
        
    return radar

@router.get("/ofertas")
def get_ofertas(current_user: User = Depends(get_current_user)):
    """Busca ofertas guardadas en el cerebro"""
    ofertas = []
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT metadata FROM documents WHERE user_id = ?", (current_user.id,))
        rows = c.fetchall()
        for row in rows:
            meta = json.loads(row[0])
            if meta.get("tipo") == "oferta" or meta.get("type") == "oferta":
                ofertas.append({
                    "tienda": meta.get("tienda", "Internet"),
                    "juego": meta.get("juego") or meta.get("titulo", "Producto"),
                    "precio": meta.get("precio", "N/A"),
                    "descuento": meta.get("descuento", "")
                })
        conn.close()
    except Exception as e:
        print("Error fetch ofertas:", e)
        
    return ofertas
