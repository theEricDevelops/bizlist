import os
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from sqlalchemy.orm import Session
from email.mime.multipart import MIMEMultipart
import base64
from app.services.logger import Logger

log = Logger('service-gmail')

# If modifying these scopes, delete the file token.json
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

class GmailService:
    def __init__(self):
        self.service = self.get_gmail_service()

    def connect():
        """Authenticate and return Gmail API service."""
        creds = None
        # The file token.json stores the user's access and refresh tokens
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        
        # If there are no valid credentials, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        
        return build('gmail', 'v1', credentials=creds)

    def draft(to: str, subject: str, message_text: str, sender: str = 'me', db: Session = None) -> dict:
        """Draft a message for an email."""
        try:
            message = MIMEMultipart(message_text)
            message['to'] = to
            message['from'] = sender  # 'me' refers to the authenticated user
            message['subject'] = subject
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            return {'raw': raw}
        except Exception as error:
            log.error(f'An error occurred: {error}')
            return None

    def send(service, message):
        """Send an email message."""
        try:
            message = (service.users().messages().send(userId='me', body=message)
                    .execute())
            log.debug('Message Id: %s' % message['id'])
            return message
        except Exception as error:
            log.error(f'An error occurred: {error}')
            return None
    
