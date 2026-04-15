"""
MarcoAI – Habits and Todos API Router (Fase 10)
══════════════════════════════════════════════════════════════════════════════
Endpoints para consultar y modificar hábitos, tareas y graficar contribuciones.
"""
from fastapi import APIRouter, Depends, Body
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any

from app.api.deps import get_current_user
from app.db.base import get_db
from app.db.models import User, HabitLog
from app.services.habits_service import HabitsService
from sqlalchemy import select

router = APIRouter(prefix="/habits", tags=["Hábitos"])


@router.get("/logs", summary="Obtener historial de hábitos para gráfico de contribuciones")
async def get_habit_logs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Devuelve datos compatibles con un 'GitHub contributions graph'."""
    # Obtenemos logs haciendo un conteno por fecha
    from sqlalchemy import func
    from app.db.models import Habit
    
    stmt = (
        select(HabitLog.completed_date, func.count(HabitLog.id).label("count"))
        .join(Habit)
        .where(Habit.user_id == current_user.id)
        .group_by(HabitLog.completed_date)
    )
    res = await db.execute(stmt)
    
    data = []
    for row in res.all():
        data.append({"date": row[0], "count": row[1]})
        
    return data

@router.post("/breakdown", summary="Romper proyecto en subtareas via LLM")
async def breakdown_project(
    project_title: str = Body(..., embed=True),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    service = HabitsService(db, current_user.id)
    result = await service.breakdown_project(project_title)
    return {"message": result}
