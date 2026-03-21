import json
import urllib.request
import urllib.error
import asyncio
import time
from fastapi import HTTPException

def fetch_hf_embedding(text: str) -> list[float]:
    # Usamos un modelo multilingüe de 768 dimensiones (compatible con la DB VSS actual)
    url = "https://api-inference.huggingface.co/pipeline/feature-extraction/sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
    headers = {"Content-Type": "application/json"}
    data = json.dumps({"inputs": text}).encode("utf-8")
    
    for attempt in range(3):
        req = urllib.request.Request(url, data=data, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode())
                if isinstance(result, list) and len(result) > 0:
                    if isinstance(result[0], float): return result
                    if isinstance(result[0], list): return result[0]
                raise Exception("Formato inesperado del API")
        except urllib.error.HTTPError as e:
            if e.code == 503:
                # El modelo gratuito está "despertando". Esperamos y reintentamos.
                time.sleep(5)
                continue
            raise e
        except Exception as e:
            raise e
    raise Exception("Timeout esperando inicialización del modelo remoto")

async def generate_embedding(text: str) -> list[float]:
    """Genera el embedding usando la API gratuita de HuggingFace como alternativa a Groq/Local."""
    try:
         # Ejecutamos la petición síncrona en un hilo separado para no bloquear FastAPI
         return await asyncio.to_thread(fetch_hf_embedding, text)
    except Exception as e:
         print(f"Error generando embedding con HuggingFace API: {e}")
         raise HTTPException(status_code=500, detail="Fallo en la generación de embeddings. Intenta de nuevo.")
