"""
Google OAuth 2.0 Authentication Router.
Flow:
  1. GET /auth/login  → redirect to Google consent screen
  2. GET /auth/callback → exchange code, set signed cookie, redirect to /
  3. GET /auth/me     → return current user from cookie
  4. GET /auth/logout → clear cookie, redirect to /
"""
import json
import logging
from typing import Optional
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Request, Response
from fastapi.responses import RedirectResponse, JSONResponse
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from ..config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

# ---------------------------------------------------------------------
# Session helpers (signed cookie, no DB needed)
# ---------------------------------------------------------------------
COOKIE_NAME = "marco_session"
COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # 30 days


def _signer() -> URLSafeTimedSerializer:
    settings = get_settings()
    return URLSafeTimedSerializer(settings.secret_key, salt="marco-auth")


def set_session(response: Response, user: dict) -> None:
    """Store user dict in a signed, httponly cookie."""
    token = _signer().dumps(user)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=False,  # set True in production behind HTTPS
    )


def get_session(request: Request) -> Optional[dict]:
    """Read and verify signed cookie. Returns user dict or None."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    try:
        return _signer().loads(token, max_age=COOKIE_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None


# ---------------------------------------------------------------------
# Google OAuth helpers
# ---------------------------------------------------------------------
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

SCOPES = [
    "openid",
    "email",
    "profile",
]


def _redirect_uri() -> str:
    settings = get_settings()
    return f"{settings.app_url}/auth/callback"


# ---------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------

@router.get("/login")
async def login(request: Request):
    """Redirect user to Google OAuth consent screen."""
    settings = get_settings()

    if not settings.google_client_id:
        return JSONResponse(
            status_code=503,
            content={"error": "Google OAuth not configured. Set GOOGLE_CLIENT_ID in .env"}
        )

    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": _redirect_uri(),
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "select_account",
    }
    url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    return RedirectResponse(url=url)


@router.get("/callback")
async def callback(request: Request, code: str = "", error: str = ""):
    """Handle Google OAuth callback, set session cookie, redirect to /."""
    if error:
        logger.warning(f"OAuth error: {error}")
        return RedirectResponse(url="/?auth_error=1")

    if not code:
        return RedirectResponse(url="/?auth_error=1")

    settings = get_settings()

    # Exchange authorization code for tokens
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": _redirect_uri(),
                "grant_type": "authorization_code",
            },
        )

    if token_resp.status_code != 200:
        logger.error(f"Token exchange failed: {token_resp.text}")
        return RedirectResponse(url="/?auth_error=1")

    tokens = token_resp.json()
    access_token = tokens.get("access_token")

    # Fetch user profile from Google
    async with httpx.AsyncClient() as client:
        userinfo_resp = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )

    if userinfo_resp.status_code != 200:
        logger.error(f"Userinfo fetch failed: {userinfo_resp.text}")
        return RedirectResponse(url="/?auth_error=1")

    userinfo = userinfo_resp.json()

    # Build minimal user object (don't store raw tokens in cookie)
    user = {
        "id": userinfo.get("id"),
        "email": userinfo.get("email"),
        "name": userinfo.get("name"),
        "picture": userinfo.get("picture"),
    }

    response = RedirectResponse(url="/", status_code=303)
    set_session(response, user)
    return response


@router.get("/me")
async def me(request: Request):
    """Return current authenticated user, or 401 if not logged in."""
    user = get_session(request)
    if not user:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})
    return JSONResponse(content=user)


@router.get("/logout")
async def logout():
    """Clear session cookie and redirect to /."""
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie(COOKIE_NAME)
    return response
