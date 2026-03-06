import smtplib
from email.message import EmailMessage

from app.core.settings import settings


def send_email(recipient: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["From"] = settings.smtp_sender
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        smtp.send_message(msg)
