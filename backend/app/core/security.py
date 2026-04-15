"""
MarcoAI – JWT Security Utilities

All token operations (create / decode) go through here so the algorithm
and secret key stay centralised in one file.
"""
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from app.core.config import settings


def create_access_token(
    subject: str | Any,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Issue a signed JWT embedding `subject` (typically user_id) as the `sub` claim.
    """
    expire = datetime.now(timezone.utc) + (
        expires_delta
        or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload = {"sub": str(subject), "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict:
    """
    Decode and validate a JWT.  Raises ``jose.JWTError`` on any failure
    (tampered signature, expired token, …).
    """
    return jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.algorithm],
    )
