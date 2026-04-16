"""
MarcoAI – Gmail API Routes (Fase 8)
══════════════════════════════════════════════════════════════════════════════

Endpoints:
  GET  /api/v1/gmail/list         – Lista los últimos correos
  GET  /api/v1/gmail/messages/{id} – Obtiene el contenido de un correo
  POST /api/v1/gmail/send         – Envía un correo nuevo
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.db.base import get_db
from app.db.models import User
from app.services.gmail_service import GmailService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/gmail", tags=["Gmail"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class EmailResponse(BaseModel):
    id: str
    subject: str
    snippet: str
    sender: str
    date: str

    class Config:
        populate_by_name = True


class EmailDetailResponse(BaseModel):
    id: str
    subject: str
    sender: str
    date: str
    body: str
    is_html: bool = False

    class Config:
        populate_by_name = True


class EmailSend(BaseModel):
    to: str = Field(..., description="Email del destinatario")
    subject: str = Field(..., min_length=1)
    body: str = Field(..., min_length=1)


class EmailListResponse(BaseModel):
    messages: list[EmailResponse]


# ── Helper ────────────────────────────────────────────────────────────────────

async def get_gmail_service(user: User, db) -> GmailService:
    """Obtiene el servicio de Gmail para el usuario actual."""
    if not user.google_calendar_token:  # Reutilizamos el token de Google
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No has conectado tu cuenta de Google. "
                   "Por favor, vuelve a iniciar sesión para autorizar el acceso.",
        )
    return GmailService(db, user)


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/list", response_model=EmailListResponse, summary="Listar correos recientes")
async def list_emails(
    q: str = Query(default="", description="Query de búsqueda (opcional)"),
    max_results: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtiene los últimos mensajes de la bandeja de entrada."""
    service = await get_gmail_service(current_user, db)
    try:
            messages = await service.list_messages(query=q, max_results=max_results)
            # Adaptamos los campos del servicio al schema
            formatted = []
            for m in messages:
                formatted.append({
                    "id": m["id"],
                    "subject": m["subject"],
                    "snippet": m["snippet"],
                    "sender": m["from"],
                    "date": m["date"]
                })
            return {"messages": formatted}
    except Exception as exc:
        logger.exception("Error listing emails")
        raise HTTPException(status_code=500, detail="Error al obtener correos de Gmail")


@router.get("/messages/{message_id}", response_model=EmailDetailResponse, summary="Leer un correo")
async def read_email(
    message_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lee el contenido completo de un mensaje por ID."""
    service = await get_gmail_service(current_user, db)
    try:
        msg = await service.read_message(message_id)
        # Ensure 'from' is mapped to 'sender' for schema consistency
        msg["sender"] = msg.pop("from", "(Sin remitente)")
        return msg
    except Exception as exc:
        logger.exception("Error reading email")
        raise HTTPException(status_code=500, detail="Error al leer el correo")


@router.post("/send", status_code=201, summary="Enviar correo")
async def send_email(
    body: EmailSend,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Envía un nuevo correo electrónico."""
    service = await get_gmail_service(current_user, db)
    try:
        result = await service.send_message(
            to=body.to,
            subject=body.subject,
            body=body.body
        )
        return result
    except Exception as exc:
        logger.exception("Error sending email")
        raise HTTPException(status_code=500, detail="Error al enviar el correo")
