"""
MarcoAI – Notification Service (Fase 11)
══════════════════════════════════════════════════════════════════════════════
Genera y envía el resumen diario al usuario vía Gmail.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import User, UserSettings

logger = logging.getLogger(__name__)


async def send_daily_digest(user: User, settings: UserSettings, db: AsyncSession) -> bool:
    """
    Compila y envía el resumen diario al usuario.
    Returns True si el envío fue exitoso.
    """
    if not user.google_calendar_token:
        logger.warning("User %s has no Gmail token, skipping digest.", user.id)
        return False

    try:
        sections = []
        now = datetime.now(timezone.utc)
        today = now.date()

        # ── 1. Calendario ──────────────────────────────────────────────────────
        if settings.notify_calendar:
            try:
                from app.services.calendar_service import CalendarService
                cal_service = CalendarService(db, user)
                start = datetime(today.year, today.month, today.day, 0, 0, 0, tzinfo=timezone.utc)
                end = datetime(today.year, today.month, today.day, 23, 59, 59, tzinfo=timezone.utc)
                events = await cal_service.list_events(start_date=start, end_date=end, max_results=10)
                if events:
                    lines = ["<h3 style='color:#D4AF37'>📅 Eventos de hoy</h3><ul>"]
                    for e in events:
                        s = e.get("start", {})
                        dt_str = s.get("dateTime", s.get("date", ""))
                        time_label = ""
                        if "T" in dt_str:
                            try:
                                dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                                time_label = f" ({dt.strftime('%H:%M')})"
                            except: pass
                        lines.append(f"<li><b>{e.get('summary','Sin título')}</b>{time_label}</li>")
                    lines.append("</ul>")
                    sections.append("\n".join(lines))
                else:
                    sections.append("<h3 style='color:#D4AF37'>📅 Eventos de hoy</h3><p>No tienes eventos hoy. ¡Día libre!</p>")
            except Exception as e:
                logger.warning("Could not fetch calendar for digest: %s", e)

        # ── 2. Hábitos ─────────────────────────────────────────────────────────
        if settings.notify_habits:
            try:
                from app.services.habits_service import HabitsService
                from app.db.models import HabitLog, Habit
                habits_service = HabitsService(db, user.id)
                habits = await habits_service.get_habits()
                today_iso = today.isoformat()
                weekday = today.weekday()

                pending = []
                done = []
                for h in habits:
                    target_days = [int(d) for d in h.target_days.split(",")] if h.target_days else [0,1,2,3,4,5,6]
                    if weekday not in target_days:
                        continue
                    log_res = await db.execute(
                        select(HabitLog).where(HabitLog.habit_id == h.id, HabitLog.completed_date == today_iso)
                    )
                    if log_res.scalar_one_or_none():
                        done.append(h.name)
                    else:
                        pending.append(h.name)

                habit_html = ["<h3 style='color:#B5838D'>🔥 Hábitos de hoy</h3>"]
                if done:
                    habit_html.append(f"<p>✅ Completados: {', '.join(done)}</p>")
                if pending:
                    habit_html.append(f"<p>⏳ Pendientes: {', '.join(pending)}</p>")
                if not done and not pending:
                    habit_html.append("<p>No tienes hábitos programados para hoy.</p>")
                sections.append("\n".join(habit_html))
            except Exception as e:
                logger.warning("Could not fetch habits for digest: %s", e)

        # ── 3. Finanzas ────────────────────────────────────────────────────────
        if settings.notify_finance:
            try:
                from app.services.finance_service import FinanceService
                fin_service = FinanceService(db, user.id)
                balance = await fin_service.get_monthly_balance()
                emoji = "🟢" if balance["balance"] >= 0 else "🔴"
                sections.append(
                    f"<h3 style='color:#D4AF37'>💰 Balance del mes</h3>"
                    f"<p>{emoji} <b>Balance:</b> {balance['balance']:,.2f}€ "
                    f"(Ingresos: {balance['income']:,.2f}€ / Gastos: {balance['expenses']:,.2f}€)</p>"
                )
            except Exception as e:
                logger.warning("Could not fetch finance for digest: %s", e)

        if not sections:
            logger.info("No sections to send for user %s digest.", user.id)
            return False

        # ── Build HTML email ───────────────────────────────────────────────────
        first_name = user.name.split()[0] if user.name else "Marco"
        html_body = f"""
        <div style="font-family: 'Outfit', Arial, sans-serif; max-width: 600px; margin: 0 auto;
                    background: #0D0D0D; color: #E2E2E2; border-radius: 12px; overflow: hidden;
                    border: 1px solid rgba(212,175,55,0.2);">
            <div style="background: linear-gradient(135deg, #141414, #1C1C1C); padding: 24px 32px;
                        border-bottom: 1px solid rgba(212,175,55,0.15);">
                <h1 style="margin: 0; font-size: 20px; color: #D4AF37;">
                    Buenos días, {first_name} ✨
                </h1>
                <p style="margin: 6px 0 0; color: #888; font-size: 14px;">
                    Tu resumen de Marco para hoy, {today.strftime('%A %d de %B').capitalize()}
                </p>
            </div>
            <div style="padding: 24px 32px; display: flex; flex-direction: column; gap: 16px;">
                {"".join(f'<div style="margin-bottom: 20px;">{s}</div>' for s in sections)}
            </div>
            <div style="padding: 16px 32px; background: #141414; text-align: center;
                        border-top: 1px solid rgba(255,255,255,0.04);">
                <p style="margin: 0; font-size: 12px; color: #333;">
                    MarcoAI · Tu asistente personal · Ajusta tus notificaciones en Ajustes
                </p>
            </div>
        </div>
        """

        # ── Send via Gmail ─────────────────────────────────────────────────────
        from app.services.gmail_service import GmailService
        gmail = GmailService(db, user)
        subject = f"☀️ Tu resumen diario — {today.strftime('%d/%m/%Y')}"
        await gmail.send_email(to=user.email, subject=subject, html_body=html_body)
        logger.info("Daily digest sent to %s (%s).", user.email, user.id)
        return True

    except Exception as exc:
        logger.error("Failed to send daily digest for user %s: %s", user.id, exc, exc_info=True)
        return False
