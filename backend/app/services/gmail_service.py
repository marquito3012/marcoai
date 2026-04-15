"""
MarcoAI – Gmail Service (Fase 8)
══════════════════════════════════════════════════════════════════════════════

Servicio para interactuar con la Gmail API.

Características:
  - Leer la bandeja de entrada
  - Buscar hilos de correo
  - Enviar correos
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
import base64
from email.message import EmailMessage

import httpx
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.readonly",
]


class GmailService:
    """
    Servicio de Gmail con gestión automática de tokens (reutiliza lógica de calendario).
    """

    def __init__(self, db: AsyncSession, user: User):
        self.db = db
        self.user = user
        self._service = None

    def _get_credentials(self) -> Credentials | None:
        if not self.user.google_calendar_token:
            return None

        expires_at = self.user.google_calendar_token_expires_at
        return Credentials(
            token=self.user.google_calendar_token,
            refresh_token=self.user.google_calendar_refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=None,
            client_secret=None,
            scopes=SCOPES,
            expiry=expires_at.replace(tzinfo=timezone.utc) if expires_at else None,
        )

    async def _refresh_tokens(self, credentials: Credentials) -> None:
        try:
            credentials.refresh(httpx.Client())
            self.user.google_calendar_token = credentials.token
            self.user.google_calendar_token_expires_at = credentials.expiry
            self.db.add(self.user)
            await self.db.commit()
            logger.info("Tokens OAuth refreshados para user=%s", self.user.id)
        except Exception as exc:
            logger.error("Error al refreshar tokens: %s", exc)
            raise

    async def _get_service(self):
        credentials = self._get_credentials()
        if not credentials:
            raise ValueError("Usuario no tiene tokens de Google OAuth")

        if credentials.expired and credentials.refresh_token:
            await self._refresh_tokens(credentials)

        self._service = build("gmail", "v1", credentials=credentials)
        return self._service

    async def list_messages(self, query: str = "", max_results: int = 10) -> list[dict]:
        """Busca correos en Gmail usando el query especificado."""
        service = await self._get_service()
        try:
            res = (
                service.users()
                .messages()
                .list(userId="me", q=query, maxResults=max_results)
                .execute()
            )
            messages = res.get("messages", [])
            
            result = []
            for msg in messages:
                # Obtener detalles del mensaje
                msg_full = service.users().messages().get(userId="me", id=msg["id"], format="metadata", metadataHeaders=["From", "Subject", "Date"]).execute()
                headers = {h["name"]: h["value"] for h in msg_full.get("payload", {}).get("headers", [])}
                result.append({
                    "id": msg_full["id"],
                    "snippet": msg_full.get("snippet", ""),
                    "subject": headers.get("Subject", "(Sin asunto)"),
                    "from": headers.get("From", ""),
                    "date": headers.get("Date", ""),
                })
            return result
        except HttpError as exc:
            logger.error("Error listando correos: %s", exc)
            raise

    async def read_message(self, message_id: str) -> dict:
        """Lee el contenido completo de un mensaje."""
        service = await self._get_service()
        try:
            msg = service.users().messages().get(userId="me", id=message_id, format="full").execute()
            
            # Simple text extraction
            body = "No se pudo extraer el texto."
            payload = msg.get("payload", {})
            parts = payload.get("parts", [])
            
            # Buscando plain text
            for part in parts:
                if part.get("mimeType") == "text/plain":
                    data = part.get("body", {}).get("data")
                    if data:
                        body = base64.urlsafe_b64decode(data).decode('utf-8')
                        break
            
            # Si no hay parts (correo muy simple o sin charset variable)
            if not parts and payload.get("body", {}).get("data"):
                data = payload.get("body").get("data")
                body = base64.urlsafe_b64decode(data).decode('utf-8')

            headers = {h["name"]: h["value"] for h in payload.get("headers", [])}
            
            return {
                "id": msg["id"],
                "subject": headers.get("Subject", "(Sin asunto)"),
                "from": headers.get("From", ""),
                "date": headers.get("Date", ""),
                "body": body
            }
        except HttpError as exc:
            logger.error("Error leyendo correo %s: %s", message_id, exc)
            raise

    async def send_message(self, to: str, subject: str, body: str) -> dict:
        """Envía un correo nuevo."""
        service = await self._get_service()
        
        message = EmailMessage()
        message.set_content(body)
        message["To"] = to
        message["From"] = "me"
        message["Subject"] = subject
        
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {"raw": encoded_message}
        
        try:
            sent = service.users().messages().send(userId="me", body=create_message).execute()
            return {"id": sent["id"], "threadId": sent["threadId"]}
        except HttpError as exc:
            logger.error("Error enviando correo: %s", exc)
            raise
