from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import base64
from email.message import EmailMessage
from app.config import settings

def get_gmail_service(user):
    """Inicializa el cliente de Gmail con los credenciales del usuario"""
    creds = Credentials(
        token=user.google_access_token,
        refresh_token=user.google_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
    )
    return build('gmail', 'v1', credentials=creds)

def list_unread_messages(user, max_results=10):
    """Obtiene los últimos mensajes no leídos"""
    service = get_gmail_service(user)
    
    results = service.users().messages().list(
        userId='me', labelIds=['INBOX', 'UNREAD'], maxResults=max_results).execute()
        
    messages = results.get('messages', [])
    
    detailed_messages = []
    for msg in messages:
        # Obtenemos el detalle (headers y snippet)
        msg_detail = service.users().messages().get(userId='me', id=msg['id'], format='metadata', metadataHeaders=['From', 'Subject', 'Date']).execute()
        headers = msg_detail.get('payload', {}).get('headers', [])
        
        # Extraemos infos
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "Sin asunto")
        sender = next((h['value'] for h in headers if h['name'] == 'From'), "Desconocido")
        
        detailed_messages.append({
            "id": msg['id'],
            "snippet": msg_detail.get('snippet', ''),
            "subject": subject,
            "from": sender
        })
        
    return detailed_messages

def create_draft(user, to, subject, body_text):
    """Crea un borrador de correo en Gmail"""
    service = get_gmail_service(user)
    
    message = EmailMessage()
    message.set_content(body_text)
    message['To'] = to
    message['From'] = user.email
    message['Subject'] = subject

    # codificado base64url
    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    create_message = {'message': {'raw': encoded_message}}
    
    draft = service.users().drafts().create(userId='me', body=create_message).execute()
    return draft
