"""
MarcoAI – Habits and Todos Service (Fase 10)
══════════════════════════════════════════════════════════════════════════════
Servicio para la gestión de hábitos y desglose inteligente (LLM) de proyectos en tareas.
"""
from __future__ import annotations

import logging
from datetime import datetime
from sqlalchemy import select

from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Habit, HabitLog
from app.services.llm_gateway import TaskTier, gateway
import json

logger = logging.getLogger(__name__)


class HabitsService:
    def __init__(self, db: AsyncSession, user_id: str):
        self.db = db
        self.user_id = user_id

    async def get_habits(self) -> list[Habit]:
        res = await self.db.execute(select(Habit).where(Habit.user_id == self.user_id))
        return list(res.scalars().all())

    async def track_habit(self, habit_name: str, date_str: str) -> str:
        """Busca o crea un hábito, y luego registra su completitud."""
        res = await self.db.execute(
            select(Habit).where(Habit.user_id == self.user_id, Habit.name == habit_name)
        )
        habit = res.scalar_one_or_none()
        
        if not habit:
            habit = Habit(user_id=self.user_id, name=habit_name)
            self.db.add(habit)
            await self.db.commit()
            await self.db.refresh(habit)

        log_res = await self.db.execute(
            select(HabitLog).where(HabitLog.habit_id == habit.id, HabitLog.completed_date == date_str)
        )
        existing_log = log_res.scalar_one_or_none()
        if existing_log:
            return f"El hábito '{habit_name}' ya estaba registrado el {date_str}."

        new_log = HabitLog(habit_id=habit.id, completed_date=date_str)
        self.db.add(new_log)
        await self.db.commit()
        return f"Hábito '{habit_name}' registrado para el {date_str}."
