"""
Leisure module router.
Events and game deals tracking.
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List

router = APIRouter(prefix="/leisure", tags=["leisure"])


@router.get("/events")
async def list_events(
    user_id: str = Query(...),
    upcoming_only: bool = True,
):
    """List leisure events."""
    from ...database import get_db
    from datetime import datetime

    db = next(get_db())
    with db.connection() as conn:
        query = """
            SELECT id, name, event_date, location, notes, created_at
            FROM leisure_events
            WHERE user_id = ?
        """
        params = [user_id]

        if upcoming_only:
            today = datetime.now().strftime("%Y-%m-%d")
            query += " AND event_date >= ?"
            params.append(today)

        query += " ORDER BY event_date ASC"

        cursor = conn.execute(query, params)
        events = [dict(row) for row in cursor.fetchall()]

    return {"events": events}


@router.post("/events")
async def create_event(
    name: str,
    event_date: str,
    location: Optional[str] = None,
    notes: Optional[str] = None,
    user_id: str = Query(...),
):
    """Create a leisure event."""
    import uuid
    from ...database import get_db

    db = next(get_db())
    event_id = str(uuid.uuid4())

    with db.transaction() as conn:
        conn.execute("""
            INSERT INTO leisure_events (id, user_id, name, event_date, location, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (event_id, user_id, name, event_date, location, notes))

    return {"id": event_id, "status": "created"}


@router.delete("/events/{event_id}")
async def delete_event(
    event_id: str,
    user_id: str = Query(...),
):
    """Delete a leisure event."""
    from ...database import get_db

    db = next(get_db())
    with db.transaction() as conn:
        conn.execute("""
            DELETE FROM leisure_events WHERE id = ? AND user_id = ?
        """, (event_id, user_id))

    return {"status": "deleted"}


@router.get("/deals")
async def list_game_deals(
    user_id: str = Query(...),
    min_discount: Optional[int] = None,
):
    """List tracked game deals."""
    from ...database import get_db

    db = next(get_db())
    with db.connection() as conn:
        query = """
            SELECT id, title, store, price, discount_percent, url, checked_at
            FROM game_deals
            WHERE user_id = ?
        """
        params = [user_id]

        if min_discount:
            query += " AND discount_percent >= ?"
            params.append(min_discount)

        query += " ORDER BY discount_percent DESC"

        cursor = conn.execute(query, params)
        deals = [dict(row) for row in cursor.fetchall()]

    return {"deals": deals}


@router.post("/deals")
async def track_game_deal(
    title: str,
    store: str,
    price: float,
    discount_percent: Optional[int] = None,
    url: Optional[str] = None,
    user_id: str = Query(...),
):
    """Track a game deal."""
    import uuid
    from ...database import get_db

    db = next(get_db())
    deal_id = str(uuid.uuid4())

    with db.transaction() as conn:
        conn.execute("""
            INSERT INTO game_deals (id, user_id, title, store, price, discount_percent, url)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (deal_id, user_id, title, store, price, discount_percent, url))

    return {"id": deal_id, "status": "tracked"}
