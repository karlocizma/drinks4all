import smtplib
from email.message import EmailMessage
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.settings import settings

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
_email_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)


def render_email(template_name: str, **context) -> str:
    return _email_env.get_template(template_name).render(**context)


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
