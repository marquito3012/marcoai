"""
MarcoAI – APScheduler Background Jobs (Fase 11)
══════════════════════════════════════════════════════════════════════════════
Scheduler que se ejecuta dentro del proceso de FastAPI.
Comprueba cada hora qué usuarios tienen notificaciones activas y cuya hora
configurada coincide con la hora local de Madrid, y les envía el resumen diario.
"""
from __future__ import annotations

import logging
import zoneinfo
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None
_TZ_MADRID = zoneinfo.ZoneInfo("Europe/Madrid")


async def _run_digest_job() -> None:
    """
    Checks every hour which users should receive their digest right now.
    Uses Europe/Madrid time so notification_hour=6 means 06:00 Madrid, not UTC.
    """
    # Bug 2 fix: always compare against Madrid local time, not server UTC
    current_hour = datetime.now(_TZ_MADRID).hour
    logger.info("Digest job running — Madrid hour: %d", current_hour)

    try:
        from sqlalchemy import select
        from app.db.base import AsyncSessionLocal
        from app.db.models import User, UserSettings
        from app.services.notification_service import send_daily_digest

        # Bug 3 fix: extract all needed primitive values inside the session,
        # before it closes, so there is no DetachedInstanceError risk later.
        pending: list[dict] = []

        async with AsyncSessionLocal() as db:
            stmt = (
                select(UserSettings, User)
                .join(User, User.id == UserSettings.user_id)
                .where(
                    UserSettings.notifications_enabled == True,  # noqa: E712
                    UserSettings.notification_hour == current_hour,
                    User.is_active == True,  # noqa: E712
                )
            )
            res = await db.execute(stmt)
            rows = res.all()

            for settings_row, user_row in rows:
                # Eagerly read every primitive we need while the session is open
                pending.append({
                    # User primitives
                    "user_id": user_row.id,
                    "user_email": user_row.email,
                    "user_name": user_row.name,
                    "google_calendar_token": user_row.google_calendar_token,
                    "google_calendar_refresh_token": user_row.google_calendar_refresh_token,
                    "google_calendar_token_expires_at": user_row.google_calendar_token_expires_at,
                    "is_active": user_row.is_active,
                    # Settings primitives
                    "notifications_enabled": settings_row.notifications_enabled,
                    "notification_hour": settings_row.notification_hour,
                    "notify_calendar": settings_row.notify_calendar,
                    "notify_habits": settings_row.notify_habits,
                    "notify_finance": settings_row.notify_finance,
                })

        if not pending:
            logger.debug("No users to notify at Madrid hour %d.", current_hour)
            return

        logger.info("Sending digest to %d user(s) at hour %d.", len(pending), current_hour)

        for data in pending:
            try:
                # Open a fresh, independent session for each user's digest
                async with AsyncSessionLocal() as db:
                    # Reload user and settings from the DB with this fresh session
                    user_obj = await db.get(User, data["user_id"])
                    if not user_obj:
                        logger.warning("User %s not found, skipping digest.", data["user_id"])
                        continue

                    settings_stmt = select(UserSettings).where(UserSettings.user_id == data["user_id"])
                    settings_res = await db.execute(settings_stmt)
                    settings_obj = settings_res.scalar_one_or_none()
                    if not settings_obj:
                        logger.warning("Settings not found for user %s.", data["user_id"])
                        continue

                    await send_daily_digest(user=user_obj, settings=settings_obj, db=db)
            except Exception as exc:
                logger.error("Failed digest for user %s: %s", data["user_id"], exc, exc_info=True)

    except Exception as exc:
        logger.error("Digest job failed: %s", exc, exc_info=True)


def start_scheduler() -> AsyncIOScheduler:
    """Create and start the APScheduler instance. Call from FastAPI lifespan."""
    global _scheduler
    _scheduler = AsyncIOScheduler(timezone="Europe/Madrid")
    _scheduler.add_job(
        _run_digest_job,
        trigger=CronTrigger(minute=0),   # fires at :00 of every hour
        id="daily_digest",
        replace_existing=True,
        misfire_grace_time=300,
    )
    _scheduler.start()
    logger.info("APScheduler started — daily digest job registered (Europe/Madrid).")
    return _scheduler


def stop_scheduler() -> None:
    """Gracefully shut down the scheduler. Call from FastAPI lifespan shutdown."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("APScheduler shut down.")
