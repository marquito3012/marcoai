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
import json
from datetime import datetime, timezone, timedelta

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
    messages = [{"role": "system", "content": CLASSIFIER}]
    
    # Include a few history messages for context if available
    history = state.get("history", [])
    for msg in history[-3:]: # Just the last 3 for speed
        messages.append(msg)
        
    messages.append({"role": "user", "content": state["user_message"]})
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
    history = state.get("history", [])

    # Set calendar-specific prompt
    system_prompt = AGENT_PROMPTS["CALENDAR"].format(name=user_name)

    tool_result = None
    message_lower = user_message.lower()

    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()

            if not user or not user.google_calendar_token:
                return {
                    "system_prompt": system_prompt,
                    "tier": "standard",
                    "context": {"calendar_result": "No has conectado tu cuenta de Google Calendar."},
                }

            from app.services.calendar_service import CalendarService
            service = CalendarService(db, user)

            # Intent detection
            is_creation = any(kw in message_lower for kw in ["crea", "añade", "nuevo", "agrega", "pon", "agendar", "programa", "recordatorio", "recuérdame", "recuerdame"])
            is_listing = any(kw in message_lower for kw in ["ver", "lista", "próxim", "agenda", "qué tengo", "que tengo", "planes"])
            is_deletion = any(kw in message_lower for kw in ["borra", "elimina", "quita", "cancela"])

            if is_creation:
                # Use LLM to extract event details
                history_context = ""
                for m in history[-4:]:
                    history_context += f"{m['role'].upper()}: {m['content']}\n"
                
                now_str = datetime.now(timezone.utc).isoformat()
                
                extract_prompt = [
                    {"role": "system", "content": f"""
                    Eres un experto en extracción de datos para Google Calendar. 
                    Extrae los detalles del evento del mensaje del usuario y la conversación.
                    
                    REGLAS:
                    1. Fecha/Hora actual de referencia: {now_str}
                    2. Interpreta términos relativos como "mañana", "lunes que viene", "a las 5".
                    3. Si no se especifica duración, asume 1 hora.
                    4. Devuelve los campos: summary (str), start_datetime (ISO 8601), end_datetime (ISO 8601), location (str|null), description (str|null).
                    
                    Responde ÚNICAMENTE con un objeto JSON: {{"action": "create", "summary": "...", "start_datetime": "...", "end_datetime": "...", "location": "...", "description": "..."}}
                    Si no hay datos suficientes para crear un evento, responde: {{"action": "none"}}
                    """},
                    {"role": "user", "content": f"HISTORIAL:\n{history_context}\nMENSAJE ACTUAL: {user_message}"}
                ]
                
                try:
                    raw_json = await gateway.complete(extract_prompt, tier=TaskTier.FAST)
                    clean_json = raw_json.strip()
                    if "```json" in clean_json: clean_json = clean_json.split("```json")[1].split("```")[0].strip()
                    elif "```" in clean_json: clean_json = clean_json.split("```")[1].split("```")[0].strip()
                    
                    data = json.loads(clean_json)
                    if data.get("action") == "create" and data.get("summary"):
                        start_dt = datetime.fromisoformat(data["start_datetime"].replace("Z", "+00:00"))
                        end_dt = datetime.fromisoformat(data["end_datetime"].replace("Z", "+00:00"))
                        
                        created = await service.create_event(
                            summary=data["summary"],
                            start_dt=start_dt,
                            end_dt=end_dt,
                            description=data.get("description"),
                            location=data.get("location"),
                        )
                        tool_result = f"✅ Evento **{created['summary']}** creado para el {start_dt.strftime('%d/%m a las %H:%M')}."
                except Exception as e:
                    logger.error("Error extraction calendar: %s", e)
                    tool_result = "No pude extraer los detalles del evento correctamente. ¿Podrías ser más específico con la fecha y hora?"

            elif is_listing:
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

            elif is_deletion:
                # Similar extraction for deletion could be added here
                tool_result = "Para eliminar eventos, por ahora te recomiendo usar la pestaña de Agenda directamente."

    except Exception as exc:
        logger.error("Error en calendar_node: %s", exc, exc_info=True)
        tool_result = "Hubo un problema al acceder a tu calendario."

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

    # Determine if we should attempt habit creation/management
    is_habit_creation = any(kw in message_lower for kw in ["crea", "añade", "nuevo", "agrega", "pon", "guarda", "registrar"]) and \
                        any(kw in message_lower for kw in ["hábito", "habito", "lista", "estos", "lo", "los", "plan", "ambos"])
    
    is_habit_deletion = any(kw in message_lower for kw in ["borra", "elimina", "quita", "suprime"]) and \
                        any(kw in message_lower for kw in ["hábito", "habito"])

    try:
        async with AsyncSessionLocal() as db:
            from app.services.habits_service import HabitsService
            service = HabitsService(db, user_id)
            
            if is_habit_creation:
                # Use the LLM to extract structured data from the context
                history_context = ""
                # We take the last 4 messages to ensure we have the plan and the user's confirmation
                for m in history[-4:]: 
                    history_context += f"{m['role'].upper()}: {m['content']}\n"
                
                extract_prompt = [
                    {"role": "system", "content": """
                    Eres un asistente experto en extracción de datos. 
                    Tu objetivo es extraer una lista de hábitos a crear a partir de la conversación.
                    
                    REGLAS:
                    1. Identifica el nombre del hábito (ej: "Salir a correr", "Hacer skate").
                    2. Identifica los días programados (0=Lunes, 1=Martes, 2=Miércoles, 3=Jueves, 4=Viernes, 5=Sábado, 6=Domingo).
                    3. IGNORA explícitamente días de descanso, relax u off. No los incluyas en los días del hábito.
                    4. Si el usuario dice "añade ambos" o "crea el plan", busca en el último mensaje del ASISTENTE el plan propuesto.
                    
                    Responde ÚNICAMENTE con un array JSON: [{"name": "...", "days": "0,2,4"}, ...]
                    Si no hay hábitos claros, responde: []
                    """},
                    {"role": "user", "content": f"HISTORIAL:\n{history_context}\nMENSAJE ACTUAL: {user_message}"}
                ]
                
                try:
                    logger.info("HabitsNode: Requesting LLM extraction...")
                    raw_json = await gateway.complete(extract_prompt, tier=TaskTier.FAST)
                    logger.info("HabitsNode: Raw LLM output: %s", raw_json)
                    
                    # Clean markdown if present
                    clean_json = raw_json.strip()
                    if "```json" in clean_json:
                        clean_json = clean_json.split("```json")[1].split("```")[0].strip()
                    elif "```" in clean_json:
                        clean_json = clean_json.split("```")[1].split("```")[0].strip()
                    
                    logger.info("HabitsNode: Cleaned JSON for parsing: %s", clean_json)
                    extracted = json.loads(clean_json)
                    logger.info("HabitsNode: Parsed extracted data: %s", extracted)
                    
                    if isinstance(extracted, list) and len(extracted) > 0:
                        created = []
                        for item in extracted:
                            name = item.get("name", "Nuevo Hábito").capitalize()
                            days = item.get("days", "0,1,2,3,4,5,6")
                            logger.info("HabitsNode: Calling service.create_habit for '%s'", name)
                            habit = await service.create_habit(name=name, target_days=days)
                            # Convert day numbers to names for the confirmation message
                            day_names = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
                            h_days_list = [day_names[int(d)] for d in days.split(",") if d.strip().isdigit()]
                            created.append(f"{habit.name} ({', '.join(h_days_list)})")
                        
                        tool_result = f"✅ He creado con éxito los siguientes hábitos: {'; '.join(created)}."
                        logger.info("HabitsNode: Created %d habits", len(created))
                    else:
                        logger.info("HabitsNode: No habits found in LLM extraction.")
                except Exception as e:
                    logger.error("HabitsNode: LLM extraction failed: %s", e)
                    # Simple regex fallback if LLM fails
                    import re
                    name_match = re.search(r'(?:hábito|habito) (?:de |: |que )?(.+?)(?:\s+(?:los |el |cada |$))', message_lower)
                    if name_match:
                        name = name_match.group(1).strip().capitalize()
                        habit = await service.create_habit(name=name)
                        tool_result = f"✅ He añadido el hábito: **{habit.name}**."

            elif is_habit_deletion:
                import re
                name_match = re.search(r'(?:borra|elimina|quita) (?:el |los )?(?:hábito |habito )?(.+)', message_lower)
                if name_match:
                    name_to_delete = name_match.group(1).strip()
                    habits = await service.get_habits()
                    target = next((h for h in habits if h.name.lower() in name_to_delete.lower() or name_to_delete.lower() in h.name.lower()), None)
                    if target:
                        await service.delete_habit(target.id)
                        tool_result = f"🗑️ He eliminado el hábito: **{target.name}**."
                    else:
                        tool_result = f"❌ No he encontrado ningún hábito que coincida con '{name_to_delete}'."
            
            # If no action was taken but we are in habits node, maybe just list them
            if not tool_result:
                habits = await service.get_habits()
                if habits:
                    h_list = [f"• {h.name} ({h.target_days})" for h in habits]
                    tool_result = "🔥 **Tus hábitos actuales:**\n" + "\n".join(h_list)
                else:
                    tool_result = "No tienes hábitos registrados. Pídeme 'Crea el hábito de leer' para empezar."

    except Exception as e:
        logger.error("Error in habits_node: %s", e)
        tool_result = f"⚠️ Error procesando la solicitud de hábitos: {e}"

    return {
        "system_prompt": system_prompt,
        "tier": "standard",
        "context": {"habits_result": tool_result} if tool_result else {},
    }
