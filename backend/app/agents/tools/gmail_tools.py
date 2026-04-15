"""
MarcoAI – Gmail Tools for LangGraph Agent (Fase 8)
══════════════════════════════════════════════════════════════════════════════

Herramientas que el Agente de Correo puede invocar para realizar
operaciones sobre Gmail.
"""
from __future__ import annotations

import logging
from langchain_core.tools import tool
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.services.gmail_service import GmailService

logger = logging.getLogger(__name__)


async def _get_gmail_service(db: AsyncSession, user: User) -> GmailService:
    """Obtiene el GmailService para el usuario actual."""
    return GmailService(db, user)


@tool
async def search_emails(
    db: AsyncSession,
    user: User,
    query: str,
    max_results: int = 5,
) -> str:
    """
    Busca correos en la bandeja de entrada usando una consulta de Gmail.

    Args:
        query: Consulta de búsqueda de Gmail (ej: "is:unread", "from:jefe@empresa.com"). Usa "in:inbox" para ver la bandeja principal.
        max_results: Número máximo de correos a recuperar.

    Returns:
        Lista de correos encontrados (asunto, remitente, ID).
    """
    try:
        service = await _get_gmail_service(db, user)
        emails = await service.list_messages(query=query, max_results=max_results)

        if not emails:
            return f"No se encontraron correos para la búsqueda: '{query}'."

        lines = [f"📧 **Correos encontrados ({len(emails)}):**\n"]
        for em in emails:
            lines.append(f"• **{em['subject']}** de {em['from']} (Fecha: {em['date']}) - ID: `{em['id']}`")

        return "\n".join(lines)
    except ValueError as exc:
        return f"Error: {exc}"
    except Exception as exc:
        logger.exception("Error en search_emails")
        return "Error al buscar correos. Verifica la autenticación."


@tool
async def read_email_content(
    db: AsyncSession,
    user: User,
    message_id: str,
) -> str:
    """
    Lee el contenido completo de un correo específico.

    Args:
        message_id: ID del correo a leer (obtenido de search_emails).

    Returns:
        Contenido del correo y metadatos.
    """
    try:
        service = await _get_gmail_service(db, user)
        email = await service.read_message(message_id)

        return (
            f"📨 **De:** {email['from']}\n"
            f"**Fecha:** {email['date']}\n"
            f"**Asunto:** {email['subject']}\n\n"
            f"**Mensaje:**\n{email['body'][:2000]}..." # truncado si es muy largo
        )
    except Exception as exc:
        logger.exception("Error en read_email_content")
        return f"Error al leer el correo con ID {message_id}."


@tool
async def send_new_email(
    db: AsyncSession,
    user: User,
    to: str,
    subject: str,
    body: str,
) -> str:
    """
    Envía un correo nuevo.

    Args:
        to: Dirección de correo del destinatario.
        subject: Asunto del correo.
        body: Contenido del mensaje.

    Returns:
        Confirmación del envío.
    """
    try:
        service = await _get_gmail_service(db, user)
        sent = await service.send_message(to=to, subject=subject, body=body)

        return f"✅ Correo enviado correctamente a **{to}** con asunto **{subject}**."
    except ValueError as exc:
        return f"Error de autenticación: {exc}"
    except Exception as exc:
        logger.exception("Error en send_new_email")
        return "Error al enviar el correo."


GMAIL_TOOLS = [
    search_emails,
    read_email_content,
    send_new_email,
]
