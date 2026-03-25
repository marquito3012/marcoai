from fastapi import APIRouter, Depends
from typing import Dict, Any
import datetime
import json
from app.database import User
from app.auth.dependencies import get_current_user
from app.services.google_calendar import list_upcoming_events
from app.services.google_gmail import list_unread_messages
from app.rag.engine import get_connection

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/summary")
def get_dashboard_summary(current_user: User = Depends(get_current_user)):
    """Obtiene el resumen dinámico para el dashboard del usuario actual"""
    summary = {
        "evento": None,
        "correos": {"total": 0, "alta_prioridad": 0},
        "habitos": [],
        "radar": [],
        "mensaje_agente": "¡Bienvenido! Soy Marco, tu agente personal."
    }

    # Próximo Evento (Calendar)
    try:
        events = list_upcoming_events(current_user, max_results=1)
        if events:
            ev = events[0]
            # La fecha puede venir en dateTime o en date (todo el día)
            time_str = ev.get('start', {}).get('dateTime', ev.get('start', {}).get('date', ''))
            summary["evento"] = {"titulo": ev.get('summary', 'Evento'), "hora": time_str}
    except Exception as e:
        print(f"Error fetch calendar: {e}")

    # Correos (Gmail)
    try:
        messages = list_unread_messages(current_user, max_results=10)
        summary["correos"]["total"] = len(messages) if messages else 0
        # Simular correos de alta prioridad
        summary["correos"]["alta_prioridad"] = min(len(messages), 2)
    except Exception as e:
        print(f"Error fetch gmail: {e}")

    # Hábitos y Radar desde RAG (sqlite documents)
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT metadata FROM documents WHERE user_id = ?", (current_user.id,))
        rows = c.fetchall()
        for row in rows:
            meta = json.loads(row[0])
            if meta.get("tipo") == "habito" or meta.get("type") == "habito":
                summary["habitos"].append(meta)
            elif meta.get("tipo") == "radar" or meta.get("type") == "radar":
                summary["radar"].append(meta)
        conn.close()
    except Exception as e:
        print(f"Error fetch VSS metadata: {e}")

    # Construcción de mensaje inteligente
    if summary["evento"]:
        # Formatear la fecha para el mensaje (ej: "lunes 23")
        fecha_obj = datetime.datetime.fromisoformat(summary["evento"]["hora"].replace("Z", "+00:00"))
        dias_es = {"Monday": "lunes", "Tuesday": "martes", "Wednesday": "miércoles", 
                   "Thursday": "jueves", "Friday": "viernes", "Saturday": "sábado", "Sunday": "domingo"}
        dia_semana = dias_es.get(fecha_obj.strftime("%A"), fecha_obj.strftime("%A"))
        fecha_str = f"{dia_semana} {fecha_obj.day:02}"
        summary["mensaje_agente"] = f"¡Hola! Tienes el buzón con {summary['correos']['total']} correos nuevos. Tu siguiente compromiso es '{summary['evento']['titulo']}' para el {fecha_str}."
    else:
        summary["mensaje_agente"] = f"¡Hola! Agenda libre por ahora. Aprovecha para ponerte al día con tus {summary['correos']['total']} correos."

    return summary
