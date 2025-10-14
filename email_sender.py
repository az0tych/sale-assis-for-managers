import base64
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from config import Config

def send_message_via_gmail(user: 'User', to_email: str, subject: str, body: str):
    creds = Credentials(
        token=user.gmail_token,
        refresh_token=user.gmail_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=Config.GMAIL_CLIENT_ID,
        client_secret=Config.GMAIL_CLIENT_SECRET,
        scopes=['https://www.googleapis.com/auth/gmail.send']
    )
    service = build('gmail', 'v1', credentials=creds)
    msg = MIMEText(body, _charset='utf-8')
    msg['to'] = to_email
    msg['from'] = user.email
    msg['subject'] = subject
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    return service.users().messages().send(userId='me', body={'raw': raw}).execute()
