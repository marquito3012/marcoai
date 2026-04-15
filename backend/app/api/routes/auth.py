"""
MarcoAI – Google OAuth 2.0 Authentication Routes

Flow:
  1. GET /api/v1/auth/google         → redirect to Google consent screen
  2. GET /api/v1/auth/google/callback → exchange code, upsert user, set JWT cookie
  3. GET /api/v1/auth/me             → get current user (requires cookie)
  4. POST /api/v1/auth/logout        → clear cookie

Security:
  • `state` parameter prevents CSRF during the OAuth dance.
  • JWT is stored in an HttpOnly, SameSite=Lax cookie (not accessible by JS).
  • Row-Level Security: every subsequent request carries user_id via JWT.
"""
import secrets
from datetime import datetime, timezone
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.security import create_access_token
from app.db.base import get_db
from app.db.models import User

router = APIRouter(prefix="/auth", tags=["Autenticación"])

# ── Google OAuth endpoints ─────────────────────────────────────────────────────
_GOOGLE_AUTH_URL    = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_URL   = "https://oauth2.googleapis.com/token"
_GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

# In-memory CSRF state store.
# For a single-process deployment on RPi this is sufficient.
# Upgrade to Redis if you ever run multiple workers.
_pending_states: set[str] = set()


def _callback_uri(request: Request) -> str:
    """Build the OAuth redirect_uri from the current request's base URL."""
    base = str(request.base_url).rstrip("/")
    return f"{base}/api/v1/auth/google/callback"


# ── 1. Initiate Google login ──────────────────────────────────────────────────
@router.get("/google", summary="Iniciar sesión con Google (SSO)")
async def google_login(request: Request):
    """Redirect the user to Google's OAuth 2.0 consent page."""
    state = secrets.token_urlsafe(32)
    _pending_states.add(state)

    params = {
        "client_id":     settings.google_client_id,
        "redirect_uri":  _callback_uri(request),
        "response_type": "code",
        "scope":         "openid email profile https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/gmail.modify https://www.googleapis.com/auth/gmail.compose https://www.googleapis.com/auth/gmail.readonly",
        "state":         state,
        "access_type":   "offline",
        "prompt":        "consent",  # Force consent to get refresh token
    }
    return RedirectResponse(f"{_GOOGLE_AUTH_URL}?{urlencode(params)}")


# ── 2. OAuth callback ─────────────────────────────────────────────────────────
@router.get("/google/callback", summary="Callback de Google OAuth")
async def google_callback(
    request: Request,
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
):
    # ── CSRF validation ──────────────────────────────────────────────────────
    if state not in _pending_states:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Estado OAuth inválido o expirado.",
        )
    _pending_states.discard(state)

    redirect_uri = _callback_uri(request)

    async with httpx.AsyncClient(timeout=10) as client:
        # ── Exchange authorisation code for tokens ────────────────────────
        token_res = await client.post(
            _GOOGLE_TOKEN_URL,
            data={
                "code":          code,
                "client_id":     settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri":  redirect_uri,
                "grant_type":    "authorization_code",
            },
        )
        if token_res.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error al intercambiar el código OAuth: {token_res.text}",
            )
        tokens = token_res.json()

        # ── Fetch Google user profile ─────────────────────────────────────
        userinfo_res = await client.get(
            _GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        if userinfo_res.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Error al obtener el perfil de Google.",
            )
        info = userinfo_res.json()

    google_id: str = info["sub"]
    email: str     = info.get("email", "")
    name: str      = info.get("name", email)
    picture: str | None = info.get("picture")

    # ── Extract Calendar tokens ────────────────────────────────────────────
    calendar_access_token = tokens.get("access_token")
    calendar_refresh_token = tokens.get("refresh_token")
    expires_in = tokens.get("expires_in", 3600)
    from datetime import timedelta
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))

    # ── Upsert user record ────────────────────────────────────────────────────
    result = await db.execute(select(User).where(User.google_id == google_id))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            google_id=google_id, email=email, name=name, picture_url=picture,
            google_calendar_token=calendar_access_token,
            google_calendar_token_expires_at=expires_at,
            google_calendar_refresh_token=calendar_refresh_token,
        )
        db.add(user)
        await db.flush()          # get the generated UUID
    else:
        user.name        = name
        user.picture_url = picture
        # Update tokens on each login to keep them fresh
        user.google_calendar_token = calendar_access_token
        user.google_calendar_token_expires_at = expires_at
        if calendar_refresh_token:
            user.google_calendar_refresh_token = calendar_refresh_token

    await db.commit()
    await db.refresh(user)

    # ── Issue JWT in an HttpOnly cookie ───────────────────────────────────────
    access_token = create_access_token(subject=user.id)

    is_https = settings.frontend_url.startswith("https")
    response = RedirectResponse(
        url=f"{settings.frontend_url}/chat",
        status_code=status.HTTP_302_FOUND,
    )
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=is_https,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )
    return response


# ── 3. Get current user ───────────────────────────────────────────────────────
@router.get("/me", summary="Obtener usuario autenticado")
async def get_me(current_user: User = Depends(get_current_user)):
    """Returns the profile of the currently authenticated user."""
    return {
        "id":          current_user.id,
        "email":       current_user.email,
        "name":        current_user.name,
        "picture_url": current_user.picture_url,
        "created_at":  current_user.created_at.isoformat(),
    }


# ── 4. Logout ─────────────────────────────────────────────────────────────────
@router.post("/logout", summary="Cerrar sesión")
async def logout(response: Response):
    """Clears the JWT session cookie."""
    response.delete_cookie("access_token", path="/")
    return {"message": "Sesión cerrada correctamente."}
