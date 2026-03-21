import groq
from app.config import settings
from fastapi import HTTPException

# Inicializar cliente Groq
client = groq.AsyncGroq(api_key=settings.GROQ_API_KEY)

# Si la API de Groq no dispone de un endpoint para embeddings, hay que usar embeddings locales
# Opcional: sentence-transformers para uso en caso Groq no de embeddings.
# Aquí implementaremos una llamada asumiendo que el modelo Llama3 text-embedding soportado (o usar API Groq de embeddings)
# Nota: A fecha de hoy para Groq API, no todos los tiers soportan endpoints de embeddings `/v1/embeddings`. Si falla, requerimos local.

async def generate_embedding(text: str) -> list[float]:
    """Genera el embedding usando la API de Groq si está disponible."""
    try:
         # Intento de llamada a embeddings de Groq (asumiendo que está soportado)
         # O usar BAAI/bge-small-en-v1.5 en un modelo disponible en Groq.
         response = await client.embeddings.create(
            model="nomic-embed-text-v1_5", # default si lo tienen, o llama3 text embed
            input=text,
            encoding_format="float"
         )
         return response.data[0].embedding
    except Exception as e:
         print(f"Error generando embedding (Intento de fallback): {e}")
         # FALLBACK (Para raspberry pi 3): Una matriz estática o error para que el usuario sepa que tiene que configurar embeddings locales.
         # En un entorno real en Rpi3, podríamos cargar onnxruntime y un modelo de 20MB.
         raise HTTPException(status_code=500, detail="Fallo en la generación de embeddings")
