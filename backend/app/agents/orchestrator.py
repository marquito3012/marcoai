from app.agents.groq_client import chat_completion
from app.agents.prompts import SYSTEM_PROMPT_ORCHESTRATOR
from app.services.google_calendar import list_upcoming_events, create_event, update_event, delete_event
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
    executed_hashes = set()
    for _ in range(max_loops):
        # 1. Decisión de Groq
        response_text = await chat_completion(messages)
        if not response_text:
            response_text = "Lo siento, no he podido procesar tu solicitud ahora mismo."
        
        print(f"🤖 LLM_RESPONSE: {response_text}")
        messages.append({"role": "assistant", "content": response_text})
        
        # 2. ¿Hay comandos JSON? (Detección múltiple con finditer)
        json_pattern = r"```(?:json)?\s*([\{\[].*?[\}\]])\s*```"
        matches = list(re.finditer(json_pattern, response_text, re.DOTALL | re.IGNORECASE))
        
        if matches:
            results_list = []
            for match in matches:
                try:
                    json_str = match.group(1).strip()
                    # Bloqueamos ejecución duplicada del mismo JSON en esta sesión
                    if json_str in executed_hashes:
                        continue
                    executed_hashes.add(json_str)
                    
                    action_data = json.loads(json_str)
                    
                    # Convertir a lista si es un solo objeto para procesar uniformemente
                    actions = action_data if isinstance(action_data, list) else [action_data]
                    
                    for entry in actions:
                        action = entry.get("action")
                        # Heurística: Si falta el action pero hay un nombre, inferimos según el contexto o el texto previo
                        if not action and "name" in entry:
                            if "marcar" in response_text.lower() or "hecho" in response_text.lower():
                                action = "habit_toggle"
                            elif "borrar" in response_text.lower() or "eliminar" in response_text.lower():
                                action = "habit_delete"
                            else:
                                action = "habit_add"
                            print(f"🔮 ORCHESTRATOR: Inferred action '{action}' from data: {entry}")

                        print(f"🛠️ ORCHESTRATOR: Processing tool '{action}' with data: {entry}")
                        context_result = ""
                        
                        try:
                            if action == "calendar_list":
                                events = list_upcoming_events(user)
                                context_result = "No tienes eventos." if not events else "Eventos:\n" + "\n".join([f"- {e['summary']}" for e in events])
                            
                            elif action == "calendar_create":
                                create_event(user, entry["summary"], entry["start_time"], entry["end_time"])
                                context_result = f"Evento '{entry['summary']}' creado."
                            
                            elif action == "calendar_update":
                                update_event(user, entry["event_id"], entry.get("summary"), entry.get("start_time"), entry.get("end_time"))
                                context_result = f"Evento '{entry.get('event_id')}' actualizado."
                            
                            elif action == "calendar_delete":
                                delete_event(user, entry["event_id"])
                                context_result = f"Evento '{entry.get('event_id')}' eliminado."
                            
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
                                results = await search(user.id, entry["query"], tipo=entry.get("tipo"))
                                context_result = "Memoria:\n" + "\n".join([f"- {r['content']}" for r in results]) if results else "Sin resultados en memoria."

                            elif action == "rag_save":
                                doc_id = await add_document(user.id, entry["content"], entry.get("metadata", {}))
                                context_result = f"Guardado (ID: {doc_id})."

                            elif action == "rag_delete":
                                tipo = entry.get("tipo")
                                query = entry.get("query")
                                if tipo == "gasto-mensual":
                                    count = await delete_documents(user.id, "gasto-mensual", query)
                                    count += await delete_documents(user.id, "suscripcion", query)
                                else:
                                    count = await delete_documents(user.id, tipo, query)
                                context_result = f"Se han eliminado {count} registros de la memoria correctamente." if count > 0 else "No se encontraron registros que coincidan para eliminar."
                            
                            # --- Specialized Tools mapping to RAG (3-Type Schema) ---
                            elif action == "money_add_monthly_expense":
                                amount = float(entry.get("amount") or entry.get("cost") or 0.0)
                                content = entry.get("content") or entry.get("name") or "Gasto mensual"
                                await add_document(user.id, content, {"tipo": "gasto-mensual", "amount": amount})
                                context_result = f"Gasto mensual de {amount}€ registrado."
                            
                            elif action == "money_add_oneoff_expense":
                                amount = float(entry.get("amount") or entry.get("cost") or 0.0)
                                content = entry.get("content") or entry.get("name") or "Gasto puntual"
                                await add_document(user.id, content, {"tipo": "gasto-puntual", "amount": amount})
                                context_result = f"Gasto puntual de {amount}€ registrado."

                            elif action == "money_add_income":
                                amount = float(entry.get("amount") or entry.get("monto") or 0.0)
                                content = entry.get("content") or "Ingreso"
                                await add_document(user.id, content, {"tipo": "ingreso", "amount": amount})
                                context_result = f"Ingreso de {amount}€ registrado."
                            
                            elif action == "money_add_sub":
                                amount = float(entry.get("cost") or entry.get("amount") or 0.0)
                                name = entry.get("name") or entry.get("content") or "Suscripción"
                                await add_document(user.id, f"Suscripción: {name}", {"tipo": "suscripcion", "nombre": name, "costo": amount, "renovacion": entry.get("period", "Mensual")})
                                context_result = f"Suscripción a {name} guardada."

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
                                name = entry.get("name") or entry.get("nombre") or "Nuevo hábito"
                                await add_document(user.id, f"Hábito: {name}", {"tipo": "habito", "nombre": name, "completado": False})
                                context_result = f"Hábito '{name}' añadido."
                                
                            elif action == "habit_toggle":
                                from app.rag.engine import toggle_habit
                                name = entry.get("name") or entry.get("nombre")
                                if name:
                                    new_state = await toggle_habit(user.id, name)
                                    context_result = f"Hábito '{name}' marcado como {'completado' if new_state else 'pendiente'}."
                                else:
                                    context_result = "Error: Falta el nombre del hábito para cambiar su estado."

                            elif action == "habit_delete":
                                name = entry.get("name") or entry.get("nombre")
                                count = await delete_documents(user.id, "habito", name)
                                context_result = f"Eliminados {count} hábitos."
                                
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
            
            # [SEGURIDAD] Sustituimos el JSON en el historial por un marcador para que el LLM no lo repita
            messages[-1]["content"] = re.sub(json_pattern, "[COMANDO PROCESADO POR EL SISTEMA]", response_text, flags=re.DOTALL | re.IGNORECASE)
            
            messages.append({"role": "system", "content": f"SISTEMA (RESULTADOS): {final_context}"})
    # 5. Respuesta Final (Limpieza y Humanización)
    # Si detectamos que el LLM aún intenta enviar JSON o la respuesta está vacía, forzamos humanización
    is_technical = bool(re.search(r"\{.*\"action\".*\}|\[.*\{\"action\".*\}\]", response_text, flags=re.DOTALL))
    clean_text = re.sub(json_pattern, "", response_text, flags=re.DOTALL).strip()
    
    if is_technical or not clean_text or clean_text.startswith(("{", "[")):
        messages.append({"role": "system", "content": "Acciones completadas con éxito. Responde al usuario de forma humana y natural en español confirmando lo hecho. PROHIBIDO usar JSON o bloques de código."})
        final_response = await chat_completion(messages)
        # Limpieza final extrema por si el LLM ignora la instrucción
        return re.sub(json_pattern, "", final_response, flags=re.DOTALL).strip() or "Hecho, todo listo."

    return clean_text
