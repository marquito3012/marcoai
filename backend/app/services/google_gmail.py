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

def list_messages(user, q=None, label_ids=None, max_results=10):
    """Lista mensajes con filtros opcionales (query o etiquetas)"""
    service = get_gmail_service(user)
    
    params = {'userId': 'me', 'maxResults': max_results}
    if q: params['q'] = q
    if label_ids: params['labelIds'] = label_ids
    
    results = service.users().messages().list(**params).execute()
    messages = results.get('messages', [])
    
    detailed_messages = []
    for msg in messages:
        msg_detail = service.users().messages().get(userId='me', id=msg['id'], format='metadata', metadataHeaders=['From', 'Subject', 'Date']).execute()
        headers = msg_detail.get('payload', {}).get('headers', [])
        
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "Sin asunto")
        sender = next((h['value'] for h in headers if h['name'] == 'From'), "Desconocido")
        
        detailed_messages.append({
            "id": msg['id'],
            "snippet": msg_detail.get('snippet', ''),
            "subject": subject,
            "from": sender
        })
        
    return detailed_messages

def list_unread_messages(user, max_results=10):
    """Legacy helper: Obtiene los últimos mensajes no leídos"""
    return list_messages(user, label_ids=['INBOX', 'UNREAD'], max_results=max_results)

def create_draft(user, to, subject, body_text):
    """Crea un borrador de correo en Gmail"""
    service = get_gmail_service(user)
    
    message = EmailMessage()
    message.set_content(body_text)
    message['To'] = to
    message['From'] = user.email
    message['Subject'] = subject

    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    create_message = {'message': {'raw': encoded_message}}
    
    draft = service.users().drafts().create(userId='me', body=create_message).execute()
    return draft

def send_email(user, to, subject, body_text):
    """Envía un correo directamente"""
    service = get_gmail_service(user)
    
    message = EmailMessage()
    message.set_content(body_text)
    message['To'] = to
    message['From'] = user.email
    message['Subject'] = subject

    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    create_message = {'raw': encoded_message}
    
    send_msg = service.users().messages().send(userId='me', body=create_message).execute()
    return send_msg

def list_labels(user):
    """Obtiene la lista de etiquetas (carpetas) de Gmail"""
    service = get_gmail_service(user)
    results = service.users().labels().list(userId='me').execute()
    return results.get('labels', [])

def modify_message_labels(user, message_id, add_labels=None, remove_labels=None):
    """Añade o quita etiquetas de un mensaje (ej: marcar como leído, mover a carpeta)"""
    service = get_gmail_service(user)
    
    body = {}
    if add_labels:
        body['addLabelIds'] = add_labels
    if remove_labels:
        body['removeLabelIds'] = remove_labels
        
    result = service.users().messages().modify(userId='me', id=message_id, body=body).execute()
    return result

def create_label(user, label_name):
    """Crea una nueva etiqueta (carpeta) en Gmail"""
    service = get_gmail_service(user)
    label_object = {
        'name': label_name,
        'labelListVisibility': 'labelShow',
        'messageListVisibility': 'show'
    }
    result = service.users().labels().create(userId='me', body=label_object).execute()
    return result
