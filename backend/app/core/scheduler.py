"""
MarcoAI – APScheduler Background Jobs (Fase 11)
══════════════════════════════════════════════════════════════════════════════
Scheduler que se ejecuta dentro del proceso de FastAPI.
Comprueba cada hora qué usuarios tienen notificaciones activas y cuya hora
configurada coincide con la hora local actual, y les envía el resumen diario.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


async def _run_digest_job() -> None:
    """Checks every hour which users should receive their digest right now."""
    current_hour = datetime.now().hour  # local server hour
    logger.info("Digest job running at hour %d", current_hour)

    try:
        from sqlalchemy import select
        from app.db.base import AsyncSessionLocal
        from app.db.models import User, UserSettings
        from app.services.notification_service import send_daily_digest

        async with AsyncSessionLocal() as db:
            stmt = (
                select(UserSettings, User)
                .join(User, User.id == UserSettings.user_id)
                .where(
                    UserSettings.notifications_enabled == True,
                    UserSettings.notification_hour == current_hour,
                    User.is_active == True,
                )
            )
            res = await db.execute(stmt)
            rows = res.all()

        if not rows:
            logger.debug("No users to notify at hour %d.", current_hour)
            return

        logger.info("Sending digest to %d user(s) at hour %d.", len(rows), current_hour)
        for settings, user in rows:
            # Open a fresh session per send to avoid long-lived transactions
            async with AsyncSessionLocal() as db:
                await send_daily_digest(user=user, settings=settings, db=db)

    except Exception as exc:
        logger.error("Digest job failed: %s", exc, exc_info=True)


def start_scheduler() -> AsyncIOScheduler:
    """Create and start the APScheduler instance. Call from FastAPI lifespan."""
    global _scheduler
    _scheduler = AsyncIOScheduler(timezone="Europe/Madrid")
    _scheduler.add_job(
        _run_digest_job,
        trigger=CronTrigger(minute=0),  # fires at :00 of every hour
        id="daily_digest",
        replace_existing=True,
        misfire_grace_time=300,
    )
    _scheduler.start()
    logger.info("APScheduler started — daily digest job registered.")
    return _scheduler


def stop_scheduler() -> None:
    """Gracefully shut down the scheduler. Call from FastAPI lifespan shutdown."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("APScheduler shut down.")
