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
    Now persists history to the DB and provides context to the agent.
    """
    async def sse_generator():
        from app.db.base import AsyncSessionLocal
        from app.db.models import ChatMessage
        from sqlalchemy import select

        history = []
        user_id_str = str(current_user.id)
        conv_id = body.conversation_id

        try:
            async with AsyncSessionLocal() as db:
                # 1. Fetch last 15 messages FOR THIS CONVERSATION specifically
                if conv_id:
                    stmt = (
                        select(ChatMessage)
                        .where(ChatMessage.user_id == user_id_str, ChatMessage.conversation_id == conv_id)
                        .order_by(ChatMessage.created_at.desc())
                        .limit(15)
                    )
                    res = await db.execute(stmt)
                    db_msgs = res.scalars().all()
                    # Reverse to get chronological order
                    for m in reversed(db_msgs):
                        history.append({"role": m.role, "content": m.content})

                # 2. Save new user message
                new_user_msg = ChatMessage(
                    user_id=user_id_str,
                    role="user",
                    content=body.message,
                    conversation_id=conv_id
                )
                db.add(new_user_msg)
                await db.commit()

            # 3. Stream from supervisor
            full_content = []
            async for event in supervisor_stream(
                message   = body.message,
                user_name = current_user.name,
                user_id   = user_id_str,
                history   = history
            ):
                if "content" in event:
                    full_content.append(event["content"])
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

            # 4. Save assistant response
            if full_content:
                async with AsyncSessionLocal() as db:
                    assistant_msg = ChatMessage(
                        user_id=user_id_str,
                        role="assistant",
                        content="".join(full_content),
                        conversation_id=conv_id
                    )
                    db.add(assistant_msg)
                    await db.commit()

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
