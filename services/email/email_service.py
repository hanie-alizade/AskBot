"""Per-event email senders.

One function per Stripe-driven notification. Each builds a branded template and
hands it to the Resend client. They take already-resolved data (recipient email,
optional portal URL, event specifics) — resolving the customer/email from Stripe
is the job of services.stripe_events, keeping this module pure send-logic.

Every function returns True/False (never raises) so callers can log the outcome.
"""

from __future__ import annotations

import logging
from typing import Optional

from app.config import config

from . import templates
from .resend_client import send_email

logger = logging.getLogger(__name__)


def _bot_url() -> str:
    return config.telegram_bot_url


def _brand() -> str:
    return config.brand_name


def send_payment_successful(
    to: Optional[str],
    *,
    portal_url: Optional[str] = None,
    amount: Optional[str] = None,
    period_end: Optional[str] = None,
) -> bool:
    subject, html = templates.render_payment_successful(
        brand=_brand(), bot_url=_bot_url(), portal_url=portal_url,
        amount=amount, period_end=period_end,
    )
    return send_email(to, subject, html)


def send_payment_failed(
    to: Optional[str],
    *,
    portal_url: Optional[str] = None,
    reason: Optional[str] = None,
    next_attempt: Optional[str] = None,
) -> bool:
    subject, html = templates.render_payment_failed(
        brand=_brand(), bot_url=_bot_url(), portal_url=portal_url,
        reason=reason, next_attempt=next_attempt,
    )
    return send_email(to, subject, html)


def send_subscription_cancelled(
    to: Optional[str],
    *,
    portal_url: Optional[str] = None,
    access_until: Optional[str] = None,
) -> bool:
    subject, html = templates.render_subscription_cancelled(
        brand=_brand(), bot_url=_bot_url(), portal_url=portal_url,
        access_until=access_until,
    )
    return send_email(to, subject, html)


def send_subscription_expired(
    to: Optional[str],
    *,
    portal_url: Optional[str] = None,
    expired_on: Optional[str] = None,
) -> bool:
    subject, html = templates.render_subscription_expired(
        brand=_brand(), bot_url=_bot_url(), portal_url=portal_url, expired_on=expired_on,
    )
    return send_email(to, subject, html)


def send_subscription_status_changed(
    to: Optional[str],
    *,
    status: str,
    portal_url: Optional[str] = None,
) -> bool:
    subject, html = templates.render_subscription_status_changed(
        brand=_brand(), bot_url=_bot_url(), portal_url=portal_url, status=status,
    )
    return send_email(to, subject, html)
