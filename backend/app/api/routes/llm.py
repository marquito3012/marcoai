"""
MarcoAI – LLM Gateway Test Route

Exposes a simple endpoint so you can verify that each provider tier
is reachable and the fallback chain works, without needing the full
agent graph up yet.

POST /api/v1/llm/test
  Body:   { "message": "...", "tier": "fast|standard|intelligent" }
  Auth:   JWT cookie required (uses get_current_user dependency)
  Returns: { "tier": "...", "response": "...", "error": null }

Usage during development:
  curl -b 'access_token=<jwt>' \\
       -H 'Content-Type: application/json' \\
       -d '{"message":"Di hola","tier":"fast"}' \\
       http://localhost:8000/api/v1/llm/test
"""
import logging

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.api.schemas import LLMTestRequest, LLMTestResponse
from app.db.models import User
from app.services.llm_gateway import AllProvidersExhausted, TaskTier, gateway

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/llm", tags=["LLM Gateway"])


@router.post("/test", response_model=LLMTestResponse, summary="Probar el LLM Gateway")
async def test_llm_gateway(
    body: LLMTestRequest,
    _current_user: User = Depends(get_current_user),
) -> LLMTestResponse:
    """
    Send a test prompt through the LLM Gateway and return the response.

    Useful for:
      - Verifying API keys are valid.
      - Confirming the fallback chain works when a provider is down.
      - Profiling latency per tier from this hardware.
    """
    try:
        tier = TaskTier(body.tier)
    except ValueError:
        valid = [t.value for t in TaskTier]
        return LLMTestResponse(
            tier=body.tier,
            response="",
            error=f"Tier inválido '{body.tier}'. Valores válidos: {valid}",
        )

    messages = [
        {
            "role":    "system",
            "content": (
                "Eres Marco, un asistente personal conciso y amigable. "
                "Responde siempre en español."
            ),
        },
        {"role": "user", "content": body.message},
    ]

    try:
        response = await gateway.complete(messages, tier=tier)
        return LLMTestResponse(tier=tier.value, response=response)

    except AllProvidersExhausted as exc:
        logger.error("LLM test – all providers exhausted: %s", exc)
        return LLMTestResponse(
            tier=tier.value,
            response="",
            error=f"Todos los proveedores fallaron: {exc}",
        )
    except Exception as exc:
        logger.exception("LLM test – unexpected error")
        return LLMTestResponse(
            tier=tier.value,
            response="",
            error=str(exc),
        )
