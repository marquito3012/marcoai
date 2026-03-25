from app.agents.groq_client import chat_completion
from app.agents.prompts import SYSTEM_PROMPT_ORCHESTRATOR
from app.services.google_calendar import list_upcoming_events, create_event
from app.services.google_gmail import list_unread_messages, list_messages, create_draft, send_email, list_labels, modify_message_labels, create_label
from app.rag.engine import search, add_document, delete_documents
import json
import re

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
                            
                            # --- Specialized Tools mapping to RAG (3-Type Schema) ---
                            elif action == "money_add_monthly_expense":
                                await add_document(user.id, f"Gasto Mensual: {entry['content']} ({entry['amount']}€)", {"tipo": "gasto-mensual", "amount": float(entry["amount"])})
                                context_result = f"Gasto mensual de {entry['amount']}€ registrado."
                            
                            elif action == "money_add_oneoff_expense":
                                await add_document(user.id, f"Gasto Puntual: {entry['content']} ({entry['amount']}€)", {"tipo": "gasto-puntual", "amount": float(entry["amount"])})
                                context_result = f"Gasto puntual de {entry['amount']}€ registrado."

                            elif action == "money_add_income":
                                await add_document(user.id, f"Ingreso: {entry['content']} ({entry['amount']}€)", {"tipo": "ingreso", "monto": float(entry["amount"])})
                                context_result = f"Ingreso de {entry['amount']}€ registrado."
                            
                            elif action == "money_add_sub":
                                await add_document(user.id, f"Suscripción: {entry['name']}", {"tipo": "suscripcion", "nombre": entry["name"], "costo": float(entry["cost"]), "renovacion": entry.get("period", "Mensual")})
                                context_result = f"Suscripción a {entry['name']} guardada."

                            elif action == "calcular_presupuesto":
                                from app.rag.engine import get_connection
                                from datetime import datetime
                                now_prefix = datetime.now().strftime("%Y-%m")
                                conn = get_connection()
                                c = conn.cursor()
                                c.execute("SELECT metadata, created_at FROM documents WHERE user_id = ?", (user.id,))
                                balance = 0.0
                                for row in c.fetchall():
                                    m = json.loads(row[0])
                                    created_at = row[1] or ""
                                    t = m.get("tipo")
                                    if t == "ingreso":
                                        balance += float(m.get("monto") or 0)
                                    elif t == "gasto-mensual":
                                        balance -= float(m.get("amount") or 0)
                                    elif t == "gasto-puntual":
                                        if created_at.startswith(now_prefix):
                                            balance -= float(m.get("amount") or 0)
                                    elif t == "suscripcion":
                                        balance -= float(m.get("costo") or 0)
                                    # Compatibilidad
                                    elif t == "presupuesto":
                                        balance += float(m.get("restante") or 0)
                                conn.close()
                                context_result = f"TU BALANCE ACTUAL ES: {balance}€. (Incluye ingresos, gastos mensuales, suscripciones y gastos puntuales de este mes)."

                            elif action == "habit_add":
                                await add_document(user.id, f"Hábito: {entry['name']}", {"tipo": "habito", "nombre": entry["name"]})
                                context_result = f"Hábito '{entry['name']}' añadido."
                                
                            elif action == "meal_add":
                                await add_document(user.id, f"Comida: {entry['name']}", {"tipo": "comida", "nombre": entry["name"]})
                                context_result = f"Comida '{entry['name']}' añadida al plan."
                                
                            elif action == "buy_list_add":
                                await add_document(user.id, f"Compra: {entry['item']}", {"tipo": "compra", "items": [entry["item"]]})
                                context_result = f"Añadido '{entry['item']}' a la lista de la compra."
                                
                            elif action == "radar_add":
                                await add_document(user.id, f"Radar: {entry['title']}", {"tipo": "radar", "titulo": entry["title"], "fecha": entry.get("date", "Por confirmar"), "categoria": entry.get("category", "Interés")})
                                context_result = f"Añadido '{entry['title']}' al radar de ocio."
                                
                            elif action == "offer_add":
                                await add_document(user.id, f"Oferta: {entry['title']}", {"tipo": "oferta", "juego": entry["title"], "tienda": entry.get("store", "Internet"), "precio": entry["price"], "descuento": entry.get("discount", "")})
                                context_result = f"Oferta de '{entry['title']}' guardada."
                            
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
            # SI NO HAY JSON: Es la respuesta final. 
            # Limpiamos bloques sobrantes por si acaso (ej: ejemplos que el LLM ponga)
            clean_text = re.sub(json_pattern, "", response_text, flags=re.DOTALL).strip()
            if not clean_text:
                # Si se quedó vacío (solo era JSON), pedimos una confirmación final
                messages.append({"role": "system", "content": "Acciones completadas. Responde al usuario confirmando lo hecho en español, sin usar bloques de código."})
                confirm_res = await chat_completion(messages)
                return re.sub(json_pattern, "", confirm_res, flags=re.DOTALL).strip() or "Hecho."
            return clean_text
            
    # Si agotamos bucles y el último mensaje aún tiene JSON, lo limpiamos para el usuario
    final_clean = re.sub(r"```(?:json)?\s*(\{.*?\})\s*```", "", response_text, flags=re.DOTALL | re.IGNORECASE).strip()
    return final_clean or "Acciones procesadas correctamente."
