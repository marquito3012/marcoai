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
    
    start_str = start_time if isinstance(start_time, str) else start_time.isoformat()
    end_str = end_time if isinstance(end_time, str) else end_time.isoformat()

    event = {
      'summary': summary,
      'description': description,
      'start': {
        'dateTime': start_str,
        'timeZone': 'UTC',
      },
      'end': {
        'dateTime': end_str,
        'timeZone': 'UTC',
      },
    }
    
    event = service.events().insert(calendarId='primary', body=event).execute()
    return event

def update_event(user, event_id, summary=None, start_time=None, end_time=None, description=None):
    """Actualiza un evento existente en el calendario principal"""
    service = get_calendar_service(user)
    
    # Primero obtenemos el evento actual para no sobreescribir campos que no queremos cambiar
    event = service.events().get(calendarId='primary', eventId=event_id).execute()
    
    if summary:
        event['summary'] = summary
    if description is not None:
        event['description'] = description
    
    if start_time:
        start_str = start_time if isinstance(start_time, str) else start_time.isoformat()
        event['start'] = {'dateTime': start_str, 'timeZone': 'UTC'}
    
    if end_time:
        end_str = end_time if isinstance(end_time, str) else end_time.isoformat()
        event['end'] = {'dateTime': end_str, 'timeZone': 'UTC'}
        
    updated_event = service.events().update(calendarId='primary', eventId=event_id, body=event).execute()
    return updated_event
