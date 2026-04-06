"""
Food module router.
Shopping list and meal planning.
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional

router = APIRouter(prefix="/food", tags=["food"])


@router.get("/shopping")
async def get_shopping_list(
    user_id: str = Query(...),
    include_purchased: bool = False,
):
    """Get shopping list items."""
    from ...database import get_db
    from ...agent.tools import shopping_list_items

    db = next(get_db())
    items = shopping_list_items(include_purchased, user_id, db)
    return {"items": items}


@router.post("/shopping/add")
async def add_to_shopping_list(
    item: str,
    quantity: Optional[str] = None,
    user_id: str = Query(...),
):
    """Add item to shopping list."""
    from ...database import get_db
    from ...agent.tools import shopping_add_item

    db = next(get_db())
    result = shopping_add_item(item, quantity, user_id, db)
    return result


@router.post("/shopping/purchase/{item_id}")
async def mark_purchased(
    item_id: str,
    user_id: str = Query(...),
):
    """Mark an item as purchased."""
    from ...database import get_db

    db = next(get_db())
    with db.transaction() as conn:
        conn.execute("""
            UPDATE shopping_list SET purchased = 1 WHERE id = ? AND user_id = ?
        """, (item_id, user_id))

    return {"status": "purchased"}


@router.delete("/shopping/{item_id}")
async def remove_from_shopping_list(
    item_id: str,
    user_id: str = Query(...),
):
    """Remove item from shopping list."""
    from ...database import get_db

    db = next(get_db())
    with db.transaction() as conn:
        conn.execute("""
            DELETE FROM shopping_list WHERE id = ? AND user_id = ?
        """, (item_id, user_id))

    return {"status": "removed"}


@router.get("/meal-plan")
async def get_meal_plan(
    week_start: str,
    user_id: str = Query(...),
):
    """Get weekly meal plan."""
    from ...database import get_db

    db = next(get_db())
    with db.connection() as conn:
        cursor = conn.execute("""
            SELECT day, meal_type, description
            FROM meal_plan
            WHERE user_id = ? AND week_start = ?
            ORDER BY day, meal_type
        """, (user_id, week_start))
        meals = [dict(row) for row in cursor.fetchall()]

    return {"meals": meals}


@router.post("/meal-plan")
async def set_meal_plan(
    week_start: str,
    day: int,
    meal_type: str,
    description: str,
    user_id: str = Query(...),
):
    """Set a meal in the weekly plan."""
    import uuid
    from ...database import get_db

    db = next(get_db())
    meal_id = str(uuid.uuid4())

    with db.transaction() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO meal_plan (id, user_id, week_start, day, meal_type, description)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (meal_id, user_id, week_start, day, meal_type, description))

    return {"id": meal_id, "status": "saved"}
