import logging
from datetime import datetime, timedelta
from typing import Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User

logger = logging.getLogger(__name__)


class CalendarService:
    def __init__(self, db: AsyncSession, user: User):
        self.db = db
        self.user = user

    async def _get_service(self):
        """Inicializa el servicio de Google Calendar."""
        if not self.user.google_calendar_token:
            raise ValueError("El usuario no tiene una cuenta de Google conectada")

        creds = Credentials(
            token=self.user.google_calendar_token,
            refresh_token=self.user.google_refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.user.google_client_id,
            client_secret=self.user.google_client_secret,
        )
        return build("calendar", "v3", credentials=creds)

    async def list_events(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        max_results: int = 50,
    ) -> list[dict[str, Any]]:
        """Lista los eventos del calendario."""
        service = await self._get_service()

        if not start_date:
            start_date = datetime.now()
        
        time_min = start_date.isoformat() + "Z"
        time_max = end_date.isoformat() + "Z" if end_date else None

        try:
            events_result = (
                service.events()
                .list(
                    calendarId="primary",
                    timeMin=time_min,
                    timeMax=time_max,
                    maxResults=max_results,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            return events_result.get("items", [])
        except HttpError as exc:
            logger.error("Error listando eventos: %s", exc)
            return []

    async def get_event(self, event_id: str) -> dict[str, Any] | None:
        """Obtiene un evento específico."""
        service = await self._get_service()
        try:
            event = (
                service.events()
                .get(calendarId="primary", eventId=event_id)
                .execute()
            )
            return {
                "id": event.get("id"),
                "summary": event.get("summary"),
                "description": event.get("description", ""),
                "location": event.get("location", ""),
                "start": event.get("start"),
                "end": event.get("end"),
                "htmlLink": event.get("htmlLink"),
            }
        except HttpError as exc:
            if exc.resp.status == 404:
                return None
            logger.error("Error obteniendo evento %s: %s", event_id, exc)
            raise

    async def create_event(
        self,
        summary: str,
        start_dt: datetime,
        end_dt: datetime,
        description: str | None = None,
        location: str | None = None,
        attendees: list[str] | None = None,
    ) -> dict:
        """Crea un nuevo evento."""
        service = await self._get_service()

        event = {
            "summary": summary,
            "location": location,
            "description": description,
            "start": {
                "dateTime": start_dt.isoformat(),
                "timeZone": "Europe/Madrid",
            },
            "end": {
                "dateTime": end_dt.isoformat(),
                "timeZone": "Europe/Madrid",
            },
            "attendees": [{"email": email} for email in (attendees or [])],
        }

        try:
            created = (
                service.events()
                .insert(calendarId="primary", body=event)
                .execute()
            )
            logger.info("Evento creado: %s (%s)", summary, created.get("id"))
            return {
                "id": created.get("id"),
                "summary": created.get("summary"),
                "description": created.get("description"),
                "start": created.get("start"),
                "end": created.get("end"),
                "location": created.get("location"),
                "attendees": created.get("attendees", []),
                "htmlLink": created.get("htmlLink"),
            }
        except HttpError as exc:
            logger.error("Error creando evento: %s", exc)
            raise

    async def update_event(
        self,
        event_id: str,
        summary: str | None = None,
        start_dt: datetime | None = None,
        end_dt: datetime | None = None,
        description: str | None = None,
        location: str | None = None,
    ) -> dict:
        """Actualiza un evento existente."""
        service = await self._get_service()

        # Primero obtener el evento actual
        existing = await self.get_event(event_id)
        if not existing:
            raise ValueError(f"Evento {event_id} no encontrado")

        event = {
            "summary": summary or existing["summary"],
            "description": description if description is not None else existing["description"],
            "location": location if location is not None else existing["location"],
            "start": existing["start"] if start_dt is None else {
                "dateTime": start_dt.isoformat(),
                "timeZone": "Europe/Madrid",
            },
            "end": existing["end"] if end_dt is None else {
                "dateTime": end_dt.isoformat(),
                "timeZone": "Europe/Madrid",
            },
        }

        try:
            updated = (
                service.events()
                .patch(calendarId="primary", eventId=event_id, body=event)
                .execute()
            )
            logger.info("Evento actualizado: %s (%s)", updated.get("summary"), event_id)
            return {
                "id": updated.get("id"),
                "summary": updated.get("summary"),
                "description": updated.get("description"),
                "start": updated.get("start"),
                "end": updated.get("end"),
                "location": updated.get("location"),
                "attendees": updated.get("attendees", []),
                "htmlLink": updated.get("htmlLink"),
            }
        except HttpError as exc:
            logger.error("Error actualizando evento %s: %s", event_id, exc)
            raise

    async def delete_event(self, event_id: str) -> bool:
        """Elimina un evento del calendario."""
        service = await self._get_service()

        try:
            (
                service.events()
                .delete(calendarId="primary", eventId=event_id)
                .execute()
            )
            logger.info("Evento eliminado: %s", event_id)
            return True
        except HttpError as exc:
            if exc.resp.status == 404:
                return False
            logger.error("Error eliminando evento %s: %s", event_id, exc)
            raise

    async def move_event(
        self,
        event_id: str,
        new_start_dt: datetime,
        duration_minutes: int | None = None,
    ) -> dict:
        """Mueve un evento a una nueva fecha/hora."""
        existing = await self.get_event(event_id)
        if not existing:
            raise ValueError(f"Evento {event_id} no encontrado")

        # Calcular nueva fecha de fin si no se especifica duración
        if duration_minutes is None:
            old_start = datetime.fromisoformat(existing["start"]["dateTime"].replace("Z", "+00:00"))
            old_end = datetime.fromisoformat(existing["end"]["dateTime"].replace("Z", "+00:00"))
            duration_minutes = int((old_end - old_start).total_seconds() / 60)

        new_end_dt = new_start_dt + timedelta(minutes=duration_minutes)

        return await self.update_event(
            event_id=event_id,
            start_dt=new_start_dt,
            end_dt=new_end_dt
        )
