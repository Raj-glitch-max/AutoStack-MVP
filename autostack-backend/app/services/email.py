from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from ..config import settings

logger = logging.getLogger(__name__)


def _log_fallback(subject: str, body: str, recipient: str) -> None:
    logger.info("Email to %s | %s\n%s", recipient, subject, body)


def send_email(subject: str, body: str, recipient: str) -> None:
    if not recipient:
        return

    if settings.smtp_host and settings.email_from:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = settings.email_from
        message["To"] = recipient
        message.set_content(body)

        port = settings.smtp_port or (587 if settings.smtp_use_tls else 25)

        try:
            with smtplib.SMTP(settings.smtp_host, port, timeout=15) as server:
                if settings.smtp_use_tls:
                    server.starttls()
                if settings.smtp_username and settings.smtp_password:
                    server.login(settings.smtp_username, settings.smtp_password)
                server.send_message(message)
                return
        except Exception as exc:  # pragma: no cover - depends on external SMTP
            logger.exception("Failed to send email via SMTP: %s", exc)

    _log_fallback(subject, body, recipient)

