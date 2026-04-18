"""
MarcoAI – Habits and Todos API Router (Fase 10)
══════════════════════════════════════════════════════════════════════════════
Endpoints para consultar y modificar hábitos, tareas y graficar contribuciones.
"""
from fastapi import APIRouter, Depends, Body, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.db.base import get_db
from app.db.models import User, HabitLog, Habit
from app.services.habits_service import HabitsService
from sqlalchemy import select, update, delete

router = APIRouter(prefix="/habits", tags=["Hábitos"])

# ── Schemas ───────────────────────────────────────────────────────────────────

# class TodoCreate(BaseModel):
#     title: str

class HabitCreate(BaseModel):
    name: str
    description: str | None = None
    target_days: str | None = "0,1,2,3,4,5,6"

class HabitTrack(BaseModel):
    habit_id: str
    date: str  # YYYY-MM-DD

# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/summary", summary="Obtener todos los hábitos y tareas del usuario")
async def get_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    service = HabitsService(db, current_user.id)
    habits = await service.get_habits()
    
    # Get today's completion status for habits
    import datetime
    today = datetime.date.today()
    today_iso = today.isoformat()
    weekday_num = today.weekday() # 0 is Monday, 6 is Sunday
    
    # Simple check for each habit if it has a log for today
    today_habits_data = []
    other_habits_data = []
    for h in habits:
        log_res = await db.execute(
            select(HabitLog).where(HabitLog.habit_id == h.id, HabitLog.completed_date == today_iso)
        )
        is_done_today = log_res.scalar_one_or_none() is not None
        
        habit_dict = {
            "id": h.id,
            "name": h.name,
            "is_done_today": is_done_today,
            "target_days": h.target_days
        }
        
        target_days_list = [int(d) for d in h.target_days.split(",")] if h.target_days else [0,1,2,3,4,5,6]
        
        if weekday_num in target_days_list:
            today_habits_data.append(habit_dict)
        else:
            other_habits_data.append(habit_dict)

    return {
        "habits": today_habits_data,
        "other_habits": other_habits_data,
        "todos": [] # Redirigido a Google Calendar
    }

@router.get("/logs", summary="Obtener historial de hábitos para gráfico de contribuciones")
async def get_habit_logs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Devuelve datos compatibles con un 'GitHub contributions graph'."""
    from sqlalchemy import func
    
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

@router.post("/track", summary="Marcar un hábito como completado")
async def track_habit_completion(
    body: HabitTrack,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify owner
    res = await db.execute(select(Habit).where(Habit.id == body.habit_id, Habit.user_id == current_user.id))
    habit = res.scalar_one_or_none()
    if not habit:
        raise HTTPException(status_code=404, detail="Hábito no encontrado")
    
    service = HabitsService(db, current_user.id)
    msg = await service.track_habit(habit.name, body.date)
    return {"message": msg}

@router.post("", summary="Crear un nuevo hábito")
async def create_habit(
    body: HabitCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = HabitsService(db, current_user.id)
    habit = await service.create_habit(name=body.name, description=body.description, target_days=body.target_days)
    return {"id": habit.id, "name": habit.name, "message": "Hábito creado"}

@router.delete("/{habit_id}", summary="Eliminar un hábito")
async def delete_habit(
    habit_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = HabitsService(db, current_user.id)
    success = await service.delete_habit(habit_id)
    if not success:
        raise HTTPException(status_code=404, detail="Hábito no encontrado")
    return {"message": "Hábito eliminado"}
