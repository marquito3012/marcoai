"""
OAuth CSRF state storage — persistent replacement for in-memory set.

Each state is a random token stored with a timestamp. Validated and deleted
on callback. Expired states are cleaned up periodically.
"""
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import Column, DateTime, String, delete, select
from app.db.base import Base


class OAuthState(Base):
    __tablename__ = "oauth_states"

    state = Column(String(64), primary_key=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


STATE_TTL_MINUTES = 10


async def create_state(db) -> str:
    """Generate a random state token, store it, and return it."""
    # Cleanup expired states (lazy, runs on each login)
    await cleanup_expired_states(db)

    state = secrets.token_urlsafe(32)
    db.add(OAuthState(state=state))
    await db.commit()
    return state


async def validate_and_delete_state(db, state: str) -> bool:
    """Check if state exists and is not expired. Delete it regardless (single use)."""
    result = await db.execute(
        select(OAuthState).where(OAuthState.state == state)
    )
    record = result.scalar_one_or_none()

    if record is None:
        return False

    # Delete the state (single use)
    await db.execute(delete(OAuthState).where(OAuthState.state == state))
    await db.commit()

    # Check TTL
    age = datetime.now(timezone.utc) - record.created_at
    if age > timedelta(minutes=STATE_TTL_MINUTES):
        return False

    return True


async def cleanup_expired_states(db) -> int:
    """Delete states older than STATE_TTL_MINUTES. Returns count deleted."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=STATE_TTL_MINUTES)
    result = await db.execute(
        delete(OAuthState).where(OAuthState.created_at < cutoff)
    )
    await db.commit()
    return result.rowcount
