import groq
import openai
from app.config import settings
import edge_tts
import io

# Clientes principales
groq_client = groq.AsyncGroq(api_key=settings.GROQ_API_KEY)

# Cliente de respaldo (OpenRouter usa el SDK de OpenAI)
or_client = None
if settings.OPENROUTER_API_KEY:
    or_client = openai.AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=settings.OPENROUTER_API_KEY,
    )

async def chat_completion(messages: list[dict], model: str = "llama-3.3-70b-versatile", temperature: float = 0.7, max_tokens: int = 1000):
    """
    Intenta llamar a Groq. Si falla por límites (429) o tokens, rota a OpenRouter.
    """
    # 1. Intento con Groq
    try:
        response = await groq_client.chat.completions.create(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content
    except Exception as e:
        error_msg = str(e).lower()
        # Verificar si es un error de cuota o límite
        if "rate_limit" in error_msg or "429" in error_msg or "token" in error_msg:
            print(f"⚠️ Groq límite alcanzado, rotando a OpenRouter... (Error: {e})")
            if or_client:
                return await chat_completion_openrouter(messages, temperature, max_tokens)
        
        print(f"❌ Error crítico en Groq API: {e}")
        return "Lo siento, tuve un problema procesando tu solicitud. Intenta de nuevo en unos segundos."

async def chat_completion_openrouter(messages: list[dict], temperature: float = 0.7, max_tokens: int = 1000):
    """
    Fallback usando OpenRouter (Gemini 2.0 Flash por defecto).
    """
    try:
        if not or_client:
            return "El proveedor de respaldo (OpenRouter) no está configurado."
            
        # Usamos un modelo estable y económico de respaldo
        fallback_model = "google/gemini-2.0-flash-001"
        response = await or_client.chat.completions.create(
            model=fallback_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            extra_headers={
                "HTTP-Referer": "https://marcoai.org", # Opcional para OpenRouter
                "X-Title": "Marco AI",
            }
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"❌ Error crítico en OpenRouter Fallback: {e}")
        return "Ambos proveedores (Groq y OpenRouter) han fallado. Por favor, revisa tus límites de API."

async def speech_to_text(file_bytes: bytes, filename: str):
    """
    Usa Groq Whisper para transcribir audio a texto.
    """
    try:
        transcription = await groq_client.audio.transcriptions.create(
            file=(filename, file_bytes),
            model="whisper-large-v3-turbo",
            response_format="verbose_json",
        )
        return transcription.text
    except Exception as e:
        print(f"Error transcribiendo audio con Groq: {e}")
        return None

async def text_to_speech(text: str):
    """
    Genera audio realista usando edge-tts.
    """
    try:
        # Usamos Álvaro o Elvira para máxima naturalidad
        voice = "es-ES-AlvaroNeural"
        communicate = edge_tts.Communicate(text, voice)
        
        audio_stream = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_stream.write(chunk["data"])
        
        audio_stream.seek(0)
        return audio_stream.read()
    except Exception as e:
        print(f"Error generando TTS con edge-tts: {e}")
        return None
