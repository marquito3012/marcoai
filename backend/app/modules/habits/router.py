"""
Habits module router.
Binary habit tracking with streak calculations.
"""
from fastapi import APIRouter, Query, HTTPException, Body
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

router = APIRouter(prefix="/habits", tags=["habits"])


class TrackHabitRequest(BaseModel):
    """JSON body for tracking a habit."""
    habit_name: str
    date: str
    user_id: str


@router.post("/track")
async def track_habit(req: TrackHabitRequest):
    """Mark a habit as completed."""
    from ...database import get_db
    from ...agent.tools import habits_track

    db = next(get_db())
    result = habits_track(req.habit_name, req.date, req.user_id, db)
    return result


@router.get("/{habit_name}/streak")
async def get_streak(
    habit_name: str,
    user_id: str = Query(...),
):
    """Get current habit streak."""
    from ...database import get_db
    from ...agent.tools import habits_get_streak

    db = next(get_db())
    result = habits_get_streak(habit_name, user_id, db)
    return result


@router.get("")
async def list_habits(
    user_id: str = Query(...),
    active_only: bool = True,
):
    """List all habits for a user, with today's completion status."""
    from ...database import get_db

    today = datetime.now().strftime("%Y-%m-%d")
    db = next(get_db())

    with db.connection() as conn:
        query = """
            SELECT
                h.id,
                h.name,
                h.frequency,
                h.active,
                CASE WHEN hc.completed IS NOT NULL THEN 1 ELSE 0 END as completed
            FROM habits h
            LEFT JOIN habit_completions hc
                ON h.id = hc.habit_id AND hc.date = ?
            WHERE h.user_id = ?
        """
        params = [today, user_id]

        if active_only:
            query += " AND h.active = 1"

        cursor = conn.execute(query, params)
        habits = [dict(row) for row in cursor.fetchall()]

    return {"habits": habits}


@router.post("/create")
async def create_habit(
    name: str,
    frequency: str,  # JSON: {"type": "daily"|"weekdays", "days": [0,1,2]}
    user_id: str = Query(...),
):
    """Create a new habit."""
    import uuid
    from ...database import get_db

    db = next(get_db())
    habit_id = str(uuid.uuid4())

    with db.transaction() as conn:
        conn.execute("""
            INSERT INTO habits (id, user_id, name, frequency, active)
            VALUES (?, ?, ?, ?, 1)
        """, (habit_id, user_id, name, frequency))

    return {"id": habit_id, "status": "created"}
