"""
MarcoAI – Habits and Todos Service (Fase 10)
══════════════════════════════════════════════════════════════════════════════
Servicio para la gestión de hábitos y desglose inteligente (LLM) de proyectos en tareas.
"""
from __future__ import annotations

import logging
from datetime import datetime, date, timedelta
from sqlalchemy import select

from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Habit, HabitLog
from app.services.llm_gateway import TaskTier, gateway
import json

logger = logging.getLogger(__name__)


def week_start(day: date) -> date:
    """Lunes que inicia la semana ISO/local (lunes a domingo) de `day`."""
    return day - timedelta(days=day.weekday())


class HabitsService:
    def __init__(self, db: AsyncSession, user_id: str):
        self.db = db
        self.user_id = user_id

    async def get_habits(self) -> list[Habit]:
        res = await self.db.execute(select(Habit).where(Habit.user_id == self.user_id))
        return list(res.scalars().all())

    async def create_habit(
        self,
        name: str,
        description: str = None,
        target_days: str = "0,1,2,3,4,5,6",
        target_type: str = "days",
        target_per_week: int | None = None,
    ) -> Habit:
        logger.info(
            "HabitsService: Creating habit '%s' type=%s days=%s weekly_target=%s for user %s",
            name, target_type, target_days, target_per_week, self.user_id,
        )
        habit = Habit(
            user_id=self.user_id,
            name=name,
            description=description,
            # La BD existente tiene target_days NOT NULL; para weekly/flexible se guarda el
            # valor por defecto (ninguna ruta lo interpreta: siempre se filtra por target_type).
            target_days=target_days if target_days else "0,1,2,3,4,5,6",
            target_type=target_type,
            target_per_week=target_per_week if target_type == "weekly" else None,
        )
        self.db.add(habit)
        await self.db.commit()
        await self.db.refresh(habit)
        logger.info("HabitsService: Habit '%s' persisted with ID %s", habit.name, habit.id)
        return habit

    async def delete_habit(self, habit_id: str) -> bool:
        from sqlalchemy import delete
        res = await self.db.execute(select(Habit).where(Habit.id == habit_id, Habit.user_id == self.user_id))
        habit = res.scalar_one_or_none()
        if not habit:
            return False

        await self.db.execute(delete(HabitLog).where(HabitLog.habit_id == habit.id))
        await self.db.delete(habit)
        await self.db.commit()
        return True

    async def toggle_habit(self, habit_id: str, date_str: str) -> tuple[str, bool] | None:
        """Registra o des-registra un hábito en una fecha. Returns (message, completed) | None."""
        res = await self.db.execute(
            select(Habit).where(Habit.id == habit_id, Habit.user_id == self.user_id)
        )
        habit = res.scalar_one_or_none()
        if not habit:
            return None

        log_res = await self.db.execute(
            select(HabitLog).where(HabitLog.habit_id == habit.id, HabitLog.completed_date == date_str)
        )
        existing_log = log_res.scalar_one_or_none()
        if existing_log:
            await self.db.delete(existing_log)
            await self.db.commit()
            return f"Hábito '{habit.name}' desmarcado del {date_str}.", False

        new_log = HabitLog(habit_id=habit.id, completed_date=date_str)
        self.db.add(new_log)
        await self.db.commit()
        return f"Hábito '{habit.name}' registrado para el {date_str}.", True

    async def count_logs_in_week(self, habit_id: str, date_str: str | None = None) -> int:
        """Nº de veces completado en la semana (lunes a domingo) de `date_str`."""
        day = date.fromisoformat(date_str) if date_str else date.today()
        start = week_start(day)
        end = start + timedelta(days=6)
        return await self._count_logs_between(habit_id, start.isoformat(), end.isoformat())

    async def count_logs_in_month(self, habit_id: str, date_str: str | None = None) -> int:
        """Nº de veces completado en el mes calendario de `date_str`."""
        day = date.fromisoformat(date_str) if date_str else date.today()
        start = day.replace(day=1)
        return await self._count_logs_between(habit_id, start.isoformat(), day.isoformat())

    async def _count_logs_between(self, habit_id: str, start: str, end: str) -> int:
        from sqlalchemy import func
        res = await self.db.execute(
            select(func.count(HabitLog.id)).where(
                HabitLog.habit_id == habit_id,
                HabitLog.completed_date >= start,
                HabitLog.completed_date <= end,
            )
        )
        return res.scalar_one() or 0
