from __future__ import annotations

from dataclasses import dataclass
from email.message import EmailMessage
import os
import smtplib


@dataclass(frozen=True)
class MailSettings:
    host: str
    port: int
    username: str
    password: str
    sender: str
    recipients: tuple[str, ...]
    use_ssl: bool


def load_mail_settings() -> MailSettings:
    recipients = tuple(
        item.strip()
        for item in os.environ.get("MAIL_TO", "").split(",")
        if item.strip()
    )
    settings = MailSettings(
        host=os.environ["SMTP_HOST"],
        port=int(os.environ.get("SMTP_PORT", "465")),
        username=os.environ["SMTP_USER"],
        password=_clean_secret(os.environ["SMTP_PASSWORD"]),
        sender=os.environ.get("MAIL_FROM", os.environ["SMTP_USER"]),
        recipients=recipients,
        use_ssl=os.environ.get("SMTP_SSL", "true").lower() in {"1", "true", "yes"},
    )
    if not settings.recipients:
        raise ValueError("MAIL_TO is required. Use commas for multiple recipients.")
    return settings


def _clean_secret(value: str) -> str:
    return "".join(value.split())


def send_email(settings: MailSettings, subject: str, text: str, html: str) -> None:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.sender
    message["To"] = ", ".join(settings.recipients)
    message.set_content(text)
    message.add_alternative(html, subtype="html")

    if settings.use_ssl:
        with smtplib.SMTP_SSL(settings.host, settings.port, timeout=30) as smtp:
            smtp.login(settings.username, settings.password)
            smtp.send_message(message)
        return

    with smtplib.SMTP(settings.host, settings.port, timeout=30) as smtp:
        smtp.starttls()
        smtp.login(settings.username, settings.password)
        smtp.send_message(message)
