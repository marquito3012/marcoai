import string
import math
import hashlib

async def generate_embedding(text: str) -> list[float]:
    """
    Fallback RAG ultraligero para Raspberry Pi: Count Vectorizer con Hashing Trick.
    No requiere APIs externas y convierte el RAG en un sistema de Búsqueda Léxica pura.
    Mapea las palabras a un vector de 768 dimensiones.
    """
    vec = [0.0] * 768
    
    # Normalizar texto
    text = text.lower()
    for p in string.punctuation.replace('á','').replace('é','').replace('í','').replace('ó','').replace('ú','').replace('ñ',''):
        text = text.replace(p, ' ')
        
    words = text.split()
    stop_words = {"el", "la", "los", "las", "un", "una", "y", "o", "pero", "si", "de", "en", "a", "por", "para", "con", "sin", "es", "son", "del", "al", "q", "que"}
    
    for word in words:
        if len(word) > 2 and word not in stop_words:
            # Deterministic hash compatible cruzado
            h = int(hashlib.md5(word.encode('utf-8')).hexdigest(), 16)
            idx = h % 768
            vec[idx] += 1.0
            
    # L2 Normalization para que la similitud de coseno funcione igual que texto
    norm = math.sqrt(sum(x*x for x in vec))
    if norm > 0:
         vec = [x / norm for x in vec]
    else:
         # Si no hay palabras útiles, ponemos el primer índice a 1 para no romper la BD
         vec[0] = 1.0
         
    return vec
