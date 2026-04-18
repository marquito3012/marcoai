"""
MarcoAI – LangGraph Node Functions

Each function is a LangGraph node that:
  • Receives the full AgentState dict
  • Returns a partial dict with ONLY the keys it modifies (LangGraph merges)

Nodes:
  supervisor_node  → classifies intent via FAST LLM tier (cheap, < 20 tokens)
  route            → conditional edge function: intent → next node name
  general_chat_node, calendar_node, finance_node, mail_node,
  files_node, habits_node → set system_prompt and tier for the response phase

Calendar node (Fase 6):
  • Now uses LangChain tools for Google Calendar CRUD operations
  • Tools are passed to the LLM for function calling
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool

from app.agents.prompts import AGENT_PROMPTS, CLASSIFIER
from app.agents.states import AgentState
from app.agents.tools.calendar_tools import CALENDAR_TOOLS
from app.agents.tools.finance_tools import FINANCE_TOOLS
from app.services.llm_gateway import TaskTier, gateway

logger = logging.getLogger(__name__)

VALID_INTENTS = {"GENERAL_CHAT", "CALENDAR", "FINANCE", "MAIL", "FILES", "HABITS"}

_INTENT_TO_NODE: dict[str, str] = {
    "GENERAL_CHAT": "general_chat",
    "CALENDAR":     "calendar",
    "FINANCE":      "finance",
    "MAIL":         "mail",
    "FILES":        "files",
    "HABITS":       "habits",
}


# ══════════════════════════════════════════════════════════════════════════════
#  Supervisor node – intent classification
# ══════════════════════════════════════════════════════════════════════════════

async def supervisor_node(state: AgentState) -> dict:
    """
    Classify the user's message into one of the six intent categories using
    the cheapest (FAST) LLM tier – typically <100ms on Groq.
    """
    messages = [
        {"role": "system", "content": CLASSIFIER},
        {"role": "user",   "content": state["user_message"]},
    ]
    try:
        raw    = await gateway.complete(messages, tier=TaskTier.FAST, max_tokens=20, temperature=0.0)
        intent = raw.strip().upper().split()[0]          # take first word only
        if intent not in VALID_INTENTS:
            intent = "GENERAL_CHAT"
    except Exception as exc:
        logger.warning("Intent classification failed (%s). Defaulting to GENERAL_CHAT.", exc)
        intent = "GENERAL_CHAT"

    logger.info("Supervisor → %s  (user=%s)", intent, state.get("user_name"))
    return {"intent": intent}


def route(state: AgentState) -> str:
    """
    Conditional edge function.  Maps the intent to the name of the next node.
    Falls back to 'general_chat' if intent is somehow unrecognised.
    """
    return _INTENT_TO_NODE.get(state.get("intent", ""), "general_chat")


# ══════════════════════════════════════════════════════════════════════════════
#  Agent nodes – set system prompt and LLM tier for the response phase
#  (actual streaming happens in supervisor.py::supervisor_stream, not here)
# ══════════════════════════════════════════════════════════════════════════════

def _make_node(intent_key: str, tier: str = "standard"):
    """Factory that returns an async node function for any intent key."""
    async def _node(state: AgentState) -> dict:
        return {
            "system_prompt": AGENT_PROMPTS[intent_key].format(
                name=state.get("user_name", "usuario")
            ),
            "tier": tier,
        }
    _node.__name__ = f"{intent_key.lower()}_node"
    return _node


general_chat_node = _make_node("GENERAL_CHAT", tier="standard")
# mail_node placeholder removed

# files_node placeholder removed

# habits_node placeholder removed


# ══════════════════════════════════════════════════════════════════════════════
#  Calendar node – with tool execution (Fase 6)
# ══════════════════════════════════════════════════════════════════════════════

async def calendar_node(state: AgentState) -> dict:
    """
    Calendar agent node with Google Calendar tool integration.
    """
    from app.db.base import AsyncSessionLocal
    from app.db.models import User
    from sqlalchemy import select

    user_message = state.get("user_message", "")
    user_id = state.get("user_id")
    user_name = state.get("user_name", "usuario")

    # Set calendar-specific prompt
    system_prompt = AGENT_PROMPTS["CALENDAR"].format(name=user_name)

    # Try to execute calendar tools if user has tokens
    tool_result = None
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()

            if user and user.google_calendar_token:
                if any(kw in user_message.lower() for kw in ["ver", "lista", "próxim", "agenda", "evento", "reunión", "reunion"]):
                    from app.services.calendar_service import CalendarService
                    service = CalendarService(db, user)
                    events = await service.list_events(
                        end_date=datetime.now(timezone.utc) + timedelta(days=30),
                        max_results=10
                    )

                    if events:
                        lines = ["📅 **Próximos eventos:**\n"]
                        for event in events:
                            start = event.get("start", {})
                            date_str = start.get("dateTime", start.get("date", "Sin fecha"))
                            if "T" in date_str:
                                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                                date_str = dt.strftime("%d/%m %H:%M")
                            summary = event.get("summary", "Sin título")
                            lines.append(f"• **{summary}** – {date_str}")
                        tool_result = "\n".join(lines)
                    else:
                        tool_result = "No tienes eventos programados en los próximos 30 días."
    except Exception as exc:
        logger.error("Error crítico en calendar_node: %s", exc, exc_info=True)
        # We provide a clean, non-technical context to the LLM so it can answer helpfully
        tool_result = "No se pudo recuperar información del calendario debido a un problema técnico interno de sincronización."

    if not tool_result:
        tool_result = "No se pudo recuperar información del calendario. Es posible que el usuario necesite volver a iniciar sesión para renovar permisos o que no tenga eventos próximos."

    return {
        "system_prompt": system_prompt,
        "tier": "standard",
        "context": {"calendar_result": tool_result} if tool_result else {},
    }


# ══════════════════════════════════════════════════════════════════════════════
#  Finance node – with tool execution (Fase 7)
# ══════════════════════════════════════════════════════════════════════════════

async def finance_node(state: AgentState) -> dict:
    """
    Finance agent node with tool integration for expense/income tracking.

    This node:
    1. Sets the system prompt for finance operations
    2. Detects intent from user message (register expense, check balance, etc.)
    3. Executes finance tools automatically when applicable
    4. Returns context for the streaming response
    """
    from app.db.base import AsyncSessionLocal
    from app.db.models import User
    from sqlalchemy import select

    user_message = state.get("user_message", "")
    user_id = state.get("user_id")
    user_name = state.get("user_name", "usuario")

    # Set finance-specific prompt
    system_prompt = AGENT_PROMPTS["FINANCE"].format(name=user_name)

    tool_result = None
    message_lower = user_message.lower()

    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()

            if not user:
                return {
                    "system_prompt": system_prompt,
                    "tier": "standard",
                    "context": {},
                }

            from app.services.finance_service import FinanceService
            service = FinanceService(db, user.id)

            # Detect intent: Register expense
            expense_keywords = ["gasta", "gasté", "gastado", "pagado", "compré", "apunta", "anota"]
            if any(kw in message_lower for kw in expense_keywords):
                # Try to extract amount and category from message
                import re
                amount_match = re.search(r'(\d+[,.]\d{1,2})\s*€?', message_lower)
                amount = float(amount_match.group(1).replace(",", ".")) if amount_match else None

                if amount:
                    # Detect category
                    category = "otros"
                    category_keywords = {
                        "alimentacion": ["comida", "supermercado", "restaurante", "almuerzo", "cenar"],
                        "transporte": ["gasolina", "gasolinera", "metro", "bus", "taxi", "coche"],
                        "ocio": ["cine", "fiesta", "concierto", "juego", "netflix", "spotify"],
                        "tecnologia": ["ordenador", "móvil", "software", "app", "suscripción"],
                        "salud": ["farmacia", "médico", "gimnasio", "deporte"],
                        "hogar": ["alquiler", "luz", "agua", "internet", "comunidad"],
                    }
                    for cat, keywords in category_keywords.items():
                        if any(kw in message_lower for kw in keywords):
                            category = cat
                            break

                    # Extract description (rest of message after amount)
                    description = user_message
                    if amount_match:
                        desc_parts = user_message.split(amount_match.group(0), 1)
                        if len(desc_parts) > 1:
                            description = desc_parts[1].strip()

                    transaction = await service.create_transaction(
                        tx_type="expense",
                        amount=amount,
                        category=category,
                        description=description or "Gasto registrado",
                    )

                    tool_result = (
                        f"✅ **Gasto registrado:** {amount:.2f}€ en **{category}**\n\n"
                        f"📝 {transaction.description}"
                    )

            # Detect intent: Check balance
            elif any(kw in message_lower for kw in ["balance", "cuánto dinero", "cuanto dinero", "gastado este mes", "ingresado este mes"]):
                balance = await service.get_monthly_balance()
                month_name = [
                    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
                ][balance["month"] - 1]

                emoji = "🟢" if balance["balance"] >= 0 else "🔴"
                tool_result = (
                    f"{emoji} **Balance de {month_name}**\n\n"
                    f"| Concepto | Cantidad |\n"
                    f"|----------|----------|\n"
                    f"| Ingresos | {balance['income']:,.2f} € |\n"
                    f"| Gastos   | {balance['expenses']:,.2f} € |\n"
                    f"| **Balance** | **{balance['balance']:,.2f} €** |\n\n"
                    f"💡 Tasa de ahorro: {balance['savings_rate']:.1f}%"
                )

            # Detect intent: Expenses by category
            elif any(kw in message_lower for kw in ["categoría", "categoria", "distribución", "distribucion", "gráfica", "grafica"]):
                categories = await service.get_expenses_by_category()
                if categories:
                    lines = ["📊 **Gastos por categoría:**\n"]
                    total = sum(c["total"] for c in categories)
                    for cat in categories[:5]:  # Top 5
                        percentage = (cat["total"] / total * 100) if total > 0 else 0
                        lines.append(f"• **{cat['category'].capitalize()}**: {cat['total']:,.2f}€ ({percentage:.0f}%)")
                    tool_result = "\n".join(lines)
                else:
                    tool_result = "No hay gastos registrados este mes para analizar por categoría."

            # Detect intent: List recent transactions
            elif any(kw in message_lower for kw in ["últimos", "ultimos", "recientes", "historial", "lista de"]):
                transactions = await service.list_transactions(limit=5)
                if transactions:
                    lines = ["📋 **Últimas transacciones:**\n"]
                    for tx in transactions:
                        emoji = "💰" if tx.type == "income" else "💸"
                        sign = "+" if tx.type == "income" else "-"
                        date_str = tx.date.strftime("%d/%m")
                        lines.append(f"{emoji} {date_str}: {sign}{tx.amount:,.2f}€ - {tx.description}")
                    tool_result = "\n".join(lines)
                else:
                    tool_result = "No hay transacciones recientes."

    except Exception as exc:
        logger.warning("Finance tool execution failed: %s", exc)
        tool_result = None

    return {
        "system_prompt": system_prompt,
        "tier": "standard",
        "context": {"finance_result": tool_result} if tool_result else {},
    }

# ══════════════════════════════════════════════════════════════════════════════
#  Mail node – with tool execution (Fase 8)
# ══════════════════════════════════════════════════════════════════════════════

async def mail_node(state: AgentState) -> dict:
    """
    Mail agent node with Gmail tool integration.

    This node:
    1. Sets the system prompt for mail operations
    2. Detects intent from user message (read inbox, send email)
    3. Executes gmail tools automatically when applicable
    4. Returns context for the streaming response
    """
    from app.db.base import AsyncSessionLocal
    from app.db.models import User
    from sqlalchemy import select

    user_message = state.get("user_message", "")
    user_id = state.get("user_id")
    user_name = state.get("user_name", "usuario")

    system_prompt = AGENT_PROMPTS["MAIL"].format(name=user_name)

    tool_result = None
    message_lower = user_message.lower()

    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()

            if user and user.google_calendar_token:
                from app.services.gmail_service import GmailService
                service = GmailService(db, user)

                # Intent: Buscar o leer correos (bandeja, inbox, no leídos)
                if any(kw in message_lower for kw in ["ver", "lee", "bandeja", "inbox", "correos", "emails", "mensajes", "recientes"]):
                    # Por defecto busca los 5 más recientes en INBOX
                    query = "in:inbox"
                    if "no leído" in message_lower or "no leido" in message_lower:
                        query += " is:unread"
                    
                    emails = await service.list_messages(query=query, max_results=5)

                    if emails:
                        lines = ["📧 **Últimos correos:**\n"]
                        for em in emails:
                            lines.append(f"• **{em['subject']}** - de {em['from']} ({em['date']})")
                        tool_result = "\n".join(lines)
                    else:
                        tool_result = "No tienes correos nuevos en tu bandeja."

                # Intent: Enviar un mensaje
                # Si es muy evidente (ej. "envía un correo a juan@gmail.com con asunto X...") 
                # dejaríamos al LLM organizar el envío a través de tools en Fase 8b.
                # Por ahora, extraemos al contexto que la intención es redactar.
                elif any(kw in message_lower for kw in ["envía", "manda", "redacta", "escribe", "responder"]):
                    # El LLM usará el prompt para pedir más datos o confirmar el borrador.
                    pass

    except Exception as exc:
        logger.warning("Mail tool execution failed: %s", exc)
        tool_result = None

    return {
        "system_prompt": system_prompt,
        "tier": "standard",
        "context": {"mail_result": tool_result} if tool_result else {},
    }


# ══════════════════════════════════════════════════════════════════════════════
#  Files node – with RAG execution (Fase 9)
# ══════════════════════════════════════════════════════════════════════════════

async def files_node(state: AgentState) -> dict:
    """
    Files agent node with Document RAG tool integration.
    """
    from app.db.base import AsyncSessionLocal
    
    user_message = state.get("user_message", "")
    user_id = state.get("user_id")
    user_name = state.get("user_name", "usuario")

    system_prompt = AGENT_PROMPTS["FILES"].format(name=user_name)

    tool_result = None
    message_lower = user_message.lower()

    try:
        if any(kw in message_lower for kw in ["busca", "archivo", "documento", "pdf", "encuentra", "nube", "sobre", "qué dice"]):
            async with AsyncSessionLocal() as db:
                from app.services.document_service import DocumentService
                service = DocumentService(db, user_id)
                results = await service.search_similar(query=user_message, top_k=5)
                
                if results:
                    lines = ["📂 **Información encontrada en tus documentos:**\n"]
                    for r in results:
                        lines.append(f"• {r}\n")
                    tool_result = "\n".join(lines)
    except Exception as exc:
        logger.warning("Files/RAG tool execution failed: %s", exc)
        tool_result = None

    return {
        "system_prompt": system_prompt,
        "tier": "intelligent",
        "context": {"files_result": tool_result} if tool_result else {},
    }


# ══════════════════════════════════════════════════════════════════════════════
#  Habits & Todos node (Fase 10)
# ══════════════════════════════════════════════════════════════════════════════

async def habits_node(state: AgentState) -> dict:
    """
    Habits agent node handling habit tracking and project breakdowns into To-Dos.
    """
    from app.db.base import AsyncSessionLocal
    import re
    from datetime import datetime
    
    user_message = state.get("user_message", "")
    user_id = state.get("user_id")
    user_name = state.get("user_name", "usuario")

    history = state.get("history", [])
    system_prompt = AGENT_PROMPTS["HABITS"].format(name=user_name)
    tool_result = None
    message_lower = user_message.lower()

    try:
        async with AsyncSessionLocal() as db:
            from app.services.habits_service import HabitsService
            service = HabitsService(db, user_id)
            
            # Intent: Crear hábito
            if any(kw in message_lower for kw in ["crea", "añade", "nuevo", "agrega", "pon", "guarda"]) and any(kw in message_lower for kw in ["hábito", "habito", "lista", "estos", "lo", "los"]):
                import re
                # 1. Intento de extracción simple vía Regex
                name_match = re.search(r'(?:hábito|habito) (?:de |: |que )?(.+?)(?:\s+(?:los |el |cada )|$)', message_lower)
                
                # 2. Si es vago o complejo, usamos el LLM para extraer del contexto
                if not name_match or any(kw in message_lower for kw in ["lo", "los", "estos", "plan"]):
                    history_context = ""
                    for m in history[-2:]: # Tomamos los últimos 2 para contexto inmediato
                        history_context += f"{m['role']}: {m['content']}\n"
                    
                    extract_prompt = [
                        {"role": "system", "content": "Eres un extractor de datos. Extrae hábitos y sus días (0=Lunes, 6=Domingo). Responde SOLO un JSON array: [{\"name\": \"...\", \"days\": \"0,1...\"}]."},
                        {"role": "user", "content": f"Contexto:\n{history_context}\nMensaje: {user_message}"}
                    ]
                    try:
                        raw_json = await gateway.complete(extract_prompt, tier=TaskTier.FAST)
                        # Limpiar posible markdown
                        if "```json" in raw_json:
                            raw_json = raw_json.split("```json")[1].split("```")[0].strip()
                        elif "```" in raw_json:
                            raw_json = raw_json.split("```")[1].split("```")[0].strip()
                        
                        extracted = json.loads(raw_json)
                        if isinstance(extracted, list) and len(extracted) > 0:
                            created_names = []
                            for item in extracted:
                                h_name = item.get("name", "Nuevo Hábito").capitalize()
                                h_days = item.get("days", "0,1,2,3,4,5,6")
                                habit = await service.create_habit(name=h_name, target_days=h_days)
                                created_names.append(habit.name)
                            tool_result = f"✅ He añadido los hábitos: {', '.join(created_names)}."
                        else:
                            # Fallback if JSON is empty or not list
                            name = name_match.group(1).strip() if name_match else "Nuevo Hábito"
                            habit = await service.create_habit(name=name.capitalize())
                            tool_result = f"✅ He añadido el hábito: **{habit.name}**."
                    except Exception as e:
                        logger.warning("LLM Extraction failed, falling back: %s", e)
                        name = name_match.group(1).strip() if name_match else "Nuevo Hábito"
                        habit = await service.create_habit(name=name.capitalize())
                        tool_result = f"✅ He añadido el hábito: **{habit.name}**."
                else:
                    # Regex simple funcionó
                    name = name_match.group(1).strip()
                    if name.endswith('.'): name = name[:-1]
                    
                    days_map = {"lunes": 0, "martes": 1, "miércoles": 2, "miercoles": 2, "jueves": 3, "viernes": 4, "sábado": 5, "sabado": 5, "domingo": 6}
                    target_days = []
                    for day_name, day_num in days_map.items():
                        if day_name in message_lower:
                            target_days.append(day_num)
                    
                    target_days_str = ",".join(map(str, sorted(list(set(target_days))))) if target_days else "0,1,2,3,4,5,6"
                    habit = await service.create_habit(name=name.capitalize(), target_days=target_days_str)
                    tool_result = f"✅ He añadido el hábito: **{habit.name}**."
                
            # Intent: Borrar hábito
            elif any(kw in message_lower for kw in ["borra", "elimina", "quita"]) and any(kw in message_lower for kw in ["hábito", "habito"]):
                import re
                name_match = re.search(r'(?:hábito|habito) (?:de )?(.+)', message_lower)
                if name_match:
                    target_name = name_match.group(1).strip()
                    if target_name.endswith('.'): target_name = target_name[:-1]
                    
                    habits = await service.get_habits()
                    target_habit = next((h for h in habits if target_name in h.name.lower() or h.name.lower() in target_name), None)
                    if target_habit:
                        await service.delete_habit(target_habit.id)
                        logger.info("Habit deleted: %s", target_habit.name)
                        tool_result = f"🗑️ He eliminado el hábito: **{target_habit.name}**."
                    else:
                        tool_result = f"No he encontrado ningún hábito llamado '{target_name}' para borrar."
                else:
                    tool_result = "No me has dicho qué hábito quieres borrar."
                    
            # Intent: Listar o Registrar completado
            elif any(kw in message_lower for kw in ["hábito", "habito", "completé", "hecho", "marcar", "lista", "cuales", "cuáles"]):
                habits = await service.get_habits()
                if habits:
                    lines = ["🔥 **Tus hábitos actuales:**\n"]
                    for h in habits:
                        lines.append(f"• {h.name}")
                    tool_result = "\n".join(lines) + "\n\n(Dime cuál quieres marcar como hecho hoy o hazlo desde la interfaz web)"
                else:
                    tool_result = "No tienes hábitos registrados. Pídeme 'Crea el hábito de leer' para empezar."
            
            else:
                # Fallback
                tool_result = "Gestiono tus hábitos y consistencia. Para añadir uno dime 'crea el hábito de...'."
                
            logger.info("Habits node tool_result: %s", tool_result)
                    
    except Exception as exc:
        logger.error("Habits tool execution failed: %s", exc, exc_info=True)
        tool_result = f"Hubo un error al gestionar tus hábitos: {str(exc)}"

    return {
        "system_prompt": system_prompt,
        "tier": "standard",
        "context": {"habits_result": tool_result} if tool_result else {},
    }

