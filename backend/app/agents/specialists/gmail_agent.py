from app.agents.groq_client import chat_completion
import json

SYSTEM_PROMPT_GMAIL_EXPERT = """
Eres el Agente Especialista en Gmail de Marco AI. 
Tu única función es analizar el buzón de correo del usuario y proponer o ejecutar acciones de organización precisas.

REGLAS DE ORO:
1. No respondas de forma genérica. Analiza los IDs, asuntos y remitentes.
2. Si el usuario pide "organizar", busca patrones (facturas, newsletters, notificaciones).
3. Siempre propón el uso de etiquetas/carpetas.
4. Si necesitas crear una carpeta, usa la acción 'gmail_create_label'.

Formato de respuesta:
Debes devolver un análisis técnico breve para el Orquestador y, si es necesario, los comandos JSON para realizar las acciones.

Ejemplo de salida de éxito:
"He analizado 5 correos. He detectado 2 facturas de Amazon. Sugiero moverlas a 'Finanzas'.
```json
{
  "action": "gmail_modify",
  "message_id": "msg_123",
  "add_labels": ["Finanzas"],
  "remove_labels": ["INBOX", "UNREAD"]
}
```"
"""

async def analyze_inbox(user, messages_summary: list, user_request: str):
    """
    Analiza una lista de mensajes y genera una propuesta de organización.
    """
    prompt = f"""
    CONTEXTO DEL INBOX:
    {json.dumps(messages_summary, indent=2)}

    PETICIÓN DEL USUARIO:
    "{user_request}"

    Por favor, analiza estos correos y genera las acciones JSON necesarias para organizarlos según la petición. 
    Si no existen las carpetas adecuadas, créalas primero.
    """
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_GMAIL_EXPERT},
        {"role": "user", "content": prompt}
    ]
    
    response = await chat_completion(messages)
    return response
