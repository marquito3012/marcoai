"""
Calendar module router.
Google Calendar integration.
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional

router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.get("/events")
async def list_events(
    user_id: str = Query(...),
    date: Optional[str] = Query(None, description="Single date (YYYY-MM-DD)"),
    start_date: Optional[str] = Query(None, description="Range start (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Range end (YYYY-MM-DD)"),
):
    """
    List calendar events.
    Supports single-day (?date=) or range (?start_date=&end_date=) queries.
    """
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

    service = GoogleCalendarService(user_id)
    events = service.list_events(start_date, end_date)
    return {"events": events}


@router.post("/events")
async def create_event(
    title: str,
    start_datetime: str,
    end_datetime: str,
    description: Optional[str] = None,
    location: Optional[str] = None,
    user_id: str = Query(...),
):
    """Create a new calendar event."""
    from ...services.google_calendar import GoogleCalendarService

    service = GoogleCalendarService(user_id)
    result = service.create_event(title, start_datetime, end_datetime, description, location)
    return result


@router.delete("/events/{event_id}")
async def delete_event(
    event_id: str,
    user_id: str = Query(...),
):
    """Delete a calendar event."""
    from ...services.google_calendar import GoogleCalendarService

    service = GoogleCalendarService(user_id)
    success = service.delete_event(event_id)
    return {"deleted": success}
