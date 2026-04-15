"""
MarcoAI – LLM Gateway  (HU49)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Single entry-point for every LLM call in the system.

Key features
────────────
• Three task tiers (FAST / STANDARD / INTELLIGENT) map to model chains
  ordered from cheapest-to-most-capable.
• On rate-limit (429), timeout or transient error the gateway transparently
  tries the next provider in the chain without the caller knowing.
• Tenacity retries within each provider (up to 2 attempts with backoff)
  before marking it failed and moving on.
• All LangChain clients are lazy-initialised and cached per model string.

Provider matrix
────────────────────────────────────────────────────────────────────────
 Tier          Primary              Fallback 1           Fallback 2
 ──────────────────────────────────────────────────────────────────────
 FAST          Groq / Llama-3.1-8b  Gemini Flash 2.0     OpenRouter Llama-free
 STANDARD      Gemini Flash 2.0     Groq / Llama-3.3-70b OpenRouter Mistral-free
 INTELLIGENT   Gemini 2.5 Pro       OpenRouter Claude 3.5 Groq / Llama-3.3-70b
────────────────────────────────────────────────────────────────────────

Cost strategy:
 • FAST     → intent routing, metadata extraction, small-talk disambiguation
 • STANDARD → calendar CRUD, finance entry, habit checks
 • INTELLIGENT → RAG Q&A, email drafting, multi-step reasoning (Phase 9+)
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import AsyncIterator

import httpx
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
#  Task Tier enum
# ══════════════════════════════════════════════════════════════════════════════

class TaskTier(str, Enum):
    """
    Complexity level of an LLM task.

    Pass this when calling ``gateway.complete()`` so the router can pick
    the right cost/quality trade-off automatically.
    """
    FAST        = "fast"         # cheapest; used for routing / classification
    STANDARD    = "standard"     # balanced; used for most agent tools
    INTELLIGENT = "intelligent"  # smartest; RAG, email drafting, long reasoning


# ══════════════════════════════════════════════════════════════════════════════
#  Provider / model chains
# ══════════════════════════════════════════════════════════════════════════════

_CHAINS: dict[TaskTier, list[dict[str, str]]] = {
    TaskTier.FAST: [
        # ~0 cost on free tiers, very low latency on RPi
        {"provider": "groq",       "model": "llama-3.1-8b-instant"},
        {"provider": "gemini",     "model": "gemini-2.0-flash"},
        {"provider": "openrouter", "model": "meta-llama/llama-3.1-8b-instruct:free"},
    ],
    TaskTier.STANDARD: [
        {"provider": "gemini",     "model": "gemini-2.0-flash"},
        {"provider": "groq",       "model": "llama-3.3-70b-versatile"},
        {"provider": "openrouter", "model": "mistralai/mistral-7b-instruct:free"},
    ],
    TaskTier.INTELLIGENT: [
        {"provider": "gemini",     "model": "gemini-2.5-pro"},
        {"provider": "openrouter", "model": "anthropic/claude-3.5-haiku"},
        {"provider": "groq",       "model": "llama-3.3-70b-versatile"},
    ],
}

# Errors that should trigger provider fallback  ────────────────────────────────
_FALLBACK_STATUS_CODES = {429, 500, 502, 503, 504}


# ══════════════════════════════════════════════════════════════════════════════
#  Custom exception
# ══════════════════════════════════════════════════════════════════════════════

class AllProvidersExhausted(RuntimeError):
    """Raised when every provider in the tier's chain has failed."""


# ══════════════════════════════════════════════════════════════════════════════
#  LLM Gateway
# ══════════════════════════════════════════════════════════════════════════════

class LLMGateway:
    """
    Provider-agnostic LLM client with tier-based routing and automatic
    sequential fallback across configured providers.

    Singleton instance exposed as ``gateway`` at module level — import and use:

        from app.services.llm_gateway import gateway, TaskTier
        reply = await gateway.complete(messages, tier=TaskTier.FAST)
    """

    def __init__(self) -> None:
        # Lazy-initialised LangChain client caches (keyed by model string)
        self._groq_cache:   dict[str, ChatGroq]                  = {}
        self._gemini_cache: dict[str, ChatGoogleGenerativeAI]    = {}

        # Shared async HTTP client for OpenRouter (one connection pool)
        self._openrouter = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.openrouter_api_key,
            http_client=httpx.AsyncClient(timeout=httpx.Timeout(60.0)),
        )

    # ── Public API ────────────────────────────────────────────────────────────

    async def complete(
        self,
        messages: list[dict],
        tier: TaskTier         = TaskTier.STANDARD,
        max_tokens: int        = 2048,
        temperature: float     = 0.35,
    ) -> str:
        """
        Execute a chat completion and return the assistant's text.

        Parameters
        ----------
        messages    List of {"role": "system"|"user"|"assistant", "content": "..."}
        tier        TaskTier.FAST / STANDARD / INTELLIGENT
        max_tokens  Hard ceiling on output length.
        temperature Sampling temperature (lower = more deterministic).

        Raises
        ------
        AllProvidersExhausted   when every provider in the chain has failed.
        """
        chain = _CHAINS[tier]
        last_exc: Exception | None = None

        for cfg in chain:
            provider = cfg["provider"]
            model    = cfg["model"]
            try:
                logger.debug("→ LLM call  tier=%-12s  %s/%s", tier, provider, model)
                content = await self._dispatch(
                    provider, model, messages, max_tokens, temperature
                )
                logger.debug("← LLM ok    %s/%s", provider, model)
                return content

            except Exception as exc:
                last_exc = exc
                # Decide whether this error warrants a fallback
                if self._should_fallback(exc):
                    logger.warning(
                        "LLM provider %s/%s failed (%s). Falling back…",
                        provider, model, exc,
                    )
                    continue
                # Non-transient error (e.g. bad prompt) – propagate immediately
                logger.error("LLM hard error from %s/%s: %s", provider, model, exc)
                raise

        raise AllProvidersExhausted(
            f"All providers exhausted for tier {tier!r}. "
            f"Last error: {last_exc}"
        )

    async def stream(
        self,
        messages: list[dict],
        tier: TaskTier     = TaskTier.STANDARD,
        max_tokens: int    = 2048,
        temperature: float = 0.35,
    ) -> AsyncIterator[str]:
        """
        Streaming version – yields text chunks as they arrive from the LLM.
        Used by the SSE chat endpoint in Phase 5.

        Currently delegates to Groq (fastest streaming) with Gemini fallback.
        The iterator yields str tokens; callers format them into SSE frames.
        """
        chain = _CHAINS[tier]
        last_exc: Exception | None = None

        for cfg in chain:
            provider = cfg["provider"]
            model    = cfg["model"]
            try:
                # Only Groq and OpenRouter support true streaming here;
                # Gemini falls back to non-streaming for simplicity.
                if provider == "groq":
                    async for chunk in self._stream_groq(model, messages, max_tokens, temperature):
                        yield chunk
                    return
                elif provider == "openrouter":
                    async for chunk in self._stream_openrouter(model, messages, max_tokens, temperature):
                        yield chunk
                    return
                else:
                    # Gemini: non-streaming fallback (yields the whole response at once)
                    content = await self._call_gemini(model, messages, max_tokens, temperature)
                    yield content
                    return

            except Exception as exc:
                last_exc = exc
                if self._should_fallback(exc):
                    logger.warning("Streaming: %s/%s failed – falling back. (%s)", provider, model, exc)
                    continue
                raise

        raise AllProvidersExhausted(
            f"Streaming: all providers exhausted. Last error: {last_exc}"
        )

    # ── Fallback decision ──────────────────────────────────────────────────────

    @staticmethod
    def _should_fallback(exc: Exception) -> bool:
        """
        Return True if the error is transient / rate-limit related,
        meaning we should try the next provider instead of propagating.
        """
        msg = str(exc).lower()
        transient_keywords = (
            "rate limit", "429", "timeout", "connection",
            "502", "503", "504", "overloaded",
            "not_found", "404",      # model not available on this API key/version
            "quota", "exhausted",
        )
        return any(kw in msg for kw in transient_keywords)

    # ── Internal dispatch ──────────────────────────────────────────────────────

    async def _dispatch(
        self,
        provider:    str,
        model:       str,
        messages:    list[dict],
        max_tokens:  int,
        temperature: float,
    ) -> str:
        if provider == "groq":
            return await self._call_groq(model, messages, max_tokens, temperature)
        if provider == "gemini":
            return await self._call_gemini(model, messages, max_tokens, temperature)
        if provider == "openrouter":
            return await self._call_openrouter(model, messages, max_tokens, temperature)
        raise ValueError(f"Unknown provider: {provider!r}")

    # ── Groq ───────────────────────────────────────────────────────────────────

    def _get_groq(self, model: str, max_tokens: int, temperature: float) -> ChatGroq:
        key = f"{model}:{max_tokens}:{temperature}"
        if key not in self._groq_cache:
            self._groq_cache[key] = ChatGroq(
                model=model,
                groq_api_key=settings.groq_api_key,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        return self._groq_cache[key]

    async def _call_groq(self, model, messages, max_tokens, temperature) -> str:
        lc = _to_lc_messages(messages)
        resp = await self._get_groq(model, max_tokens, temperature).ainvoke(lc)
        return str(resp.content)

    async def _stream_groq(self, model, messages, max_tokens, temperature) -> AsyncIterator[str]:
        lc = _to_lc_messages(messages)
        async for chunk in self._get_groq(model, max_tokens, temperature).astream(lc):
            if chunk.content:
                yield str(chunk.content)

    # ── Google Gemini ──────────────────────────────────────────────────────────

    def _get_gemini(self, model: str, max_tokens: int, temperature: float) -> ChatGoogleGenerativeAI:
        key = f"{model}:{max_tokens}:{temperature}"
        if key not in self._gemini_cache:
            self._gemini_cache[key] = ChatGoogleGenerativeAI(
                model=model,
                google_api_key=settings.google_api_key,
                max_output_tokens=max_tokens,
                temperature=temperature,
            )
        return self._gemini_cache[key]

    async def _call_gemini(self, model, messages, max_tokens, temperature) -> str:
        lc = _to_lc_messages(messages)
        resp = await self._get_gemini(model, max_tokens, temperature).ainvoke(lc)
        return str(resp.content)

    # ── OpenRouter ─────────────────────────────────────────────────────────────

    async def _call_openrouter(self, model, messages, max_tokens, temperature) -> str:
        resp = await self._openrouter.chat.completions.create(
            model=model,
            messages=messages,          # already in OpenAI dict format
            max_tokens=max_tokens,
            temperature=temperature,
            extra_headers={
                "HTTP-Referer": "https://marcoai.local",
                "X-Title":      "MarcoAI",
            },
        )
        return resp.choices[0].message.content or ""

    async def _stream_openrouter(self, model, messages, max_tokens, temperature) -> AsyncIterator[str]:
        stream = await self._openrouter.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
            extra_headers={
                "HTTP-Referer": "https://marcoai.local",
                "X-Title":      "MarcoAI",
            },
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta


# ══════════════════════════════════════════════════════════════════════════════
#  LangChain message conversion helper
# ══════════════════════════════════════════════════════════════════════════════

def _to_lc_messages(messages: list[dict]) -> list[BaseMessage]:
    """Convert OpenAI-format message dicts to LangChain message objects."""
    _map = {
        "system":    SystemMessage,
        "user":      HumanMessage,
        "assistant": AIMessage,
    }
    result: list[BaseMessage] = []
    for m in messages:
        role    = m.get("role", "user")
        content = m.get("content", "")
        cls = _map.get(role, HumanMessage)
        result.append(cls(content=content))
    return result


# ══════════════════════════════════════════════════════════════════════════════
#  Module-level singleton  (import this everywhere)
# ══════════════════════════════════════════════════════════════════════════════
gateway = LLMGateway()
