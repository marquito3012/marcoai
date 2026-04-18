"""
MarcoAI – Agent State
TypedDict that flows through every node in the LangGraph supervisor graph.
"""
from typing import TypedDict


class AgentState(TypedDict):
    # ── Input (provided by the caller) ────────────────────────────────────────
    user_message: str
    user_name:    str
    user_id:      str
    history:      list[dict]  # list of {"role": "...", "content": "..."}

    # ── Set by supervisor_node ─────────────────────────────────────────────────
    intent: str | None     # one of the VALID_INTENTS keys

    # ── Set by the routed agent node ───────────────────────────────────────────
    system_prompt: str     # agent-specific LLM system prompt
    tier: str              # "fast" | "standard" | "intelligent"

    # ── Future: populated by tool calls (DB queries, API calls) ───────────────
    context: dict
