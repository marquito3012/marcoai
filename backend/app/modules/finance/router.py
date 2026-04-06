"""
Finance module router.
Handles expenses, income, and balance calculations.
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional

router = APIRouter(prefix="/finance", tags=["finance"])


@router.get("/balance")
async def get_balance(
    month: str = Query(..., description="Month in YYYY-MM format"),
    user_id: str = Query(..., description="User ID"),
):
    """Get monthly balance summary."""
    from ...database import get_db
    from ...agent.tools import finance_get_balance

    db = next(get_db())
    result = finance_get_balance(month, user_id, db)
    return result


@router.post("/transaction")
async def log_transaction(
    type: str,
    category: str,
    amount: float,
    date: str,
    description: Optional[str] = None,
    user_id: str = Query(...),
):
    """Log a financial transaction."""
    from ...database import get_db
    from ...agent.tools import finance_log_transaction

    db = next(get_db())
    result = finance_log_transaction(
        type=type,
        category=category,
        amount=amount,
        description=description,
        date=date,
        user_id=user_id,
        db=db,
    )
    return result


@router.get("/transactions")
async def list_transactions(
    month: str = Query(...),
    type: Optional[str] = None,
    user_id: str = Query(...),
):
    """List transactions for a month."""
    from ...database import get_db

    db = next(get_db())
    with db.connection() as conn:
        query = """
            SELECT id, type, category, amount, description, date, created_at
            FROM finance_transactions
            WHERE user_id = ? AND strftime('%Y-%m', date) = ?
        """
        params = [user_id, month]

        if type:
            query += " AND type = ?"
            params.append(type)

        query += " ORDER BY date DESC"

        cursor = conn.execute(query, params)
        transactions = [dict(row) for row in cursor.fetchall()]

    return {"transactions": transactions}
