from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import datetime
from app.config import settings

def get_calendar_service(user):
    """Inicializa el cliente de Google Calendar con los credenciales del usuario"""
    creds = Credentials(
        token=user.google_access_token,
        refresh_token=user.google_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
    )
    return build('calendar', 'v3', credentials=creds)

def list_upcoming_events(user, max_results=10):
    """Obtiene los próximos eventos del calendario principal"""
    service = get_calendar_service(user)
    now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
    
    events_result = service.events().list(
        calendarId='primary', timeMin=now,
        maxResults=max_results, singleEvents=True,
        orderBy='startTime').execute()
        
    return events_result.get('items', [])

def create_event(user, summary, start_time, end_time, description=""):
    """Crea un evento en el calendario principal"""
    service = get_calendar_service(user)
    
    event = {
      'summary': summary,
      'description': description,
      'start': {
        'dateTime': start_time.isoformat(),
        'timeZone': 'UTC',
      },
      'end': {
        'dateTime': end_time.isoformat(),
        'timeZone': 'UTC',
      },
    }
    
    event = service.events().insert(calendarId='primary', body=event).execute()
    return event
