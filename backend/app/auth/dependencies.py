"""
Authentication dependencies for FastAPI.
Memory-efficient OAuth token validation.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[str]:
    """
    Extract and validate user ID from JWT token.
    Returns user_id if valid, None if no credentials.
    """
    if not credentials:
        return None

    # TODO: Implement proper JWT validation
    # For now, return a placeholder user ID
    # In production, validate against Google OAuth tokens
    return "user-123"


async def require_auth(
    user_id: Optional[str] = Depends(get_current_user),
) -> str:
    """Require authentication - raise 401 if not authenticated."""
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return user_id
