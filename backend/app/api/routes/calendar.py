"""
MarcoAI – Google Calendar API Routes (Fase 6)
══════════════════════════════════════════════════════════════════════════════

Endpoints:
  GET  /api/v1/calendar/events       – Lista eventos del calendario
  POST /api/v1/calendar/events       – Crea nuevo evento
  GET  /api/v1/calendar/events/{id}  – Obtiene evento por ID
  PUT  /api/v1/calendar/events/{id}  – Actualiza evento
  DELETE /api/v1/calendar/events/{id} – Elimina evento
  POST /api/v1/calendar/events/{id}/move – Mueve evento a nueva fecha
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import get_current_user
from app.db.models import User
from app.services.calendar_service import CalendarService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/calendar", tags=["Calendario"])


# ══════════════════════════════════════════════════════════════════════════════
#  Schemas
# ══════════════════════════════════════════════════════════════════════════════

class EventCreate(BaseModel):
    summary: str = Field(..., min_length=1, max_length=256)
    start_datetime: str = Field(..., description="ISO 8601 datetime")
    end_datetime: str = Field(..., description="ISO 8601 datetime")
    description: str | None = None
    location: str | None = None
    attendees: list[str] = Field(default_factory=list)


class EventUpdate(BaseModel):
    summary: str | None = None
    start_datetime: str | None = None
    end_datetime: str | None = None
    description: str | None = None
    location: str | None = None


class EventMove(BaseModel):
    new_datetime: str = Field(..., description="ISO 8601 datetime para el nuevo inicio")


class EventResponse(BaseModel):
    id: str
    summary: str
    description: str | None = None
    start: dict
    end: dict
    location: str | None = None
    attendees: list[dict] = Field(default_factory=list)
    htmlLink: str | None = None


class EventsListResponse(BaseModel):
    events: list[EventResponse]


# ══════════════════════════════════════════════════════════════════════════════
#  Helper
# ══════════════════════════════════════════════════════════════════════════════

async def get_calendar_service(user: User, db) -> CalendarService:
    """Obtiene el servicio de calendario para el usuario actual."""
    if not user.google_calendar_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No has conectado tu cuenta de Google Calendar. "
                   "Por favor, vuelve a iniciar sesión para autorizar el acceso al calendario.",
        )
    return CalendarService(db, user)


# ══════════════════════════════════════════════════════════════════════════════
#  Routes
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/events", response_model=EventsListResponse, summary="Listar eventos del calendario")
async def list_events(
    days_ahead: int = Query(default=7, ge=1, le=90, description="Días hacia adelante para consultar"),
    current_user: User = Depends(get_current_user),
    db=Depends(lambda: None),  # Will be replaced by actual dep
):
    """
    Lista los próximos eventos del calendario principal del usuario.

    - **days_ahead**: Número de días hacia adelante para consultar (1-90)
    """
    from app.db.base import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        service = await get_calendar_service(current_user, session)

        try:
            events = await service.list_events(max_results=100)
            return {"events": events}
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except Exception as exc:
            logger.exception("Error listing calendar events")
            raise HTTPException(status_code=500, detail="Error al obtener eventos del calendario")


@router.get("/events/{event_id}", response_model=EventResponse, summary="Obtener evento por ID")
async def get_event(
    event_id: str,
    current_user: User = Depends(get_current_user),
    db=Depends(lambda: None),
):
    """Obtiene los detalles de un evento específico."""
    from app.db.base import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        service = await get_calendar_service(current_user, session)

        try:
            event = await service.get_event(event_id)
            if event is None:
                raise HTTPException(status_code=404, detail="Evento no encontrado")
            return event
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Error getting calendar event")
            raise HTTPException(status_code=500, detail="Error al obtener el evento")


@router.post("/events", response_model=EventResponse, status_code=201, summary="Crear nuevo evento")
async def create_event(
    body: EventCreate,
    current_user: User = Depends(get_current_user),
    db=Depends(lambda: None),
):
    """
    Crea un nuevo evento en el calendario principal.

    - **summary**: Título del evento
    - **start_datetime**: Fecha/hora de inicio (ISO 8601)
    - **end_datetime**: Fecha/hora de fin (ISO 8601)
    - **description**: Descripción opcional
    - **location**: Ubicación opcional
    - **attendees**: Lista de emails de invitados (opcional)
    """
    from app.db.base import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        service = await get_calendar_service(current_user, session)

        try:
            start_dt = datetime.fromisoformat(body.start_datetime.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(body.end_datetime.replace("Z", "+00:00"))

            event = await service.create_event(
                summary=body.summary,
                start_dt=start_dt,
                end_dt=end_dt,
                description=body.description,
                location=body.location,
                attendees=body.attendees if body.attendees else None,
            )
            return event
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except Exception as exc:
            logger.exception("Error creating calendar event")
            raise HTTPException(status_code=500, detail="Error al crear el evento")


@router.put("/events/{event_id}", response_model=EventResponse, summary="Actualizar evento")
async def update_event(
    event_id: str,
    body: EventUpdate,
    current_user: User = Depends(get_current_user),
    db=Depends(lambda: None),
):
    """
    Actualiza un evento existente.

    Solo los campos proporcionados serán actualizados.
    """
    from app.db.base import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        service = await get_calendar_service(current_user, session)

        try:
            start_dt = datetime.fromisoformat(body.start_datetime.replace("Z", "+00:00")) if body.start_datetime else None
            end_dt = datetime.fromisoformat(body.end_datetime.replace("Z", "+00:00")) if body.end_datetime else None

            event = await service.update_event(
                event_id=event_id,
                summary=body.summary,
                start_dt=start_dt,
                end_dt=end_dt,
                description=body.description,
                location=body.location,
            )
            return event
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Error updating calendar event")
            raise HTTPException(status_code=500, detail="Error al actualizar el evento")


@router.delete("/events/{event_id}", status_code=204, summary="Eliminar evento")
async def delete_event(
    event_id: str,
    current_user: User = Depends(get_current_user),
    db=Depends(lambda: None),
):
    """Elimina un evento del calendario."""
    from app.db.base import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        service = await get_calendar_service(current_user, session)

        try:
            deleted = await service.delete_event(event_id)
            if not deleted:
                raise HTTPException(status_code=404, detail="Evento no encontrado")
            return None
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Error deleting calendar event")
            raise HTTPException(status_code=500, detail="Error al eliminar el evento")


@router.post("/events/{event_id}/move", response_model=EventResponse, summary="Mover evento a nueva fecha")
async def move_event(
    event_id: str,
    body: EventMove,
    current_user: User = Depends(get_current_user),
    db=Depends(lambda: None),
):
    """
    Mueve un evento a una nueva fecha/hora manteniendo su duración original.

    - **new_datetime**: Nueva fecha/hora de inicio (ISO 8601)
    """
    from app.db.base import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        service = await get_calendar_service(current_user, session)

        try:
            new_dt = datetime.fromisoformat(body.new_datetime.replace("Z", "+00:00"))
            event = await service.move_event(
                event_id=event_id,
                new_start_dt=new_dt,
            )
            return event
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Error moving calendar event")
            raise HTTPException(status_code=500, detail="Error al mover el evento")
