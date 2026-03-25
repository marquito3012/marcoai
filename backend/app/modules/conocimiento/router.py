from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.database import User
from app.auth.dependencies import get_current_user
from app.rag.engine import add_document, search

router = APIRouter(prefix="/conocimiento", tags=["conocimiento"])

class Nota(BaseModel):
    texto: str
    metadata: dict = {}

@router.post("/notas")
async def crear_nota(nota: Nota, current_user: User = Depends(get_current_user)):
    """Guarda una nota y la indexa en el cerebro (RAG)"""
    doc_id = await add_document(current_user.id, nota.texto, nota.metadata)
    return {"status": "ok", "doc_id": doc_id}

@router.get("/buscar")
async def buscar_conocimiento(q: str, current_user: User = Depends(get_current_user)):
    """Busca en el cerebro digital del usuario (Solo notas generales)"""
    resultados = await search(current_user.id, q)
    # Filtrar: solo lo que NO tiene tipo (es nota general) o es explícitamente tipo "nota"
    filtrados = [
        r for r in resultados 
        if not r.get("metadata") or not r["metadata"].get("tipo") or r["metadata"].get("tipo") == "nota"
    ]
    return {"results": filtrados}
