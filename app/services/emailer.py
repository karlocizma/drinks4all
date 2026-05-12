import smtplib
from email.message import EmailMessage

from app.core.settings import settings


def parse_recipients(value: str) -> list[str]:
    raw_parts = value.replace(";", ",").split(",")
    return [part.strip() for part in raw_parts if part.strip()]


def send_email(recipient: str, subject: str, body: str, html: str | None = None) -> None:
    msg = EmailMessage()
    msg["From"] = settings.smtp_sender
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.set_content(body)
    if html:
        msg.add_alternative(html, subtype="html")

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
        if settings.smtp_use_tls:
            smtp.starttls()
        if settings.smtp_username:
            smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(msg)
