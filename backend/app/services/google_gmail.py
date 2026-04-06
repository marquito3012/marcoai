"""
Google Gmail service with minimal memory footprint.
Lazy OAuth credential loading.
"""
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class GoogleGmailService:
    """
    Google Gmail API wrapper with lazy initialization.
    Credentials loaded only when first used.
    """

    def __init__(self, user_id: str):
        self._user_id = user_id
        self._service = None

    def _get_service(self):
        """Lazy service initialization."""
        if self._service is None:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build

            # TODO: Implement proper OAuth token storage/retrieval
            logger.warning("Google Gmail OAuth not fully implemented")

        return self._service

    def read_emails(
        self,
        query: str = "",
        max_results: int = 10,
    ) -> List[Dict[str, Any]]:
        """Read emails matching query."""
        service = self._get_service()
        if not service:
            return []

        try:
            results = service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()

            messages = results.get('messages', [])
            emails = []

            for msg in messages:
                full_msg = service.users().messages().get(
                    userId='me',
                    id=msg['id']
                ).execute()

                emails.append({
                    "id": full_msg.get('id'),
                    "subject": self._get_header(full_msg, 'Subject'),
                    "from": self._get_header(full_msg, 'From'),
                    "date": self._get_header(full_msg, 'Date'),
                    "snippet": full_msg.get('snippet'),
                })

            return emails
        except Exception as e:
            logger.error(f"Gmail read failed: {e}")
            return []

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
    ) -> Dict[str, Any]:
        """Send an email."""
        service = self._get_service()
        if not service:
            return {"error": "Gmail not configured"}

        try:
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            import base64

            message = MIMEMultipart()
            message['to'] = to
            message['subject'] = subject
            message.attach(MIMEText(body, 'plain'))

            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

            sent = service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()

            return {"id": sent.get('id'), "status": "sent"}
        except Exception as e:
            logger.error(f"Gmail send failed: {e}")
            return {"error": str(e)}

    def _get_header(self, message: Dict, name: str) -> str:
        """Extract header from message."""
        headers = message.get('payload', {}).get('headers', [])
        for header in headers:
            if header.get('name') == name:
                return header.get('value', '')
        return ''
