"""
RAG Memory module router.
Semantic search over conversation history.
"""
from fastapi import APIRouter, Query, HTTPException

router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("/search")
async def search_memory(
    q: str = Query(..., description="Search query"),
    limit: int = Query(5, description="Max results"),
    user_id: str = Query(...),
):
    """Search conversation history."""
    from ...database import get_db
    from ...agent.tools import memory_search

    db = next(get_db())
    results = memory_search(q, limit, user_id, db)
    return {"results": results}


@router.get("/context")
async def get_user_context(
    user_id: str = Query(...),
    max_turns: int = Query(10, description="Max conversation turns"),
):
    """Get recent conversation context for a user."""
    from ...database import get_db
    from ...rag.engine import RAGEngine

    db = next(get_db())
    engine = RAGEngine(db)
    context = engine.get_user_context(user_id, max_turns)

    return {"context": context}
