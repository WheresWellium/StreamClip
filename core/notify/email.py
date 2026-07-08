"""
StreamClip — Thin SMTP email notifier

Configured entirely through environment variables so no secrets live in
config.yaml:

  SMTP_HOST      — mail server hostname (unset = email disabled, no-op)
  SMTP_PORT      — default 587
  SMTP_USER      — optional auth username
  SMTP_PASSWORD  — optional auth password
  SMTP_FROM      — sender address (default: streamclip@localhost)
  SMTP_STARTTLS  — "false" to disable STARTTLS (default on)
  BUG_REPORT_TO  — recipient for bug report notifications

Mirrors the webhook delivery pattern: bounded retries, never raises to the
caller. Always send from a Celery `default`-queue task — never inline in an
API handler and never on the GPU queue.
"""

from __future__ import annotations

import os
import smtplib
import time
from dataclasses import dataclass
from email.message import EmailMessage

import structlog

log = structlog.get_logger(__name__)


@dataclass(frozen=True)
class SMTPSettings:
    host: str
    port: int
    user: str
    password: str
    sender: str
    starttls: bool

    @property
    def configured(self) -> bool:
        return bool(self.host)


def smtp_settings_from_env() -> SMTPSettings:
    return SMTPSettings(
        host=os.environ.get("SMTP_HOST", "").strip(),
        port=int(os.environ.get("SMTP_PORT", "587")),
        user=os.environ.get("SMTP_USER", ""),
        password=os.environ.get("SMTP_PASSWORD", ""),
        sender=os.environ.get("SMTP_FROM", "streamclip@localhost"),
        starttls=os.environ.get("SMTP_STARTTLS", "true").lower() != "false",
    )


def bug_report_recipient() -> str:
    return os.environ.get("BUG_REPORT_TO", "").strip()


def bug_report_email_status() -> str:
    """Whether a submitted bug report will trigger operator email notification."""
    smtp = smtp_settings_from_env()
    if not smtp.configured:
        return "skipped_unconfigured"
    if not bug_report_recipient():
        return "skipped_no_recipient"
    return "queued"


def send_email(
    *,
    to: str,
    subject: str,
    body: str,
    settings: SMTPSettings | None = None,
    max_retries: int = 3,
) -> bool:
    """Send a plain-text email. Returns True on success, False otherwise."""
    smtp = settings or smtp_settings_from_env()
    if not smtp.configured:
        log.info("email_skipped_unconfigured", subject=subject)
        return False
    if not to:
        log.warning("email_skipped_no_recipient", subject=subject)
        return False

    msg = EmailMessage()
    msg["From"] = smtp.sender
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    for attempt in range(max_retries):
        try:
            with smtplib.SMTP(smtp.host, smtp.port, timeout=15) as client:
                if smtp.starttls:
                    client.starttls()
                if smtp.user:
                    client.login(smtp.user, smtp.password)
                client.send_message(msg)
            log.info("email_sent", to=to, subject=subject)
            return True
        except (smtplib.SMTPException, OSError) as exc:
            log.warning(
                "email_send_failed",
                attempt=attempt + 1,
                error=str(exc),
                subject=subject,
            )
            time.sleep(1.5 ** attempt)
    return False
