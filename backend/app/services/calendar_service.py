"""
MarcoAI – Google Calendar Service (Fase 6)
══════════════════════════════════════════════════════════════════════════════

Servicio para interactuar con la Google Calendar API.

Características:
  - Refresh automático de tokens expirados
  - Operaciones CRUD sobre eventos
  - Aislamiento por user_id (cada usuario solo ve sus propios calendarios)
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from google.oauth2.credentials import Credentials
from google.oauth2 import reauth
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.core.config import settings

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar"]


class CalendarService:
    """
    Servicio de Google Calendar con gestión automática de tokens.

    Uso:
        service = CalendarService(db, user)
        events = await service.list_events()
        event = await service.create_event(summary="Reunión", start_dt=..., end_dt=...)
    """

    def __init__(self, db: AsyncSession, user: User):
        self.db = db
        self.user = user
        self._service = None

    def _get_credentials(self) -> Credentials | None:
        """Construye credenciales de Google OAuth desde los tokens almacenados."""
        if not self.user.google_calendar_token:
            return None

        # Sanitize datetime to ensure it's offset-aware for comparison
        now = datetime.now(timezone.utc)
        expires_at = self.user.google_calendar_token_expires_at
        if expires_at and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        is_expired = expires_at is None or expires_at < now

        # Google auth library compares against naive UTC internally.
        # We must provide a naive UTC object to avoid "offset-naive vs offset-aware" crashes.
        naive_expiry = None
        if expires_at:
             # Ensure we start from a clean UTC state even if DB returned naive
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            # Convert to naive UTC
            naive_expiry = expires_at.astimezone(timezone.utc).replace(tzinfo=None)

        return Credentials(
            token=self.user.google_calendar_token,
            refresh_token=self.user.google_calendar_refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
            scopes=SCOPES,
            expiry=naive_expiry,
        )

    async def _refresh_tokens(self, credentials: Credentials) -> None:
        """Refresca los tokens usando httpx (async) y guarda en BD."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post("https://oauth2.googleapis.com/token", data={
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "refresh_token": self.user.google_calendar_refresh_token,
                    "grant_type": "refresh_token",
                })
                resp.raise_for_status()
                data = resp.json()

                # Actualizar objeto de credenciales para el proceso actual
                credentials.token = data["access_token"]
                if "expires_in" in data:
                    expiry = datetime.now(timezone.utc) + timedelta(seconds=data["expires_in"])
                    # google-auth expects naive UTC internally for its expiry check
                    credentials.expiry = expiry.replace(tzinfo=None)
                    self.user.google_calendar_token_expires_at = expiry

                # Actualizar en BD para persistencia
                self.user.google_calendar_token = data["access_token"]
                self.db.add(self.user)
                await self.db.commit()
                await self.db.refresh(self.user)

            logger.info("Tokens de Calendar refreshados exitosamente para user=%s", self.user.id)

            logger.info("Tokens de Calendar refreshados para user=%s", self.user.id)
        except Exception as exc:
            logger.error("Error al refreshar tokens de Calendar: %s", exc)
            raise

    async def _get_service(self) -> Any:
        """Obtiene el servicio de Google Calendar, refreshando tokens si es necesario."""
        credentials = self._get_credentials()
        if not credentials:
            raise ValueError("Usuario no tiene tokens de Google Calendar")

        if credentials.expired and credentials.refresh_token:
            await self._refresh_tokens(credentials)

        self._service = build("calendar", "v3", credentials=credentials)
        return self._service

    async def list_events(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        max_results: int = 50,
    ) -> list[dict]:
        """
        Lista eventos del calendario principal del usuario.

        Args:
            start_date: Inicio del rango (default: hoy 00:00)
            end_date: Fin del rango (default: hoy + 7 días)
            max_results: Máximo número de eventos a devolver
        """
        service = await self._get_service()

        if start_date is None:
            start_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        if end_date is None:
            end_date = start_date + timedelta(days=30)

        try:
            events_result = (
                service.events()
                .list(
                    calendarId="primary",
                    timeMin=start_date.isoformat(),
                    timeMax=end_date.isoformat(),
                    maxResults=max_results,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            events = events_result.get("items", [])

            return [
                {
                    "id": event.get("id"),
                    "summary": event.get("summary", "Sin título"),
                    "description": event.get("description", ""),
                    "start": event.get("start", {}),
                    "end": event.get("end", {}),
                    "location": event.get("location", ""),
                    "attendees": event.get("attendees", []),
                    "htmlLink": event.get("htmlLink"),
                }
                for event in events
            ]
        except HttpError as exc:
            logger.error("Error listando eventos de Calendar: %s", exc)
            raise

    async def get_event(self, event_id: str) -> dict | None:
        """Obtiene un evento específico por su ID."""
        service = await self._get_service()

        try:
            event = (
                service.events()
                .get(calendarId="primary", eventId=event_id)
                .execute()
            )
            return {
                "id": event.get("id"),
                "summary": event.get("summary", "Sin título"),
                "description": event.get("description", ""),
                "start": event.get("start", {}),
                "end": event.get("end", {}),
                "location": event.get("location", ""),
                "attendees": event.get("attendees", []),
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
        """
        Crea un nuevo evento en el calendario principal.

        Args:
            summary: Título del evento
            start_dt: Fecha/hora de inicio
            end_dt: Fecha/hora de fin
            description: Descripción opcional
            location: Ubicación opcional
            attendees: Lista de emails de invitados
        """
        service = await self._get_service()

        event = {
            "summary": summary,
            "description": description or "",
            "location": location or "",
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
        """
        Mueve un evento a una nueva fecha/hora.

        Args:
            event_id: ID del evento a mover
            new_start_dt: Nueva fecha/hora de inicio
            duration_minutes: Duración en minutos (si None, mantiene la duración original)
        """
        existing = await self.get_event(event_id)
        if not existing:
            raise ValueError(f"Evento {event_id} no encontrado")

        # Calcular duración original si no se especifica
        if duration_minutes is None:
            start_str = existing["start"].get("dateTime", existing["start"].get("date"))
            end_str = existing["end"].get("dateTime", existing["end"].get("date"))
            if start_str and end_str:
                start = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                end = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
                duration_minutes = int((end - start).total_seconds() / 60)
            else:
                duration_minutes = 60  # Default 1 hora

        new_end_dt = new_start_dt + timedelta(minutes=duration_minutes)

        return await self.update_event(
            event_id=event_id,
            start_dt=new_start_dt,
            end_dt=new_end_dt,
        )


# ══════════════════════════════════════════════════════════════════════════════
#  Factory function
# ══════════════════════════════════════════════════════════════════════════════

async def get_calendar_service(db: AsyncSession, user: User) -> CalendarService:
    """Factory para obtener CalendarService."""
    return CalendarService(db, user)
