from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from urllib.parse import urlencode
from datetime import timedelta
from typing import Any

from app.config import settings
from app.database import get_db, User
from app.auth.google_client import exchange_code_for_tokens, get_user_info
from app.auth.dependencies import create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])

# Alcance necesario para Google Calendar y Gmail
SCOPES = [
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.modify"
]

@router.get("/login")
def login_google():
    """Redirige al usuario a la página de login de Google"""
    base_url = "https://accounts.google.com/o/oauth2/v2/auth"
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": f"{settings.FRONTEND_URL}/api/auth/callback",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent", # Forzar refresh token en cada login para asegurar que lo tenemos
    }
    url = f"{base_url}?{urlencode(params)}"
    return RedirectResponse(url)

@router.get("/callback")
async def google_callback(code: str, response: Response, db: Session = Depends(get_db)):
    """Procesa el código de Google y crea la sesión del usuario"""
    try:
        redirect_uri = f"{settings.FRONTEND_URL}/api/auth/callback"
        token_data = await exchange_code_for_tokens(code, redirect_uri)
    except Exception as e:
        raise HTTPException(status_code=400, detail="Error en OAuth code exchange")
        
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    
    if not access_token:
        raise HTTPException(status_code=400, detail="Token de acceso no recibido de Google")
        
    try:
        user_info = await get_user_info(access_token)
    except Exception as e:
        raise HTTPException(status_code=400, detail="Error obteniendo perfil de Google")
        
    email = user_info.get("email")
    google_id = user_info.get("id")
    name = user_info.get("name")
    picture = user_info.get("picture")
    
    # 20 Usuarios MAX (Para control de acceso)
    total_users = db.query(User).count()
    
    # Buscar si el usuario ya existe
    user = db.query(User).filter(User.google_id == google_id).first()
    
    if not user:
        if total_users >= 20:
             # Redirigir al frontend con error
             return RedirectResponse(url=f"{settings.FRONTEND_URL}/#login?error=max_users_reached")
        # Crear usuario
        user = User(
            google_id=google_id,
            email=email,
            name=name,
            picture=picture,
            google_access_token=access_token,
            google_refresh_token=refresh_token # Puede ser None si no es la primera vez
        )
        db.add(user)
        db.commit()
    else:
        # Actualizar tokens
        user.google_access_token = access_token
        if refresh_token:
             user.google_refresh_token = refresh_token
        
        # Opcional: actualizar nombre/foto en caso cambien
        user.name = name
        user.picture = picture
        db.commit()
        
    db.refresh(user)
    
    # Crear JWT de sesión propia
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    session_jwt = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    
    # Redirigir al frontend al Dashboard
    redirect_dash = RedirectResponse(url=f"{settings.FRONTEND_URL}/#dashboard")
    
    # Seteamos la cookie HttpOnly
    redirect_dash.set_cookie(
        key="session_token",
        value=session_jwt,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        expires=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=False  # True en prod con HTTPS
    )
    
    return redirect_dash

@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    """Retorna información del usuario actual"""
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "picture": current_user.picture
    }

@router.post("/logout")
def logout(response: Response):
    """Cierra la sesión borrando la cookie"""
    redirect_url = f"{settings.FRONTEND_URL}/#login"
    resp = RedirectResponse(url=redirect_url)
    resp.delete_cookie(key="session_token")
    return resp
