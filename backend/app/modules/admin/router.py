from fastapi import APIRouter, Depends
from typing import List
from app.database import User
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/admin", tags=["admin"])

import json
from app.rag.engine import get_connection

@router.get("/dashboard")
def get_admin_dashboard(current_user: User = Depends(get_current_user)):
    """Busca suscripciones y presupuesto en el cerebro"""
    suscripciones = []
    presupuesto_restante = 0.0
    presupuesto_encontrado = False
    
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT metadata FROM documents WHERE user_id = ?", (current_user.id,))
        rows = c.fetchall()
        for row in rows:
            meta = json.loads(row[0])
            if meta.get("tipo") == "suscripcion" or meta.get("type") == "suscripcion":
                suscripciones.append({
                    "nombre": meta.get("nombre") or meta.get("servicio", "Servicio Desconocido"),
                    "costo": meta.get("costo") or meta.get("precio", 0.0),
                    "renovacion": meta.get("renovacion") or meta.get("fecha", "Desconocida")
                })
            elif meta.get("tipo") in ["ingreso", "beneficio"]:
                val = meta.get("monto") or meta.get("cantidad") or meta.get("valor")
                if val is not None:
                    try:
                        presupuesto_restante += float(val)
                        presupuesto_encontrado = True
                    except ValueError:
                        pass
            elif meta.get("tipo") == "presupuesto" or meta.get("type") == "presupuesto":
                val = meta.get("restante") or meta.get("cantidad") or meta.get("presupuesto")
                if val is not None:
                    try:
                        presupuesto_restante += float(val)
                        presupuesto_encontrado = True
                    except ValueError:
                        pass
        
        # RESTAR suscripciones del presupuesto restante si hay presupuesto o ingresos
        if presupuesto_encontrado:
            total_subs = sum(float(s["costo"]) for s in suscripciones)
            presupuesto_restante -= total_subs

        conn.close()
    except Exception as e:
        print("Error fetch admin:", e)
        
    return {
        "suscripciones": suscripciones,
        "presupuesto_restante": presupuesto_restante if presupuesto_encontrado else None
    }
