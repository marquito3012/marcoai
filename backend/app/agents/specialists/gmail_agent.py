from app.agents.groq_client import chat_completion
import json

SYSTEM_PROMPT_GMAIL_EXPERT = """
Eres el Agente Especialista en Gmail de Marco AI. 
Tu función es analizar el buzón y generar un plan de organización EJECUTABLE.

REGLAS DE ORO:
1. SÉ DECISIVO. Si el usuario te pide organizar, no preguntes "¿Quieres que lo haga?". Genera las acciones necesarias.
2. Identifica patrones: facturas, newsletters, notificaciones de bancos, ocio, etc.
3. Propón el uso de etiquetas/carpetas. Si necesitas una carpeta nueva, usa la acción 'gmail_create_label'.
4. Para cada correo que quieras organizar, genera un bloque JSON 'gmail_modify'. 
5. Si un correo es basura o publicidad irrelevante, marca su ID para moverlo fuera de 'INBOX'.

Tu respuesta será procesada por el Orquestador de Marco AI. 
Debes incluir tu razonamiento lógico y todos los bloques JSON de comandos necesarios.
"""

async def analyze_inbox(user, messages_summary: list, user_request: str):
    """
    Analiza una lista de mensajes y genera una propuesta de organización.
    """
    prompt = f"""
    CONTEXTO DEL INBOX (Mensajes recientes y leídos):
    {json.dumps(messages_summary, indent=2)}

    PETICIÓN DEL USUARIO:
    "{user_request}"

    Por favor, analiza estos correos y genera las acciones JSON necesarias para organizarlos según la petición. 
    Asegúrate de incluir los IDs de los mensajes. 
    Si no existen las carpetas adecuadas, propón crearlas.
    """
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_GMAIL_EXPERT},
        {"role": "user", "content": prompt}
    ]
    
    response = await chat_completion(messages)
    return response
