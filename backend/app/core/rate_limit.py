"""
Simple in-memory per-user rate limiter using sliding window.

Usage as a FastAPI dependency:

    from app.core.rate_limit import rate_limit

    @router.post("/endpoint")
    async def endpoint(_rl: None = Depends(rate_limit)):
        ...
"""
import time
from collections import defaultdict

from fastapi import Depends, HTTPException, status

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.models import User

# {user_id: [timestamp, timestamp, ...]}
_buckets: dict[str, list[float]] = defaultdict(list)

WINDOW = 60.0  # 1 minute window


async def rate_limit(user: User = Depends(get_current_user)) -> None:
    """FastAPI dependency -- raises 429 if user exceeds RPM."""
    rpm: int = getattr(settings, "rate_limit_rpm", 30)
    user_id: str = str(user.id)
    now = time.monotonic()

    # Prune timestamps outside the window
    _buckets[user_id] = [t for t in _buckets[user_id] if now - t < WINDOW]

    if len(_buckets[user_id]) >= rpm:
        oldest = _buckets[user_id][0]
        retry_after = int(WINDOW - (now - oldest)) + 1
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Try again later.",
            headers={"Retry-After": str(retry_after)},
        )

    _buckets[user_id].append(now)
