from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session
from app.database import get_db, User
from app.auth.dependencies import get_current_user
from pydantic import BaseModel
from typing import List, Dict, Optional
from app.agents.orchestrator import process_message
from app.agents.groq_client import speech_to_text

router = APIRouter(prefix="/agente", tags=["agente"])

class ChatMessage(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = []

@router.post("/chat")
async def chat_with_agent(req: ChatMessage, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Endpoint principal para hablar con el agente"""
    respuesta = await process_message(current_user, req.message, req.history)
    return {"reply": respuesta}

@router.post("/stt")
async def transcribe_audio(audio: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    """Endpoint para transcribir audio del chat"""
    try:
        audio_content = await audio.read()
        text = await speech_to_text(audio_content, audio.filename)
        return {"transcript": text or ""}
    except Exception as e:
        return {"error": str(e), "transcript": ""}
