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
    total_ingresos = 0.0
    total_gastos_mensuales = 0.0
    total_gastos_puntuales = 0.0
    
    from datetime import datetime
    now_prefix = datetime.now().strftime("%Y-%m")
    
    try:
        conn = get_connection()
        c = conn.cursor()
        # Traemos metadata y fecha de creación
        c.execute("SELECT metadata, created_at FROM documents WHERE user_id = ?", (current_user.id,))
        rows = c.fetchall()
        for row in rows:
            meta = json.loads(row[0])
            created_at = row[1] or ""
            tipo = meta.get("tipo") or meta.get("type")
            
            # 1. Suscripciones (para la lista UI)
            if tipo == "suscripcion":
                costo = float(meta.get("costo") or meta.get("precio") or 0.0)
                suscripciones.append({
                    "nombre": meta.get("nombre") or meta.get("servicio", "Desconocido"),
                    "costo": costo,
                    "renovacion": meta.get("renovacion") or meta.get("fecha", "Mensual")
                })
                # Las suscripciones cuentan como gasto mensual automáticamente
                total_gastos_mensuales += costo

            # 2. Ingresos
            elif tipo == "ingreso":
                total_ingresos += float(meta.get("monto") or meta.get("cantidad") or 0.0)
            
            # 3. Gastos Mensuales
            elif tipo == "gasto-mensual":
                total_gastos_mensuales += float(meta.get("amount") or meta.get("monto") or 0.0)
            
            # 4. Gastos Puntuales (Solo del mes actual)
            elif tipo == "gasto-puntual":
                if created_at.startswith(now_prefix):
                    total_gastos_puntuales += float(meta.get("amount") or meta.get("monto") or 0.0)
            
            # --- Compatibilidad con tipos antiguos ---
            elif tipo == "presupuesto":
                total_ingresos += float(meta.get("restante") or 0.0)
            elif tipo == "beneficio":
                total_ingresos += float(meta.get("monto") or 0.0)
            elif tipo == "gasto":
                if created_at.startswith(now_prefix):
                    total_gastos_puntuales += float(meta.get("amount") or meta.get("monto") or 0.0)

        conn.close()
    except Exception as e:
        print("Error fetch admin dashboard refactored:", e)
        
    presupuesto_final = total_ingresos - total_gastos_mensuales - total_gastos_puntuales
    
    return {
        "suscripciones": suscripciones,
        "presupuesto_restante": presupuesto_final,
        "detalles": {
            "ingresos": total_ingresos,
            "gastos_mensuales": total_gastos_mensuales,
            "gastos_puntuales": total_gastos_puntuales
        }
    }
