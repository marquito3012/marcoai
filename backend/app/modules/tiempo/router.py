from fastapi import APIRouter, Depends
from typing import List
from app.database import User
from app.auth.dependencies import get_current_user
from app.services.google_calendar import list_upcoming_events
from app.services.google_gmail import list_unread_messages

router = APIRouter(prefix="/tiempo", tags=["tiempo"])

@router.get("/agenda")
def get_agenda(current_user: User = Depends(get_current_user)):
    """Devuelve los próximos eventos del usuario"""
    return list_upcoming_events(current_user, max_results=10)

@router.get("/correos")
def get_correos(current_user: User = Depends(get_current_user)):
    """Devuelve los últimos correos no leídos"""
    return list_unread_messages(current_user, max_results=10)
