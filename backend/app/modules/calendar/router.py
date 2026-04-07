"""
Calendar module router.
Google Calendar integration.
"""
from fastapi import APIRouter, Query, HTTPException, Request
from typing import Optional
from ...auth.router import get_session

router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.get("/events")
async def list_events(
    request: Request,
    date: Optional[str] = Query(None, description="Single date (YYYY-MM-DD)"),
    start_date: Optional[str] = Query(None, description="Range start (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Range end (YYYY-MM-DD)"),
):
    """
    List calendar events.
    Supports single-day (?date=) or range (?start_date=&end_date=) queries.
    """
    session = get_session(request)
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Resolve date range
    if date:
        start_date = date
        end_date = date
    elif not start_date or not end_date:
        # Default to today
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        start_date = start_date or today
        end_date = end_date or today

    from ...services.google_calendar import GoogleCalendarService

    service = GoogleCalendarService(session.get("sub"), session)
    events = service.list_events(start_date, end_date)
    return {"events": events}


@router.post("/events")
async def create_event(
    request: Request,
    title: str,
    start_datetime: str,
    end_datetime: str,
    description: Optional[str] = None,
    location: Optional[str] = None,
):
    """Create a new calendar event."""
    session = get_session(request)
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    from ...services.google_calendar import GoogleCalendarService

    service = GoogleCalendarService(session.get("sub"), session)
    result = service.create_event(title, start_datetime, end_datetime, description, location)
    return result


@router.delete("/events/{event_id}")
async def delete_event(
    request: Request,
    event_id: str,
):
    """Delete a calendar event."""
    session = get_session(request)
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    from ...services.google_calendar import GoogleCalendarService

    service = GoogleCalendarService(session.get("sub"), session)
    success = service.delete_event(event_id)
    return {"deleted": success}
