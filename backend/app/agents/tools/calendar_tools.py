"""
MarcoAI – Calendar Tools for LangGraph Agent (Fase 6)
══════════════════════════════════════════════════════════════════════════════

Herramientas que el Agente de Calendario puede invocar para realizar
operaciones CRUD sobre Google Calendar.

Cada herramienta es una función async decorada con @tool de LangChain.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from langchain_core.tools import tool
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.services.calendar_service import CalendarService

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
#  Helper para obtener el servicio de calendario
# ══════════════════════════════════════════════════════════════════════════════

async def _get_calendar_service(db: AsyncSession, user: User) -> CalendarService:
    """Obtiene el CalendarService para el usuario actual."""
    return CalendarService(db, user)


# ══════════════════════════════════════════════════════════════════════════════
#  Herramientas del Agente de Calendario
# ══════════════════════════════════════════════════════════════════════════════

@tool
async def list_calendar_events(
    db: AsyncSession,
    user: User,
    days_ahead: int = 30,
) -> str:
    """
    Lista los próximos eventos del calendario del usuario.

    Args:
        days_ahead: Número de días hacia adelante para consultar (default: 7)

    Returns:
        Texto formateado con la lista de eventos o mensaje si no hay eventos.
    """
    try:
        service = await _get_calendar_service(db, user)
        events = await service.list_events(
            end_date=datetime.now(timezone.utc) + timedelta(days=days_ahead),
            max_results=50
        )

        if not events:
            return f"No tienes eventos programados en los próximos {days_ahead} días."

        lines = ["📅 **Próximos eventos:**\n"]
        for event in events:
            start = event.get("start", {})
            date_str = start.get("dateTime", start.get("date", "Sin fecha"))
            if "T" in date_str:
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                date_str = dt.strftime("%d/%m %H:%M")

            summary = event.get("summary", "Sin título")
            location = event.get("location")
            line = f"• **{summary}** – {date_str}"
            if location:
                line += f" 📍 {location}"
            lines.append(line)

        return "\n".join(lines)

    except ValueError as exc:
        return f"Error: {exc}"
    except Exception as exc:
        logger.exception("Error en list_calendar_events")
        return "Error al consultar el calendario. Inténtalo de nuevo."


@tool
async def create_calendar_event(
    db: AsyncSession,
    user: User,
    summary: str,
    start_datetime: str,
    end_datetime: str,
    description: str | None = None,
    location: str | None = None,
) -> str:
    """
    Crea un nuevo evento en el calendario.

    Args:
        summary: Título del evento (ej: "Reunión con equipo")
        start_datetime: Fecha/hora inicio en formato ISO (ej: "2026-04-20T10:00:00")
        end_datetime: Fecha/hora fin en formato ISO
        description: Descripción opcional del evento
        location: Ubicación opcional

    Returns:
        Mensaje de confirmación con el enlace al evento.
    """
    try:
        # Parsear fechas
        start_dt = datetime.fromisoformat(start_datetime.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end_datetime.replace("Z", "+00:00"))

        service = await _get_calendar_service(db, user)
        result = await service.create_event(
            summary=summary,
            start_dt=start_dt,
            end_dt=end_dt,
            description=description,
            location=location,
        )

        return f"✅ Evento **{summary}** creado correctamente. [Ver evento]({result['htmlLink']})"

    except ValueError as exc:
        return f"Error: {exc}"
    except Exception as exc:
        logger.exception("Error en create_calendar_event")
        return "Error al crear el evento. Verifica las fechas e inténtalo de nuevo."


@tool
async def update_calendar_event(
    db: AsyncSession,
    user: User,
    event_id: str,
    summary: str | None = None,
    start_datetime: str | None = None,
    end_datetime: str | None = None,
    description: str | None = None,
    location: str | None = None,
) -> str:
    """
    Actualiza un evento existente.

    Args:
        event_id: ID del evento a actualizar
        summary: Nuevo título (opcional)
        start_datetime: Nueva fecha/hora inicio ISO (opcional)
        end_datetime: Nueva fecha/hora fin ISO (opcional)
        description: Nueva descripción (opcional)
        location: Nueva ubicación (opcional)

    Returns:
        Mensaje de confirmación.
    """
    try:
        service = await _get_calendar_service(db, user)

        start_dt = datetime.fromisoformat(start_datetime.replace("Z", "+00:00")) if start_datetime else None
        end_dt = datetime.fromisoformat(end_datetime.replace("Z", "+00:00")) if end_datetime else None

        result = await service.update_event(
            event_id=event_id,
            summary=summary,
            start_dt=start_dt,
            end_dt=end_dt,
            description=description,
            location=location,
        )

        return f"✅ Evento **{result['summary']}** actualizado correctamente."

    except ValueError as exc:
        return f"Error: {exc}"
    except Exception as exc:
        logger.exception("Error en update_calendar_event")
        return "Error al actualizar el evento. Verifica el ID y los datos."


@tool
async def delete_calendar_event(
    db: AsyncSession,
    user: User,
    event_id: str,
) -> str:
    """
    Elimina un evento del calendario.

    Args:
        event_id: ID del evento a eliminar

    Returns:
        Mensaje de confirmación.
    """
    try:
        service = await _get_calendar_service(db, user)
        deleted = await service.delete_event(event_id)

        if deleted:
            return "✅ Evento eliminado correctamente."
        return "No se encontró el evento con ese ID."

    except Exception as exc:
        logger.exception("Error en delete_calendar_event")
        return "Error al eliminar el evento."


@tool
async def move_calendar_event(
    db: AsyncSession,
    user: User,
    event_id: str,
    new_datetime: str,
) -> str:
    """
    Mueve un evento a una nueva fecha/hora.

    Args:
        event_id: ID del evento a mover
        new_datetime: Nueva fecha/hora de inicio en formato ISO

    Returns:
        Mensaje de confirmación con la nueva hora.
    """
    try:
        new_dt = datetime.fromisoformat(new_datetime.replace("Z", "+00:00"))

        service = await _get_calendar_service(db, user)
        result = await service.move_event(
            event_id=event_id,
            new_start_dt=new_dt,
        )

        return f"✅ Evento **{result['summary']}** movido a {new_dt.strftime('%d/%m a las %H:%M')}."

    except ValueError as exc:
        return f"Error: {exc}"
    except Exception as exc:
        logger.exception("Error en move_calendar_event")
        return "Error al mover el evento. Verifica el ID y la fecha."


@tool
async def find_event_by_summary(
    db: AsyncSession,
    user: User,
    summary_keyword: str,
) -> str:
    """
    Busca un evento por palabra clave en el título.

    Args:
        summary_keyword: Palabra o frase para buscar en el título

    Returns:
        Lista de eventos encontrados o mensaje si no hay coincidencias.
    """
    try:
        service = await _get_calendar_service(db, user)
        # Listar eventos de los próximos 30 días
        events = await service.list_events(
            start_date=datetime.now(timezone.utc),
            end_date=datetime.now(timezone.utc) + timedelta(days=30),
            max_results=100,
        )

        # Filtrar por keyword (case-insensitive)
        keyword = summary_keyword.lower()
        matches = [
            e for e in events
            if keyword in e.get("summary", "").lower()
        ]

        if not matches:
            return f"No se encontraron eventos con '{summary_keyword}'."

        lines = [f"🔍 **Coincidencias para '{summary_keyword}':**\n"]
        for event in matches:
            start = event.get("start", {})
            date_str = start.get("dateTime", start.get("date", "Sin fecha"))
            if "T" in date_str:
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                date_str = dt.strftime("%d/%m %H:%M")

            lines.append(f"• **{event.get('summary')}** – {date_str} (ID: `{event.get('id')}`)")

        return "\n".join(lines)

    except Exception as exc:
        logger.exception("Error en find_event_by_summary")
        return "Error al buscar el evento."


# ══════════════════════════════════════════════════════════════════════════════
#  Exportar todas las herramientas
# ══════════════════════════════════════════════════════════════════════════════

CALENDAR_TOOLS = [
    list_calendar_events,
    create_calendar_event,
    update_calendar_event,
    delete_calendar_event,
    move_calendar_event,
    find_event_by_summary,
]
