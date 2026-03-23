import json
import re
from app.agents.groq_client import chat_completion
from app.agents.prompts import SYSTEM_PROMPT_ORCHESTRATOR
from app.services.google_calendar import list_upcoming_events, create_event
from app.services.google_gmail import list_unread_messages, create_draft
from app.rag.engine import search, add_document, delete_documents

async def process_message(user, user_message: str, history: list = None):
    """
    Orquestador principal del Agente. Recibe un mensaje, decide si requiere acción
    y genera una respuesta.
    """
    if history is None:
        history = []
        
    system_msg = SYSTEM_PROMPT_ORCHESTRATOR.replace("{user_name}", user.name.split(" ")[0])
    
    messages = [
        {"role": "system", "content": system_msg}
    ]
    
    # Inyectar memoria de la conversación actual (limitada a 3 turnos / 6 mensajes)
    for h in history[-6:]:
        if isinstance(h, dict) and h.get('role') in ['user', 'assistant'] and h.get('content'):
            messages.append({"role": h['role'], "content": h['content']})
            
    messages.append({"role": "user", "content": user_message})
    
    max_loops = 3
    for _ in range(max_loops):
        # 1. Obtenemos la decisión de Groq
        response = await chat_completion(messages)
        
        # Buscar JSON en la respuesta (Tool Calling manual) más robusto
        json_str = None
        json_match = re.search(r'(?:```|""")(?:json)?\s*(\{.*?\})\s*(?:```|""")', response, re.DOTALL | re.IGNORECASE)
        
        if json_match:
            json_str = json_match.group(1)
        else:
            # Fallback a capturar cualquier bloque {} que contenga "action", codicioso para coger llaves anidadas
            alt_match = re.search(r'(\{\s*"action"\s*:.*\})', response, re.DOTALL)
            if alt_match:
                json_str = alt_match.group(1)
                
        if not json_str:
            # Si no hay JSON reconocible, asumimos que es una respuesta final conversacional
            return response
            
        try:
            action_data = json.loads(json_str)
            action = action_data.get("action")
            
            # Normalizar alucinaciones de LLM sobre el nombre de la acción
            if action in ["rag_create", "guardar_nota"]:
                action = "rag_save"
            
            # Ejecutar Acción y proveer contexto de vuelta a Groq
            context_result = "La acción se ejecutó pero no devolvió resultados."
            
            if action == "calendar_list":
                events = list_upcoming_events(user)
                if not events:
                    context_result = "No hay eventos próximos."
                else:
                    context_result = "Eventos próximos:\n" + "\n".join([f"- {e.get('summary')} ({e['start'].get('dateTime', e['start'].get('date'))})" for e in events])
                    
            elif action == "calendar_create":
                if all(k in action_data for k in ["summary", "start_time", "end_time"]):
                    evt = create_event(user, action_data["summary"], action_data["start_time"], action_data["end_time"])
                    context_result = f"Evento '{action_data['summary']}' creado exitosamente."
                else:
                    context_result = "ERROR: Faltan parámetros requeridos (summary, start_time o end_time) para crear el evento."
                
            elif action == "gmail_read":
                msgs = list_unread_messages(user)
                if not msgs:
                    context_result = "No tienes correos nuevos."
                else:
                    context_result = "Últimos correos:\n" + "\n".join([f"- De: {m['from']} | Asunto: {m['subject']} | Resumen: {m['snippet']}" for m in msgs])
                    
            elif action == "rag_search":
                results = await search(user.id, action_data["query"])
                if not results:
                    context_result = "No encontré nada en mis notas sobre eso."
                else:
                    context_result = "Resultados de mi memoria:\n" + "\n".join([f"- {r['content']}" for r in results])
                    
            elif action == "rag_save":
                content = action_data.get("content") or action_data.get("title", "Nota general")
                metadata = action_data.get("metadata", {})
                if not isinstance(metadata, dict):
                    metadata = {}
                    
                # Heurística en caso de que el LLM olvide el campo metadata
                content_lower = content.lower()
                if "tipo" not in metadata:
                    if "presupuesto" in content_lower or "dinero" in content_lower or "gastos" in content_lower:
                        metadata["tipo"] = "presupuesto"
                    elif "suscripci" in content_lower or "netflix" in content_lower:
                        metadata["tipo"] = "suscripcion"
                    elif "hábito" in content_lower or "habito" in content_lower:
                        metadata["tipo"] = "habito"
                        
                await add_document(user.id, content, metadata)
                context_result = "Información guardada en mi memoria exitosamente. Ya la tendré en cuenta para la próxima vez y aparecerá en el Dashboard."
                
            elif action == "rag_delete":
                tipo = action_data.get("tipo")
                query = action_data.get("query")
                deleted = await delete_documents(user.id, tipo=tipo, query=query)
                if deleted > 0:
                    context_result = f"Se han eliminado {deleted} registros de tu memoria con éxito."
                else:
                    context_result = "No se encontró ningún registro que coincidiera con la solicitud para eliminar."
            
            # 2. Re-inyectar en el contexto para el siguiente loop
            messages.append({"role": "assistant", "content": response})
            messages.append({"role": "user", "content": f"SISTEMA (RESULTADO ACCIÓN):\n{context_result}\nSi necesitas hacer OTRA acción, genera un nuevo bloque JSON. Si ya tienes la respuesta definitiva para el usuario, responde en texto plano sin bloques de código."})
            
        except Exception as e:
            print(f"Error procesando acción: {e}")
            messages.append({"role": "assistant", "content": response})
            messages.append({"role": "user", "content": f"SISTEMA (ERROR): Hubo un fallo técnico ejecutando la herramienta: {str(e)}. Explícaselo al usuario."})
            
    return "Lo siento, tuve que realizar demasiadas acciones consecutivas y me he detenido. ¿Podrías reformular tu petición?"
