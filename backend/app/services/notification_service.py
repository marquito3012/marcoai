"""
MarcoAI – Notification Service (Fase 11)
══════════════════════════════════════════════════════════════════════════════
Genera y envía el resumen diario al usuario vía Gmail.

Secciones del digest (controladas por UserSettings):
  - 📅 Eventos del día      (notify_calendar)
  - 🔥 Hábitos pendientes   (notify_habits)
  - 💰 Balance del mes      (notify_finance)
  - 📬 Correos recibidos    (notify_mail — sección nueva)
"""
from __future__ import annotations

import logging
import zoneinfo
from datetime import datetime, timezone, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import User, UserSettings

logger = logging.getLogger(__name__)

_TZ_MADRID = zoneinfo.ZoneInfo("Europe/Madrid")


async def send_daily_digest(user: User, settings: UserSettings, db: AsyncSession) -> bool:
    """
    Compila y envía el resumen diario al usuario.
    Returns True si el envío fue exitoso.
    """
    if not user.google_calendar_token:
        logger.warning("User %s has no Google token, skipping digest.", user.id)
        return False

    if not user.email:
        logger.warning("User %s has no email address, skipping digest.", user.id)
        return False

    try:
        sections: list[str] = []
        # Use Madrid local time for "today" so the digest is relevant for the user
        now_local = datetime.now(_TZ_MADRID)
        today = now_local.date()
        # Calendar queries in UTC-aware boundaries
        day_start_utc = datetime(today.year, today.month, today.day, 0, 0, 0, tzinfo=timezone.utc)
        day_end_utc   = datetime(today.year, today.month, today.day, 23, 59, 59, tzinfo=timezone.utc)

        # ── 1. Eventos del día ─────────────────────────────────────────────────
        if settings.notify_calendar:
            try:
                from app.services.calendar_service import CalendarService
                cal_service = CalendarService(db, user)
                events = await cal_service.list_events(
                    start_date=day_start_utc, end_date=day_end_utc, max_results=10
                )
                if events:
                    lines = ["<h3 style='color:#D4AF37;margin:0 0 8px'>📅 Eventos de hoy</h3><ul style='margin:0;padding-left:20px'>"]
                    for e in events:
                        s = e.get("start", {})
                        dt_str = s.get("dateTime", s.get("date", ""))
                        time_label = ""
                        if "T" in dt_str:
                            try:
                                dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                                # Convert to Madrid time for display
                                dt_local = dt.astimezone(_TZ_MADRID)
                                time_label = f" <span style='color:#888'>({dt_local.strftime('%H:%M')})</span>"
                            except Exception:
                                pass
                        lines.append(f"<li><b>{e.get('summary', 'Sin título')}</b>{time_label}</li>")
                    lines.append("</ul>")
                    sections.append("\n".join(lines))
                else:
                    sections.append(
                        "<h3 style='color:#D4AF37;margin:0 0 8px'>📅 Eventos de hoy</h3>"
                        "<p style='color:#888'>No tienes eventos hoy. ¡Día libre! 🎉</p>"
                    )
            except Exception as exc:
                logger.warning("Could not fetch calendar for digest: %s", exc)

        # ── 2. Hábitos pendientes ──────────────────────────────────────────────
        if settings.notify_habits:
            try:
                from app.services.habits_service import HabitsService
                from app.db.models import HabitLog
                habits_service = HabitsService(db, user.id)
                habits = await habits_service.get_habits()
                today_iso = today.isoformat()
                weekday = today.weekday()  # 0=Mon … 6=Sun

                pending_habits: list[str] = []
                done_habits: list[str] = []

                for h in habits:
                    target_days = (
                        [int(d) for d in h.target_days.split(",")]
                        if h.target_days
                        else list(range(7))
                    )
                    if weekday not in target_days:
                        continue
                    log_res = await db.execute(
                        select(HabitLog).where(
                            HabitLog.habit_id == h.id,
                            HabitLog.completed_date == today_iso,
                        )
                    )
                    if log_res.scalar_one_or_none():
                        done_habits.append(h.name)
                    else:
                        pending_habits.append(h.name)

                habit_html = ["<h3 style='color:#B5838D;margin:0 0 8px'>🔥 Hábitos de hoy</h3>"]
                if done_habits:
                    habit_html.append(
                        f"<p style='color:#4CAF50'>✅ <b>Completados:</b> {', '.join(done_habits)}</p>"
                    )
                if pending_habits:
                    habit_html.append(
                        f"<p style='color:#FFB347'>⏳ <b>Pendientes:</b> {', '.join(pending_habits)}</p>"
                    )
                if not done_habits and not pending_habits:
                    habit_html.append("<p style='color:#888'>No tienes hábitos programados para hoy.</p>")
                sections.append("\n".join(habit_html))
            except Exception as exc:
                logger.warning("Could not fetch habits for digest: %s", exc)

        # ── 3. Balance del mes ─────────────────────────────────────────────────
        if settings.notify_finance:
            try:
                from app.services.finance_service import FinanceService
                fin_service = FinanceService(db, user.id)
                balance = await fin_service.get_monthly_balance()
                emoji = "🟢" if balance["balance"] >= 0 else "🔴"
                sections.append(
                    f"<h3 style='color:#D4AF37;margin:0 0 8px'>💰 Balance del mes</h3>"
                    f"<p>{emoji} <b>Balance:</b> {balance['balance']:,.2f}€ "
                    f"<span style='color:#888'>(Ingresos: {balance['income']:,.2f}€ "
                    f"/ Gastos: {balance['expenses']:,.2f}€)</span></p>"
                )
            except Exception as exc:
                logger.warning("Could not fetch finance for digest: %s", exc)

        # ── 4. Correos recientes ───────────────────────────────────────────────
        # Included if the user has Gmail connected (same token used for Calendar)
        if user.google_calendar_token:
            try:
                from app.services.gmail_service import GmailService
                gmail_service = GmailService(db, user)
                # Fetch unread emails from the last 24 h
                recent_mails = await gmail_service.list_messages(
                    query="is:unread newer_than:1d", max_results=5
                )
                if recent_mails:
                    mail_lines = [
                        "<h3 style='color:#64B5F6;margin:0 0 8px'>📬 Correos sin leer (últimas 24h)</h3>"
                        "<ul style='margin:0;padding-left:20px'>"
                    ]
                    for m in recent_mails:
                        sender = m.get("from", "")
                        # Extract just the name from "Name <email@example.com>"
                        if "<" in sender:
                            sender = sender.split("<")[0].strip().strip('"')
                        subject = m.get("subject", "(Sin asunto)")
                        mail_lines.append(
                            f"<li><b>{subject}</b> "
                            f"<span style='color:#888'>de {sender}</span></li>"
                        )
                    mail_lines.append("</ul>")
                    sections.append("\n".join(mail_lines))
                else:
                    sections.append(
                        "<h3 style='color:#64B5F6;margin:0 0 8px'>📬 Correos sin leer</h3>"
                        "<p style='color:#888'>No tienes correos sin leer de las últimas 24h. ¡Bandeja despejada! ✉️</p>"
                    )
            except Exception as exc:
                logger.warning("Could not fetch mail for digest: %s", exc)

        if not sections:
            logger.info("No sections generated for user %s digest.", user.id)
            return False

        # ── Build HTML email ───────────────────────────────────────────────────
        first_name = user.name.split()[0] if user.name else "Marco"
        day_names_es = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
        month_names_es = [
            "enero", "febrero", "marzo", "abril", "mayo", "junio",
            "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
        ]
        day_label = (
            f"{day_names_es[today.weekday()].capitalize()} "
            f"{today.day} de {month_names_es[today.month - 1]}"
        )

        sections_html = "".join(
            f'<div style="margin-bottom:24px;padding-bottom:24px;'
            f'border-bottom:1px solid rgba(255,255,255,0.06)">{s}</div>'
            for s in sections
        )

        html_body = f"""
<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:16px;background:#0A0A0A;font-family:Arial,Helvetica,sans-serif">
  <div style="max-width:600px;margin:0 auto;background:#111111;border-radius:16px;
              overflow:hidden;border:1px solid rgba(212,175,55,0.25)">

    <!-- Header -->
    <div style="background:linear-gradient(135deg,#141414,#1C1C1C);padding:28px 32px;
                border-bottom:1px solid rgba(212,175,55,0.2)">
      <h1 style="margin:0;font-size:22px;color:#D4AF37;font-weight:700">
        Buenos días, {first_name} ✨
      </h1>
      <p style="margin:6px 0 0;color:#666;font-size:14px">
        Tu resumen diario de MarcoAI · {day_label}
      </p>
    </div>

    <!-- Body -->
    <div style="padding:28px 32px;color:#DDDDDD;font-size:15px;line-height:1.6">
      {sections_html}
    </div>

    <!-- Footer -->
    <div style="padding:16px 32px;background:#0D0D0D;text-align:center;
                border-top:1px solid rgba(255,255,255,0.05)">
      <p style="margin:0;font-size:12px;color:#444">
        MarcoAI · Tu asistente personal ·
        <a href="https://www.marcoai.org/settings" style="color:#D4AF37;text-decoration:none">
          Ajusta tus notificaciones
        </a>
      </p>
    </div>
  </div>
</body>
</html>
"""

        # ── Send via Gmail ─────────────────────────────────────────────────────
        from app.services.gmail_service import GmailService
        gmail = GmailService(db, user)
        subject = f"☀️ Tu resumen diario — {today.strftime('%d/%m/%Y')}"
        await gmail.send_email(to=user.email, subject=subject, html_body=html_body)
        logger.info("Daily digest sent to %s (user %s).", user.email, user.id)
        return True

    except Exception as exc:
        logger.error("Failed to send daily digest for user %s: %s", user.id, exc, exc_info=True)
        return False
