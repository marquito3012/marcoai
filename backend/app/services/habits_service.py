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
from app.db.models import Habit, HabitLog, Todo
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

    async def get_todos(self) -> list[Todo]:
        res = await self.db.execute(
            select(Todo).where(Todo.user_id == self.user_id).order_by(Todo.created_at.desc())
        )
        return list(res.scalars().all())

    async def add_todo(self, title: str, parent_id: str | None = None) -> Todo:
        todo = Todo(user_id=self.user_id, title=title, parent_id=parent_id)
        self.db.add(todo)
        await self.db.commit()
        await self.db.refresh(todo)
        return todo

    async def breakdown_project(self, project_title: str) -> str:
        """
        Utiliza el Gateway LLM para romper un proyecto en sub-tareas y las guarda en BD.
        """
        prompt = (
            f"Desglosa el siguiente proyecto en un máximo de 5 tareas accionables paso a paso: '{project_title}'.\n"
            "Responde estrictamente con un JSON array de strings, por ejemplo:\n"
            '["Paso 1...", "Paso 2..."]\n'
            "No incluyas markdown ni texto adicional."
        )
        
        try:
            # Reusing the existing Gateway functionality
            raw_response = await gateway.complete(
                messages=[{"role": "user", "content": prompt}], 
                tier=TaskTier.FAST,
                temperature=0.3
            )
            raw_response = raw_response.strip()
            
            # Limpieza básica si devuelve markdown blocks
            if raw_response.startswith("```json"):
                raw_response = raw_response[7:-3].strip()
            elif raw_response.startswith("```"):
                raw_response = raw_response[3:-3].strip()

            subtasks = json.loads(raw_response)

            # Insert root project
            root = await self.add_todo(title=project_title)
            
            # Insert subtasks
            for task_title in subtasks:
                await self.add_todo(title=task_title, parent_id=root.id)
                
            return f"Proyecto '{project_title}' desglosado en {len(subtasks)} tareas."

        except Exception as exc:
            logger.error("Error breaking down project: %s", exc)
            return f"No se pudo desglosar el proyecto. Error interno."
