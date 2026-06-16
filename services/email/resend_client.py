"""Thin Resend send wrapper.

The only place that talks to the Resend SDK. Designed so the rest of the app
never has to think about whether email is configured or installed:

  - `resend` is imported lazily; if the package is absent the layer disables
    itself (logs + skips) instead of crashing the process at import time.
  - send_email never raises — it returns True/False and logs the outcome.
"""

from __future__ import annotations

import logging
from typing import Optional

from app.config import config

logger = logging.getLogger(__name__)

try:  # Optional dependency — app must boot even before `pip install resend`.
    import resend  # type: ignore
except ImportError:  # pragma: no cover - exercised only when dep missing
    resend = None  # type: ignore


def is_email_configured() -> bool:
    """True only when notifications are on, a key is set, and the SDK is present."""
    return bool(
        config.email_notifications_enabled
        and config.resend_api_key
        and resend is not None
    )


def send_email(to: Optional[str], subject: str, html: str) -> bool:
    """Send one HTML email via Resend. Returns True on success, never raises.

    Skips (returns False) when email is not configured or the recipient is
    missing, logging the reason so the skip is visible in webhook traces.
    """
    if not is_email_configured():
        logger.warning(
            "email_skipped_not_configured subject=%r reason=%s",
            subject,
            "notifications_off_or_missing_key_or_sdk",
        )
        return False
    if not to:
        logger.warning("email_skipped_no_recipient subject=%r", subject)
        return False

    try:
        resend.api_key = config.resend_api_key
        response = resend.Emails.send(
            {
                # Sender address, configurable via the EMAIL_FROM env var.
                # Defaults to Resend's shared testing sender
                # ("...<onboarding@resend.dev>"), which works without domain
                # verification. Point EMAIL_FROM at a verified domain to send
                # from your own address.
                "from": config.email_from,
                "to": [to],
                "subject": subject,
                "html": html,
            }
        )
        message_id = response.get("id") if isinstance(response, dict) else getattr(response, "id", None)
        logger.info("email_sent to=%s subject=%r resend_id=%s", to, subject, message_id)
        return True
    except Exception as e:  # noqa: BLE001 - email must never break the caller
        logger.exception("email_send_failed to=%s subject=%r err=%s", to, subject, e)
        return False
