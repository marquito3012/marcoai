from app.agents.groq_client import chat_completion
from app.agents.prompts import SYSTEM_PROMPT_ORCHESTRATOR
from app.services.google_calendar import list_upcoming_events, create_event
from app.services.google_gmail import list_unread_messages, list_messages, create_draft, send_email, list_labels, modify_message_labels, create_label
from app.agents.specialists.gmail_agent import analyze_inbox as gmail_expert_analyze
from app.rag.engine import search, add_document, delete_documents
import json

async def process_message(user, user_message: str, history: list = None):
    """
    Orquestador principal que maneja el loop de razonamiento y herramientas.
    """
    if history is None:
        history = []
        
    # --- Fase 1: Análisis Multi-Agente (Handoff) ---
    email_keywords = ["organiza", "gestiona", "limpia", "triage", "clasifica", "correos", "inbox"]
    if any(k in user_message.lower() for k in email_keywords) and "calendario" not in user_message.lower():
        # Obtenemos visión amplia del inbox
        msgs = list_messages(user, max_results=20)
        if msgs:
            expert_response = await gmail_expert_analyze(user, msgs, user_message)
            # Inyectamos el análisis de forma que el orquestador entienda que es un REPORTE, no un comando directo
            user_message = f"PETICIÓN USUARIO: {user_message}\n\nREPORTE EXPERTO GMAIL:\n{expert_response}\n\nINSTRUCCIÓN: Basándote en el reporte, usa tus herramientas JSON para ejecutar el plan AHORA."

    # --- Fase 2: Configuración del Contexto LLM ---
    system_msg = SYSTEM_PROMPT_ORCHESTRATOR.replace("{user_name}", user.name or "Usuario")
    messages = [
        {"role": "system", "content": system_msg}
    ]
    
    # Inyectar memoria de la conversación (últimos 6 mensajes)
    for h in history[-6:]:
        if isinstance(h, dict) and h.get('role') in ['user', 'assistant'] and h.get('content'):
            messages.append({"role": h['role'], "content": h['content']})
            
    # Añadir el mensaje actual (posiblemente modificado por el experto)
    messages.append({"role": "user", "content": user_message})
    
    max_loops = 5
    for _ in range(max_loops):
        # 1. Decisión de Groq
        response_text = await chat_completion(messages)
        messages.append({"role": "assistant", "content": response_text})
        
        # 2. ¿Hay comando JSON? (Detección robusta con Regex)
        import re
        # Busca bloques ```json { ... } ``` o simplemente ``` { ... } ``` (insensible a mayúsculas)
        json_pattern = r"```(?:json)?\s*(\{.*?\})\s*```"
        match = re.search(json_pattern, response_text, re.DOTALL | re.IGNORECASE)
        
        if match:
            try:
                json_str = match.group(1).strip()
                action_data = json.loads(json_str)
                action = action_data.get("action")
                
                context_result = ""
                
                if action == "calendar_list":
                    events = list_upcoming_events(user)
                    if not events:
                        context_result = "No tienes eventos próximos."
                    else:
                        context_result = "Eventos próximos:\n" + "\n".join([f"- {e['summary']} ({e['start']})" for e in events])
                
                elif action == "calendar_create":
                    create_event(user, action_data["summary"], action_data["start_time"], action_data["end_time"])
                    context_result = f"Evento '{action_data['summary']}' creado exitosamente."
                
                elif action == "gmail_read":
                    # Ahora gmail_read puede ser más flexible
                    q = action_data.get("query")
                    msgs = list_messages(user, q=q, max_results=10)
                    if not msgs:
                        context_result = "No se encontraron correos."
                    else:
                        context_result = "Correos encontrados:\n" + "\n".join([f"- ID: {m['id']} | De: {m['from']} | Asunto: {m['subject']} | Resumen: {m['snippet']}" for m in msgs])

                elif action == "gmail_send":
                    if all(k in action_data for k in ["to", "subject", "body"]):
                        send_email(user, action_data["to"], action_data["subject"], action_data["body"])
                        context_result = f"Correo enviado a {action_data['to']} exitosamente."
                    else:
                        context_result = "ERROR: Faltan parámetros (to, subject o body) para enviar el correo."

                elif action == "gmail_modify":
                    msg_id = action_data.get("message_id")
                    add = action_data.get("add_labels")
                    remove = action_data.get("remove_labels")
                    if msg_id:
                        modify_message_labels(user, msg_id, add, remove)
                        context_result = f"Correo {msg_id} modificado (Etiquetas: +{add or []}, -{remove or []})."
                    else:
                        context_result = "ERROR: No hay ID de mensaje."

                elif action == "gmail_labels":
                    labels = list_labels(user)
                    context_result = "Etiquetas:\n" + "\n".join([f"- {l['name']} (ID: {l['id']})" for l in labels])

                elif action == "gmail_create_label":
                    name = action_data.get("name")
                    if name:
                        new_label = create_label(user, name)
                        context_result = f"Carpeta '{name}' creada (ID: {new_label['id']})."
                    else:
                        context_result = "ERROR: Sin nombre para la carpeta."
                        
                elif action == "rag_search":
                    results = await search(user.id, action_data["query"])
                    if not results:
                        context_result = "No encontré información relevante en mi memoria."
                    else:
                        context_result = "Resultados memoria:\n" + "\n".join([f"- {r['content']}" for r in results])

                elif action == "rag_save":
                    doc_id = await add_document(user.id, action_data["content"], action_data.get("metadata", {}))
                    context_result = f"Información guardada en memoria (ID: {doc_id})."

                elif action == "rag_delete":
                    count = delete_documents(user.id, action_data.get("tipo"), action_data.get("query"))
                    context_result = f"Se han eliminado {count} registros de la memoria."
                
                # Inyectar resultado de vuelta al loop
                messages.append({"role": "system", "content": f"SISTEMA (RESULTADO ACCIÓN): {context_result}"})
                
            except Exception as e:
                messages.append({"role": "system", "content": f"ERROR EJECUTANDO ACCIÓN: {str(e)}"})
        else:
            # Si no hay JSON, es que el agente ya dio su respuesta final al usuario
            return response_text
            
    return response_text
