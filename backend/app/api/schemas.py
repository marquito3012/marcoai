"""
MarcoAI – Shared Pydantic schemas

Centralised request/response models used across multiple routes.
Domain-specific schemas (finance, calendar…) go in their own modules.
"""
from pydantic import BaseModel, Field


# ── LLM / Chat ────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8192, description="User's chat message")
    conversation_id: str | None = Field(None, description="Current conversation session ID")


class ChatResponse(BaseModel):
    response: str
    provider: str | None = None   # populated by the gateway test endpoint
    model:    str | None = None


# ── LLM Gateway test ──────────────────────────────────────────────────────────

class LLMTestRequest(BaseModel):
    message: str = Field(
        default="Di 'Hola, soy Marco' en una sola oración.",
        description="Prompt to send to the LLM Gateway for testing.",
    )
    tier: str = Field(
        default="fast",
        description="Task tier: 'fast', 'standard', or 'intelligent'.",
    )


class LLMTestResponse(BaseModel):
    tier:     str
    response: str
    error:    str | None = None
