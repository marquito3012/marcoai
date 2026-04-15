"""
MarcoAI – FastAPI Dependencies

`get_current_user` is the core security dependency.  Import and use it in any
route that requires an authenticated user:

    @router.get("/protected")
    async def protected(user: User = Depends(get_current_user)):
        ...

The function:
  1. Reads the JWT from the HttpOnly "access_token" cookie.
  2. Decodes & validates the signature / expiry.
  3. Loads the User row from the DB and returns it.

If any step fails → HTTP 401 Unauthorized.
"""
from fastapi import Cookie, Depends, HTTPException, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.base import get_db
from app.db.models import User


async def get_current_user(
    access_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Resolve the authenticated user from the session cookie.
    Raises HTTP 401 if the cookie is missing, expired, or tampered.
    """
    _401 = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No autenticado o sesión expirada.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not access_token:
        raise _401

    try:
        payload = decode_access_token(access_token)
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise _401
    except JWTError:
        raise _401

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise _401

    return user
