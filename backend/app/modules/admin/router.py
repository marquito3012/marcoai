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
    ingresos_lista = []
    gastos_mensuales_lista = []
    gastos_puntuales_lista = []
    
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
            
            # --- Proceso por Tipo ---
            
            if tipo == "suscripcion":
                costo = float(meta.get("costo") or meta.get("precio") or 0.0)
                item = {
                    "nombre": meta.get("nombre") or meta.get("servicio", content),
                    "costo": costo,
                    "renovacion": meta.get("renovacion") or meta.get("fecha", "Mensual")
                }
                suscripciones.append(item)
                # Las suscripciones son gastos mensuales
                total_gastos_mensuales += costo
                gastos_mensuales_lista.append({"content": item["nombre"], "amount": costo})

            elif tipo == "ingreso":
                monto = float(meta.get("monto") or meta.get("cantidad") or 0.0)
                total_ingresos += monto
                ingresos_lista.append({"content": meta.get("content") or content, "amount": monto})
            
            elif tipo == "gasto-mensual":
                monto = float(meta.get("amount") or meta.get("monto") or 0.0)
                total_gastos_mensuales += monto
                gastos_mensuales_lista.append({"content": content, "amount": monto})
            
            elif tipo == "gasto-puntual":
                if created_at.startswith(now_prefix):
                    monto = float(meta.get("amount") or meta.get("monto") or 0.0)
                    total_gastos_puntuales += monto
                    gastos_puntuales_lista.append({"content": content, "amount": monto})
            
            # --- Compatibilidad ---
            elif tipo == "presupuesto":
                monto = float(meta.get("restante") or 0.0)
                total_ingresos += monto
                ingresos_lista.append({"content": "Ajuste presupuesto base", "amount": monto})
            elif tipo == "beneficio":
                monto = float(meta.get("monto") or 0.0)
                total_ingresos += monto
                ingresos_lista.append({"content": content, "amount": monto})
            elif tipo == "gasto":
                if created_at.startswith(now_prefix):
                    monto = float(meta.get("amount") or meta.get("monto") or 0.0)
                    total_gastos_puntuales += monto
                    gastos_puntuales_lista.append({"content": content, "amount": monto})

        conn.close()
    except Exception as e:
        print("Error fetch admin dashboard refactored:", e)
        
    presupuesto_final = total_ingresos - total_gastos_mensuales - total_gastos_puntuales
    
    return {
        "presupuesto_restante": presupuesto_final,
        "suscripciones": suscripciones,
        "detalles": {
            "ingresos": {"total": total_ingresos, "items": ingresos_lista},
            "gastos_mensuales": {"total": total_gastos_mensuales, "items": gastos_mensuales_lista},
            "gastos_puntuales": {"total": total_gastos_puntuales, "items": gastos_puntuales_lista}
        }
    }
