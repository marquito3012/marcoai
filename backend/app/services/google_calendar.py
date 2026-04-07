"""
Google Calendar service with minimal memory footprint.
Lazy OAuth credential loading.
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class GoogleCalendarService:
    """
    Google Calendar API wrapper with lazy initialization.
    Credentials loaded only when first used.
    """

    def __init__(self, user_id: str, credentials_dict: Optional[Dict[str, Any]] = None):
        self._user_id = user_id
        self._credentials_dict = credentials_dict
        self._service = None

    def _get_service(self):
        """Lazy service initialization."""
        if self._service is None and self._credentials_dict:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            from app.config import get_settings

            settings = get_settings()
            
            # Reconstruct Credentials object
            creds = Credentials(
                token=self._credentials_dict.get("access_token"),
                refresh_token=self._credentials_dict.get("refresh_token"),
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.google_client_id,
                client_secret=settings.google_client_secret,
                scopes=["https://www.googleapis.com/auth/calendar.readonly", "https://www.googleapis.com/auth/calendar.events"]
            )
            
            try:
                self._service = build('calendar', 'v3', credentials=creds)
            except Exception as e:
                logger.error(f"Failed to build Calendar service: {e}")

        return self._service

    def list_events(
        self,
        start_date: str,
        end_date: str,
    ) -> List[Dict[str, Any]]:
        """List calendar events in date range."""
        service = self._get_service()
        if not service:
            return []

        try:
            events_result = service.events().list(
                calendarId='primary',
                timeMin=start_date + 'T00:00:00Z',
                timeMax=end_date + 'T23:59:59Z',
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])
            return [
                {
                    "id": event.get('id'),
                    "summary": event.get('summary'),
                    "start": event.get('start', {}).get('dateTime', event.get('start', {}).get('date')),
                    "end": event.get('end', {}).get('dateTime', event.get('end', {}).get('date')),
                }
                for event in events
            ]
        except Exception as e:
            logger.error(f"Calendar list failed: {e}")
            return []

    def create_event(
        self,
        title: str,
        start_datetime: str,
        end_datetime: str,
        description: Optional[str] = None,
        location: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new calendar event."""
        service = self._get_service()
        if not service:
            return {"error": "Google Calendar not configured"}

        try:
            event = {
                'summary': title,
                'start': {'dateTime': start_datetime, 'timeZone': 'UTC'},
                'end': {'dateTime': end_datetime, 'timeZone': 'UTC'},
            }
            if description:
                event['description'] = description
            if location:
                event['location'] = location

            created = service.events().insert(
                calendarId='primary',
                body=event
            ).execute()

            return {"id": created.get('id'), "status": "created"}
        except Exception as e:
            logger.error(f"Calendar create failed: {e}")
            return {"error": str(e)}

    def delete_event(self, event_id: str) -> bool:
        """Delete a calendar event."""
        service = self._get_service()
        if not service:
            return False

        try:
            service.events().delete(
                calendarId='primary',
                eventId=event_id
            ).execute()
            return True
        except Exception as e:
            logger.error(f"Calendar delete failed: {e}")
            return False
