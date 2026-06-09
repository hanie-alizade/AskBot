"""Branded transactional email layer (Resend).

Public surface:
  - resend_client.send_email / is_email_configured
  - email_service.send_* per-event senders

Kept independent of Stripe's own receipts. Every entry point is best-effort:
a missing API key, missing recipient, or provider error logs and returns False
— it never raises into the webhook path.
"""

from .email_service import (
    send_payment_failed,
    send_payment_successful,
    send_subscription_cancelled,
    send_subscription_expired,
    send_subscription_status_changed,
)
from .resend_client import is_email_configured, send_email

__all__ = [
    "is_email_configured",
    "send_email",
    "send_payment_successful",
    "send_payment_failed",
    "send_subscription_cancelled",
    "send_subscription_expired",
    "send_subscription_status_changed",
]
