import json
import re
from app.agents.groq_client import chat_completion
from app.agents.prompts import SYSTEM_PROMPT_ORCHESTRATOR
from app.services.google_calendar import list_upcoming_events, create_event
from app.services.google_gmail import list_unread_messages, create_draft
from app.rag.engine import search, add_document

async def process_message(user, user_message: str):
    """
    Orquestador principal del Agente. Recibe un mensaje, decide si requiere acción
    y genera una respuesta.
    """
    system_msg = SYSTEM_PROMPT_ORCHESTRATOR.replace("{user_name}", user.name.split(" ")[0])
    
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_message}
    ]
    
    max_loops = 3
    for _ in range(max_loops):
        # 1. Obtenemos la decisión de Groq
        response = await chat_completion(messages)
        
        # Buscar JSON en la respuesta (Tool Calling manual)
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        
        if not json_match:
            # Si no hay JSON, es una respuesta conversacional final
            return response
            
        try:
            action_data = json.loads(json_match.group(1))
            action = action_data.get("action")
            
            # Ejecutar Acción y proveer contexto de vuelta a Groq
            context_result = "La acción se ejecutó pero no devolvió resultados."
            
            if action == "calendar_list":
                events = list_upcoming_events(user)
                if not events:
                    context_result = "No hay eventos próximos."
                else:
                    context_result = "Eventos próximos:\n" + "\n".join([f"- {e.get('summary')} ({e['start'].get('dateTime', e['start'].get('date'))})" for e in events])
                    
            elif action == "calendar_create":
                evt = create_event(user, action_data["summary"], action_data["start_time"], action_data["end_time"])
                context_result = f"Evento '{action_data['summary']}' creado exitosamente."
                
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
                await add_document(user.id, action_data["content"], action_data.get("metadata", {}))
                context_result = "Información guardada en mi memoria exitosamente. Ya la tendré en cuenta para la próxima vez y aparecerá en el Dashboard."
            
            # 2. Re-inyectar en el contexto para el siguiente loop
            messages.append({"role": "assistant", "content": response})
            messages.append({"role": "user", "content": f"SISTEMA (RESULTADO ACCIÓN):\n{context_result}\nSi necesitas hacer OTRA acción, genera un nuevo bloque JSON. Si ya tienes la respuesta definitiva para el usuario, responde en texto plano sin bloques de código."})
            
        except Exception as e:
            print(f"Error procesando acción: {e}")
            messages.append({"role": "assistant", "content": response})
            messages.append({"role": "user", "content": f"SISTEMA (ERROR): Hubo un fallo técnico ejecutando la herramienta: {str(e)}. Explícaselo al usuario."})
            
    return "Lo siento, tuve que realizar demasiadas acciones consecutivas y me he detenido. ¿Podrías reformular tu petición?"
