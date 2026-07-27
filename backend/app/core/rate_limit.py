"""
Simple in-memory rate limiter using sliding window.

Provides two FastAPI dependencies:
  - ``rate_limit``       – per-user RPM (requires auth)
  - ``ip_rate_limit``    – per-IP RPM  (for unauthenticated endpoints)

Usage::

    from app.core.rate_limit import rate_limit, ip_rate_limit

    @router.post("/endpoint")
    async def endpoint(_rl: None = Depends(rate_limit)):
        ...

    @router.get("/public")
    async def public(_rl: None = Depends(ip_rate_limit)):
        ...
"""
import time
from collections import defaultdict

from fastapi import Depends, HTTPException, Request, status

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.models import User

# {key: [timestamp, ...]}
_buckets: dict[str, list[float]] = defaultdict(list)
_ip_buckets: dict[str, list[float]] = defaultdict(list)

WINDOW = 60.0  # 1 minute window
IP_RPM = 20  # 20 attempts per minute per IP


async def rate_limit(user: User = Depends(get_current_user)) -> None:
    """FastAPI dependency -- raises 429 if user exceeds RPM."""
    rpm: int = settings.rate_limit_rpm
    user_id: str = str(user.id)
    now = time.monotonic()

    # Prune timestamps outside the window
    _buckets[user_id] = [t for t in _buckets[user_id] if now - t < WINDOW]
    if not _buckets[user_id]:
        del _buckets[user_id]

    if len(_buckets[user_id]) >= rpm:
        oldest = _buckets[user_id][0]
        retry_after = int(WINDOW - (now - oldest)) + 1
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Try again later.",
            headers={"Retry-After": str(retry_after)},
        )

    _buckets[user_id].append(now)


async def ip_rate_limit(request: Request) -> None:
    """FastAPI dependency -- raises 429 if IP exceeds RPM. For unauthenticated endpoints."""
    ip = request.client.host if request.client else "unknown"
    now = time.monotonic()

    _ip_buckets[ip] = [t for t in _ip_buckets[ip] if now - t < WINDOW]
    if not _ip_buckets[ip]:
        del _ip_buckets[ip]

    if len(_ip_buckets[ip]) >= IP_RPM:
        oldest = _ip_buckets[ip][0]
        retry_after = int(WINDOW - (now - oldest)) + 1
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication attempts. Try again later.",
            headers={"Retry-After": str(retry_after)},
        )

    _ip_buckets[ip].append(now)
