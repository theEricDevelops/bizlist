import base64
from email.mime.multipart import MIMEMultipart

from api.services.gmail import GmailService
from api.logger import Logger

log = Logger('gmail-utils')

class GmailUtils:
    def __init__(self, service: GmailService):
        self.service = service
        log.debug('GmailUtils initialized')

    def create(to, subject, message_text):
        """Create a message for an email."""
        try:
            message = MIMEMultipart(message_text)
            message['to'] = to
            message['from'] = 'me'  # 'me' refers to the authenticated user
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
            print('Message Id: %s' % message['id'])
            return message
        except Exception as error:
            log.error(f'An error occurred: {error}')
            return None