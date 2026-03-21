from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db, User
from app.auth.dependencies import get_current_user
from pydantic import BaseModel
from app.agents.orchestrator import process_message

router = APIRouter(prefix="/agente", tags=["agente"])

class ChatMessage(BaseModel):
    message: str

@router.post("/chat")
async def chat_with_agent(req: ChatMessage, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Endpoint principal para hablar con el agente"""
    respuesta = await process_message(current_user, req.message)
    return {"reply": respuesta}
