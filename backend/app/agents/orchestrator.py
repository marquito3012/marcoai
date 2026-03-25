from app.agents.groq_client import chat_completion
from app.agents.prompts import SYSTEM_PROMPT_ORCHESTRATOR
from app.services.google_calendar import list_upcoming_events, create_event
from app.services.google_gmail import list_unread_messages, list_messages, create_draft, send_email, list_labels, modify_message_labels, create_label
from app.rag.engine import search, add_document, delete_documents
import json

async def process_message(user, user_message: str, history: list = None):
    """
    Orquestador principal que maneja el loop de razonamiento y herramientas.
    """
    if history is None:
        history = []
         
    # --- Fase 1: Configuración del Contexto LLM ---
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
    
    max_loops = 3
    for _ in range(max_loops):
        # 1. Decisión de Groq
        response_text = await chat_completion(messages)
        messages.append({"role": "assistant", "content": response_text})
        
        # 2. ¿Hay comandos JSON? (Detección múltiple con finditer)
        import re
        json_pattern = r"```(?:json)?\s*(\{.*?\})\s*```"
        matches = list(re.finditer(json_pattern, response_text, re.DOTALL | re.IGNORECASE))
        
        if matches:
            results_list = []
            for match in matches:
                try:
                    json_str = match.group(1).strip()
                    action_data = json.loads(json_str)
                    
                    # Convertir a lista si es un solo objeto para procesar uniformemente
                    actions = action_data if isinstance(action_data, list) else [action_data]
                    
                    for entry in actions:
                        action = entry.get("action")
                        context_result = ""
                        
                        try:
                            if action == "calendar_list":
                                events = list_upcoming_events(user)
                                context_result = "No tienes eventos." if not events else "Eventos:\n" + "\n".join([f"- {e['summary']}" for e in events])
                            
                            elif action == "calendar_create":
                                create_event(user, entry["summary"], entry["start_time"], entry["end_time"])
                                context_result = f"Evento '{entry['summary']}' creado."
                            
                            elif action == "gmail_read":
                                msgs = list_messages(user, q=entry.get("query"), max_results=10)
                                context_result = "Correos encontrados:\n" + "\n".join([f"- ID: {m['id']} | Asunto: {m['subject']}" for m in msgs]) if msgs else "No se encontraron correos."

                            elif action == "gmail_send":
                                send_email(user, entry["to"], entry["subject"], entry["body"])
                                context_result = f"Correo enviado a {entry['to']}."

                            elif action == "gmail_modify":
                                modify_message_labels(user, entry.get("message_id"), entry.get("add_labels"), entry.get("remove_labels"))
                                context_result = f"Correo {entry.get('message_id')} modificado."

                            elif action == "gmail_labels":
                                labels = list_labels(user)
                                context_result = "Etiquetas: " + ", ".join([l['name'] for l in labels])

                            elif action == "gmail_create_label":
                                new_label = create_label(user, entry.get("name"))
                                context_result = f"Carpeta '{entry.get('name')}' creada (ID: {new_label['id']})."
                                    
                            elif action == "rag_search":
                                results = await search(user.id, entry["query"])
                                context_result = "Memoria:\n" + "\n".join([f"- {r['content']}" for r in results]) if results else "Sin resultados en memoria."

                            elif action == "rag_save":
                                doc_id = await add_document(user.id, entry["content"], entry.get("metadata", {}))
                                context_result = f"Guardado (ID: {doc_id})."

                            elif action == "rag_delete":
                                count = await delete_documents(user.id, entry.get("tipo"), entry.get("query"))
                                context_result = f"Eliminados {count} registros."
                            else:
                                context_result = f"Acción desconocida: {action}"
                        except Exception as e:
                            context_result = f"Error en acción {action}: {str(e)}"
                        
                        results_list.append(context_result)
                except Exception as e:
                    results_list.append(f"ERROR PARSING JSON BLOCK: {str(e)}")
            
            # Inyectar todos los resultados juntos
            final_context = "\n".join(results_list)
            messages.append({"role": "system", "content": f"SISTEMA (RESULTADOS): {final_context}"})
        else:
            # Si no hay JSON, es que el agente ya dio su respuesta final al usuario
            return response_text
            
    return response_text
