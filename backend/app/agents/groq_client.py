import groq
from app.config import settings
import edge_tts
import io

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

async def speech_to_text(file_bytes: bytes, filename: str):
    """
    Usa Groq Whisper para transcribir audio a texto.
    """
    try:
        transcription = await client.audio.transcriptions.create(
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
