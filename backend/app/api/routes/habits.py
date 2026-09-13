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
    target_type: str = "days"  # days | weekly | flexible
    target_per_week: int | None = None

class HabitTrack(BaseModel):
    habit_id: str
    date: str  # YYYY-MM-DD

# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/summary", summary="Obtener todos los hábitos del usuario")
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

    today_habits_data = []
    other_habits_data = []
    weekly_habits_data = []
    flexible_habits_data = []
    for h in habits:
        log_res = await db.execute(
            select(HabitLog).where(HabitLog.habit_id == h.id, HabitLog.completed_date == today_iso)
        )
        is_done_today = log_res.scalar_one_or_none() is not None

        if h.target_type == "weekly":
            weekly_habits_data.append({
                "id": h.id,
                "name": h.name,
                "is_done_today": is_done_today,
                "target_type": h.target_type,
                "target_per_week": h.target_per_week or 3,
                "done_this_week": await service.count_logs_in_week(h.id, today_iso),
            })
            continue

        if h.target_type == "flexible":
            flexible_habits_data.append({
                "id": h.id,
                "name": h.name,
                "is_done_today": is_done_today,
                "target_type": h.target_type,
                "done_this_week": await service.count_logs_in_week(h.id, today_iso),
                "done_this_month": await service.count_logs_in_month(h.id, today_iso),
            })
            continue

        # Tipo 'days': se muestra en la lista de hoy o en "otros", según programación
        habit_dict = {
            "id": h.id,
            "name": h.name,
            "is_done_today": is_done_today,
            "target_days": h.target_days,
            "target_type": h.target_type,
        }

        target_days_list = [int(d) for d in h.target_days.split(",")] if h.target_days else [0,1,2,3,4,5,6]

        if weekday_num in target_days_list:
            today_habits_data.append(habit_dict)
        else:
            other_habits_data.append(habit_dict)

    return {
        "habits": today_habits_data,
        "other_habits": other_habits_data,
        "weekly_habits": weekly_habits_data,
        "flexible_habits": flexible_habits_data,
        "todos": [] # Redirigido a Google Calendar
    }

@router.get("/logs", summary="Obtener historial de hábitos para gráfico de contribuciones")
async def get_habit_logs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Devuelve datos de consistencia (éxito/fallo) para el gráfico de contribuciones.

    El rojo lo generan SOLO los hábitos de tipo 'days' (tienen día concreto).
    Los semanales/flexibles pintan el día de verde cuando se registran, sin arriesgar rojo.
    """
    import datetime

    # 1. Obtener todos los hábitos del usuario
    res_habits = await db.execute(select(Habit).where(Habit.user_id == current_user.id))
    habits = res_habits.scalars().all()

    # 2. Obtener todos los logs de los últimos 91 días
    today = datetime.date.today()
    start_date = today - datetime.timedelta(days=90)

    stmt = (
        select(HabitLog.completed_date, HabitLog.habit_id)
        .join(Habit)
        .where(Habit.user_id == current_user.id, HabitLog.completed_date >= start_date.isoformat())
    )
    res_logs = await db.execute(stmt)

    # Organizar logs por fecha: { "2023-10-01": {habit_id1, habit_id2} }
    logs_by_date = {}
    for log_date, habit_id in res_logs.all():
        if log_date not in logs_by_date:
            logs_by_date[log_date] = set()
        logs_by_date[log_date].add(habit_id)

    # 3. Calcular estado para cada día
    data = []
    for i in range(91):
        day = today - datetime.timedelta(days=i)
        day_iso = day.isoformat()
        weekday = day.weekday() # 0=Mon, 6=Sun

        # Hábitos de tipo 'days' programados para este día de la semana
        scheduled_ids = []
        for h in habits:
            if h.target_type != "days":
                continue
            # Solo consideramos el hábito si ya existía en esa fecha
            if h.created_at.date() <= day:
                target_days = [int(d) for d in h.target_days.split(",")] if h.target_days else [0,1,2,3,4,5,6]
                if weekday in target_days:
                    scheduled_ids.append(h.id)

        done_ids = logs_by_date.get(day_iso, set())

        status = "none" # Color neutral (sin hábitos programados ni actividad)
        if scheduled_ids:
            # Si se han completado todos los programados -> Éxito (Verde)
            if all(sid in done_ids for sid in scheduled_ids):
                status = "success"
            # Si es un día pasado y falta alguno -> Fallo (Rojo)
            elif day < today:
                status = "failed"
            # Si es hoy y falta alguno -> Aún puede completarlo
            else:
                status = "pending"
        elif done_ids:
            # Sin programación de tipo 'days' pero con actividad registrada
            # (semanales o flexibles) -> Verde, sin riesgo de rojo.
            status = "done"

        data.append({
            "date": day_iso,
            "status": status,
            "count": len(done_ids),
            "scheduled": len(scheduled_ids)
        })

    return data

@router.post("/track", summary="Marcar/desmarcar un hábito como completado")
async def track_habit_completion(
    body: HabitTrack,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = HabitsService(db, current_user.id)
    result = await service.toggle_habit(body.habit_id, body.date)
    if result is None:
        raise HTTPException(status_code=404, detail="Hábito no encontrado")
    msg, completed = result
    return {"message": msg, "completed": completed}

@router.post("", summary="Crear un nuevo hábito")
async def create_habit(
    body: HabitCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.target_type not in ("days", "weekly", "flexible"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="target_type debe ser 'days', 'weekly' o 'flexible'",
        )
    if body.target_type == "weekly" and not (body.target_per_week and 1 <= body.target_per_week <= 7):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Los hábitos semanales requieren target_per_week entre 1 y 7",
        )

    service = HabitsService(db, current_user.id)
    habit = await service.create_habit(
        name=body.name,
        description=body.description,
        target_days=body.target_days,
        target_type=body.target_type,
        target_per_week=body.target_per_week,
    )
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
