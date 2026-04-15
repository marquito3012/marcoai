"""
MarcoAI – Document/Files Tools for LangGraph Agent (Fase 9)
══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import logging
from langchain_core.tools import tool
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.services.document_service import DocumentService

logger = logging.getLogger(__name__)


@tool
async def search_documents_content(
    db: AsyncSession,
    user: User,
    query: str,
) -> str:
    """
    Busca información dentro de los documentos almacenados del usuario
    utilizando búsqueda semántica de vectores (RAG).

    Args:
        query: La consulta o pregunta a buscar en los documentos.

    Returns:
        Los fragmentos de texto más relevantes encontrados en la base de datos documental.
    """
    try:
        service = DocumentService(db, user.id)
        results = await service.search_similar(query=query, top_k=4)

        if not results:
            return "No se encontró información relevante en tus documentos."

        lines = ["📂 **Información extraída de tus documentos (RAG):**\n"]
        for r in results:
            lines.append(f"• {r}\n")

        return "\n".join(lines)
    except Exception as exc:
        logger.exception("Error en search_documents_content")
        return "Hubo un error buscando en tus documentos."
