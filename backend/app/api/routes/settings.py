"""
MarcoAI – Settings API Router (Fase 11)
══════════════════════════════════════════════════════════════════════════════
Endpoints para leer y actualizar los ajustes de personalización e IA del usuario.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Any
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.db.base import get_db
from app.db.models import User, UserSettings

router = APIRouter(prefix="/settings", tags=["Ajustes"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class SettingsUpdate(BaseModel):
    # AI Personalization
    ai_tone: str | None = Field(None, pattern="^(friendly|professional|motivational)$")
    custom_instructions: str | None = None
    language: str | None = None

    # Notifications
    notifications_enabled: bool | None = None
    notification_hour: int | None = Field(None, ge=0, le=23)
    notify_calendar: bool | None = None
    notify_habits: bool | None = None
    notify_finance: bool | None = None


# ── Helper ────────────────────────────────────────────────────────────────────

async def _get_or_create_settings(user_id: str, db: AsyncSession) -> UserSettings:
    """Fetch existing settings or create defaults on first access (upsert)."""
    res = await db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
    settings = res.scalar_one_or_none()
    if settings is None:
        settings = UserSettings(user_id=user_id)
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    return settings


def _settings_to_dict(s: UserSettings) -> dict:
    return {
        "ai_tone": s.ai_tone,
        "custom_instructions": s.custom_instructions,
        "language": s.language,
        "notifications_enabled": s.notifications_enabled,
        "notification_hour": s.notification_hour,
        "notify_calendar": s.notify_calendar,
        "notify_habits": s.notify_habits,
        "notify_finance": s.notify_finance,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    }


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("", summary="Obtener los ajustes del usuario")
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    settings = await _get_or_create_settings(current_user.id, db)
    return _settings_to_dict(settings)


@router.put("", summary="Actualizar los ajustes del usuario")
async def update_settings(
    body: SettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    settings = await _get_or_create_settings(current_user.id, db)

    # Patch only the fields that were explicitly sent in the request body.
    # exclude_unset (not exclude_none) is correct here: it allows setting
    # notification_hour=0 (midnight) or notify_finance=False explicitly.
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(settings, field, value)

    await db.commit()
    await db.refresh(settings)
    return _settings_to_dict(settings)
