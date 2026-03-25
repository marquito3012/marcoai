from fastapi import APIRouter, Depends
from typing import List
from app.database import User
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/admin", tags=["admin"])

import json
from app.rag.engine import get_connection

@router.get("/dashboard")
def get_admin_dashboard(current_user: User = Depends(get_current_user)):
    """Busca suscripciones y balance basado en: gasto-mensual, gasto-puntual e ingreso"""
    suscripciones = []
    lista_ingresos = []
    lista_gastos_mensuales = []
    lista_gastos_puntuales = []
    
    total_ingresos = 0.0
    total_gastos_mensuales = 0.0
    total_gastos_puntuales = 0.0
    
    from datetime import datetime
    now_prefix = datetime.now().strftime("%Y-%m")
    
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT content, metadata, created_at FROM documents WHERE user_id = ?", (current_user.id,))
        rows = c.fetchall()
        for row in rows:
            content = row[0]
            meta = json.loads(row[1])
            created_at = row[2] or ""
            tipo = meta.get("tipo") or meta.get("type")
            
            # 1. Suscripciones
            if tipo == "suscripcion":
                costo = float(meta.get("costo") or meta.get("precio") or 0.0)
                entry = {
                    "nombre": meta.get("nombre") or meta.get("servicio", content),
                    "costo": costo,
                    "renovacion": meta.get("renovacion") or meta.get("fecha", "Mensual")
                }
                suscripciones.append(entry)
                total_gastos_mensuales += costo
                lista_gastos_mensuales.append(entry)

            # 2. Ingresos
            elif tipo == "ingreso":
                monto = float(meta.get("monto") or meta.get("cantidad") or 0.0)
                total_ingresos += monto
                lista_ingresos.append({"nombre": content, "monto": monto})
            
            # 3. Gastos Mensuales
            elif tipo == "gasto-mensual":
                monto = float(meta.get("amount") or meta.get("monto") or 0.0)
                total_gastos_mensuales += monto
                lista_gastos_mensuales.append({"nombre": content, "costo": monto})
            
            # 4. Gastos Puntuales (Solo del mes actual)
            elif tipo == "gasto-puntual":
                if created_at.startswith(now_prefix):
                    monto = float(meta.get("amount") or meta.get("monto") or 0.0)
                    total_gastos_puntuales += monto
                    lista_gastos_puntuales.append({"nombre": content, "costo": monto})
            
            # --- Compatibilidad ---
            elif tipo == "presupuesto":
                total_ingresos += float(meta.get("restante") or 0.0)
            elif tipo == "beneficio":
                total_ingresos += float(meta.get("monto") or 0.0)
            elif tipo == "gasto" and created_at.startswith(now_prefix):
                total_gastos_puntuales += float(meta.get("amount") or meta.get("monto") or 0.0)

        conn.close()
    except Exception as e:
        print("Error fetch admin dashboard refactored:", e)
        
    presupuesto_final = total_ingresos - total_gastos_mensuales - total_gastos_puntuales
    
    return {
        "presupuesto_restante": presupuesto_final,
        "detalles": {
            "ingresos": { "total": total_ingresos, "items": lista_ingresos },
            "gastos_mensuales": { "total": total_gastos_mensuales, "items": lista_gastos_mensuales },
            "gastos_puntuales": { "total": total_gastos_puntuales, "items": lista_gastos_puntuales }
        },
        "suscripciones": suscripciones # Legacy support just in case
    }
