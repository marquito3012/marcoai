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
    
    # 1. Obtenemos la decisión inicial de Groq
    initial_response = await chat_completion(messages)
    
    # Buscar JSON en la respuesta (Tool Calling manual)
    json_match = re.search(r'```json\s*(.*?)\s*```', initial_response, re.DOTALL)
    
    if json_match:
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
            
            # 2. Generar respuesta final con el contexto añadido
            messages.append({"role": "assistant", "content": initial_response})
            messages.append({"role": "system", "content": f"RESULTADO DE LA ACCION:\n{context_result}\nResponde al usuario basándote únicamente en esto."})
            
            final_response = await chat_completion(messages)
            return final_response
            
        except Exception as e:
            print(f"Error procesando acción: {e}")
            return f"Hubo un error interno procesando esa acción. Detalles: {str(e)}"
            
    # Si no hay JSON, es una respuesta conversacional
    return initial_response
