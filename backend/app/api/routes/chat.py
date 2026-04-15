"""
MarcoAI – Chat Router (HU03, HU06, HU07)
══════════════════════════════════════════

Endpoints:
  POST /api/v1/chat         – single-turn JSON (fallback / testing)
  POST /api/v1/chat/stream  – streaming SSE routed via LangGraph supervisor

SSE wire format
───────────────
  data: {"event": "route", "intent": "FINANCE", "label": "Finanzas"}  ← routing badge
  data: {"content": "<token>"}   ← one or more per response
  data: [DONE]                   ← signals end of stream
  data: {"error": "<msg>"}       ← only if every provider failed
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.agents.supervisor import supervisor_stream
from app.api.deps import get_current_user
from app.api.schemas import ChatRequest, ChatResponse
from app.db.models import User
from app.services.llm_gateway import AllProvidersExhausted, TaskTier, gateway

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["Chat"])


def _direct_messages(user_name: str, message: str) -> list[dict]:
    """Build message list for the non-streaming (bypass) endpoint."""
    return [
        {
            "role": "system",
            "content": (
                f"Eres Marco, el asistente personal inteligente de {user_name}. "
                "Responde en español, de forma concisa, usando Markdown."
            ),
        },
        {"role": "user", "content": message},
    ]


# ── Non-streaming (JSON) ───────────────────────────────────────────────────────
@router.post("", response_model=ChatResponse, summary="Chat normal (JSON completo)")
async def chat(
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    """Single-turn, non-streaming chat. Useful for testing or API clients."""
    msgs = _direct_messages(current_user.name, body.message)
    try:
        text = await gateway.complete(msgs, tier=TaskTier.STANDARD)
    except AllProvidersExhausted:
        text = "Lo siento, no pude conectar con ningún proveedor de IA."
    return ChatResponse(response=text)


# ── Streaming (SSE via LangGraph supervisor) ───────────────────────────────────
@router.post("/stream", summary="Chat con streaming SSE + LangGraph (HU06, HU07)")
async def chat_stream(
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """
    Low-latency streaming chat routed through the LangGraph supervisor.

    Pipeline per request:
      1. Supervisor node classifies intent (FAST tier, ~100ms on Groq)
      2. Route event sent to frontend  → shows module badge in the UI
      3. Agent node sets system prompt and LLM tier
      4. Response streamed token-by-token via gateway.stream()
    """
    async def sse_generator():
        try:
            async for event in supervisor_stream(
                message   = body.message,
                user_name = current_user.name,
                user_id   = str(current_user.id),
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as exc:
            logger.exception("SSE generator error")
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":     "no-cache",
            "Connection":        "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
