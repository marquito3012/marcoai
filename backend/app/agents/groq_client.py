import groq
import openai
import google.generativeai as genai
from app.config import settings
import edge_tts
import io

# Clientes principales
groq_client = groq.AsyncGroq(api_key=settings.GROQ_API_KEY)

# Cliente de respaldo (OpenRouter)
or_client = None
if settings.OPENROUTER_API_KEY:
    or_client = openai.AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=settings.OPENROUTER_API_KEY,
    )

# Cliente de respaldo (Google AI Studio)
if settings.GOOGLE_API_KEY:
    genai.configure(api_key=settings.GOOGLE_API_KEY)

async def chat_completion(messages: list[dict], model: str = "llama-3.3-70b-versatile", temperature: float = 0.7, max_tokens: int = 1000):
    """
    Rotación en 3 niveles:
    1. Groq (Llama 3.3 70b)
    2. Google AI Studio (Gemini 2.0 Flash)
    3. OpenRouter (Llama 3 8b Free)
    """
    # NIVEL 1: Groq
    try:
        response = await groq_client.chat.completions.create(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=10.0  # Tiempo límite corto para rotar rápido
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"⚠️ Nivel 1 (Groq) falló, rotando a Nivel 2 (Google)... Error: {e}")
        return await chat_completion_google(messages, temperature, max_tokens)

async def chat_completion_google(messages: list[dict], temperature: float = 0.7, max_tokens: int = 1000):
    """
    NIVEL 2: Google AI Studio (Gemini 2.0 Flash)
    """
    if not settings.GOOGLE_API_KEY:
        print("⚠️ Google API Key no configurada, saltando a Nivel 3...")
        return await chat_completion_openrouter(messages, "meta-llama/llama-3-8b-instruct:free", temperature, max_tokens, level=3)

    try:
        # Convertir mensajes (OpenAI format) a Google format (history + content)
        history = []
        system_instruction = ""
        msg_list = list(messages)
        
        for m in msg_list:
            if m.get("role") == "system":
                system_instruction += m.get("content", "") + "\n"
        
        # Filtramos para el chat (solo user/model)
        chat_msgs = [m for m in msg_list if m.get("role") in ["user", "assistant"]]
        for m in chat_msgs[:-1]:
            role = "user" if m.get("role") == "user" else "model"
            history.append({"role": role, "parts": [m.get("content", "")]})
        
        last_message = chat_msgs[-1].get("content", "") if chat_msgs else "Hola"

        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash", 
            system_instruction=system_instruction.strip() or None
        )
        
        chat = model.start_chat(history=history)
        response = await chat.send_message_async(last_message)
        return response.text
    except Exception as e:
        print(f"⚠️ Nivel 2 (Google) falló, rotando a Nivel 3 (OpenRouter)... Error: {e}")
        return await chat_completion_openrouter(messages, "", temperature, max_tokens, level=3)

async def chat_completion_openrouter(messages: list[dict], model: str, temperature: float, max_tokens: int, level: int):
    """
    Maneja los niveles 2 y 3 vía OpenRouter.
    """
    if not or_client:
        return "Error: OpenRouter no configurado."

    models_to_try = [
        "stepfun/step-3.5-flash:free",
        "qwen/qwen3-next-80b-a3b-instruct:free",
        "meta-llama/llama-3.3-70b-instruct:free"
    ]
    
    for current_model in models_to_try:
        try:
            print(f"🔄 Probando Nivel 3 (OpenRouter) con modelo: {current_model}...")
            response = await or_client.chat.completions.create(
                model=current_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                extra_headers={"X-Title": "Marco AI"},
                timeout=8.0  # Muy corto para probar varios
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"⚠️ Modelo {current_model} falló en Nivel 3: {e}")
            continue

    return "Lo siento, todos los proveedores de IA están saturados en este momento."

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
