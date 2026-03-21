import groq
from app.config import settings

client = groq.AsyncGroq(api_key=settings.GROQ_API_KEY)

async def chat_completion(messages: list[dict], model: str = "llama-3.3-70b-versatile", temperature: float = 0.7, max_tokens: int = 1000):
    """
    Función de utilidad para abstraer llamadas a la API de Groq.
    Si se desea "Tool Calling" nativo se puede extender aquí. 
    En esta primera versión usaremos Tool Calling manual para mayor control.
    """
    try:
        response = await client.chat.completions.create(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error llamando a Groq API: {e}")
        return "Lo siento, tuve un problema procesando tu solicitud con mi cerebro principal. Intenta de nuevo en unos segundos."
