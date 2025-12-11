"""SMTP email backend."""

from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import Iterable

from parlaylab.config import get_settings


class EmailBackend:
    """Simple SMTP email sender."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def send(self, subject: str, body: str, recipients: Iterable[str]) -> None:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.settings.email_from
        msg["To"] = ", ".join(recipients)
        msg.set_content(body)

        with smtplib.SMTP(self.settings.email_host, self.settings.email_port) as smtp:
            smtp.starttls()
            if self.settings.email_user and self.settings.email_password:
                smtp.login(self.settings.email_user, self.settings.email_password)
            smtp.send_message(msg)
