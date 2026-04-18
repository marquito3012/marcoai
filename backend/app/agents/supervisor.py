"""
MarcoAI – LangGraph Supervisor Graph  (HU07, HU08, HU50)
══════════════════════════════════════════════════════════

Architecture
────────────
                    ┌──────────────────────────────────┐
  user message ──▶  │  supervisor_node                 │
                    │    (FAST tier: intent classifier) │
                    └──────────────┬───────────────────┘
                                   │ conditional edge (route())
          ┌─────────────┬──────────┼──────────┬────────────┬───────────┐
          ▼             ▼          ▼          ▼            ▼           ▼
   general_chat    calendar    finance     mail          files      habits
          │             │          │          │            │           │
          └─────────────┴──────────┴──────────┴────────────┴───────────┘
                                   │
                                  END
                                   │
            supervisor_stream() reads final_state and streams the LLM response
            token-by-token via gateway.stream()

Public API
──────────
    from app.agents.supervisor import supervisor_stream

    async for event in supervisor_stream(message, user_name, user_id):
        # event is a dict:
        #   {"event": "route", "intent": "FINANCE", "label": "Finanzas"}
        #   {"content": "<token>"}
"""
from __future__ import annotations

import logging
from typing import AsyncIterator

from langgraph.graph import END, StateGraph

from app.agents.nodes import (
    calendar_node,
    files_node,
    finance_node,
    general_chat_node,
    habits_node,
    mail_node,
    route,
    supervisor_node,
)
from app.agents.prompts import INTENT_LABELS
from app.agents.states import AgentState
from app.services.llm_gateway import AllProvidersExhausted, TaskTier, gateway

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
#  Build & compile the graph  (happens once at module import)
# ══════════════════════════════════════════════════════════════════════════════

def _build_graph() -> "CompiledGraph":
    g = StateGraph(AgentState)

    # Nodes
    g.add_node("supervisor",  supervisor_node)
    g.add_node("general_chat", general_chat_node)
    g.add_node("calendar",    calendar_node)
    g.add_node("finance",     finance_node)
    g.add_node("mail",        mail_node)
    g.add_node("files",       files_node)
    g.add_node("habits",      habits_node)

    # Entry point
    g.set_entry_point("supervisor")

    # Conditional edges from supervisor
    g.add_conditional_edges(
        "supervisor",
        route,
        {
            "general_chat": "general_chat",
            "calendar":     "calendar",
            "finance":      "finance",
            "mail":         "mail",
            "files":        "files",
            "habits":       "habits",
        },
    )

    # All agent nodes → END
    for node_name in ("general_chat", "calendar", "finance", "mail", "files", "habits"):
        g.add_edge(node_name, END)

    return g.compile()


_compiled = _build_graph()
logger.info("LangGraph supervisor compiled successfully.")


# ══════════════════════════════════════════════════════════════════════════════
#  Public streaming function
# ══════════════════════════════════════════════════════════════════════════════

async def supervisor_stream(
    message:   str,
    user_name: str,
    user_id:   str,
    history:   list[dict] | None = None,
) -> AsyncIterator[dict]:
    """
    Main entry point for the agent pipeline.
    """
    # ── a. Intent classification via the graph ────────────────────────────────
    initial: AgentState = {
        "user_message":  message,
        "user_name":     user_name,
        "user_id":       user_id,
        "history":       history or [],
        "intent":        None,
        "system_prompt": "",
        "tier":          "standard",
        "context":       {},
    }

    try:
        final: AgentState = await _compiled.ainvoke(initial)
    except Exception as exc:
        logger.error("LangGraph graph failed: %s", exc)
        # Graceful fallback: skip routing, answer directly
        final = {
            **initial,
            "intent":        "GENERAL_CHAT",
            "system_prompt": f"Eres Marco, el asistente personal de {user_name}. Responde en español.",
            "tier":          "standard",
        }

    intent = final.get("intent", "GENERAL_CHAT")
    label  = INTENT_LABELS.get(intent, intent)

    # ── b. Yield routing event ────────────────────────────────────────────────
    yield {"event": "route", "intent": intent, "label": label}

    # ── c. Stream LLM response ────────────────────────────────────────────────
    # Build system prompt with optional tool context
    system_content = final["system_prompt"]
    calendar_result = final.get("context", {}).get("calendar_result")
    finance_result = final.get("context", {}).get("finance_result")
    mail_result = final.get("context", {}).get("mail_result")
    files_result = final.get("context", {}).get("files_result")
    habits_result = final.get("context", {}).get("habits_result")

    if calendar_result:
        system_content += f"\n\n[Contexto de calendario obtenido:]\n{calendar_result}"
    if finance_result:
        system_content += f"\n\n[Operación de finanzas completada:]\n{finance_result}"
    if mail_result:
        system_content += f"\n\n[Operación de correo completada:]\n{mail_result}"
    if files_result:
        system_content += f"\n\n[Contexto de documentos recuperado mediante RAG:]\n{files_result}"
    if habits_result:
        system_content += f"\n\n[Gestión de tareas completada/obtenida:]\n{habits_result}"

    # Prepare messages: history + system + current message
    lc_messages = []
    lc_messages.append({"role": "system", "content": system_content})
    
    if history:
        # Add history messages (filtered or limited if necessary)
        for msg in history:
            lc_messages.append(msg)
            
    lc_messages.append({"role": "user",   "content": message})
    
    tier = TaskTier(final.get("tier", "standard"))

    try:
        async for chunk in gateway.stream(lc_messages, tier=tier):
            if chunk:
                yield {"content": chunk}
    except AllProvidersExhausted as exc:
        logger.error("Supervisor stream – all providers exhausted: %s", exc)
        yield {"content": "\n\n⚠️ No se pudo conectar con ningún proveedor de IA en este momento."}
