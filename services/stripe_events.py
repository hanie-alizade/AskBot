"""Stripe resolution helpers (no side-effects, no email logic).

Small reusable lookups shared by the email notification layer:
  - resolve_subscription_status : normalize a Stripe subscription status string
  - resolve_customer_email      : Stripe Customer id -> email
  - build_portal_url            : best-effort Customer Portal link ("Manage Subscription")

Intentionally free of business logic. The email side-effect itself lives in
services/email/notification_dispatcher.py, which is driven by subscription state
changes (via the after_subscription_mutation hook) — NOT by raw Stripe events —
so there is a single, idempotent email path.
"""

from __future__ import annotations

import logging
from typing import Optional

import stripe

from app.config import config
from services.stripe_portal import create_customer_portal_session

logger = logging.getLogger(__name__)


def resolve_subscription_status(stripe_subscription_obj: Optional[dict]) -> str:
    """Normalize a Stripe subscription object's status to a lowercase string.

    Returns "unknown" when the object or its status is absent, so callers can
    branch safely without guarding for None.
    """
    if not stripe_subscription_obj:
        return "unknown"
    return str(stripe_subscription_obj.get("status") or "unknown").lower()


def resolve_customer_email(customer_id: Optional[str]) -> Optional[str]:
    """Resolve a recipient email from a Stripe Customer id (stored in the DB as
    Subscription.provider_customer_id). Returns None on any failure."""
    if not customer_id or not config.stripe_secret_key:
        return None
    try:
        stripe.api_key = config.stripe_secret_key
        customer = stripe.Customer.retrieve(customer_id)
        email = customer.get("email") if isinstance(customer, dict) else getattr(customer, "email", None)
        return str(email) if email else None
    except Exception as e:  # noqa: BLE001
        logger.warning("email_customer_retrieve_failed customer_id=%s err=%s", customer_id, e)
        return None


def build_portal_url(customer_id: Optional[str]) -> Optional[str]:
    """Best-effort Stripe Customer Portal link for the 'Manage Subscription' CTA.

    Portal session URLs are short-lived; included only "if available" and any
    failure simply drops the button.
    """
    if not customer_id:
        return None
    try:
        return create_customer_portal_session(
            customer_id, return_url=config.stripe_portal_return_url
        )
    except Exception as e:  # noqa: BLE001
        logger.info("email_portal_link_unavailable customer_id=%s err=%s", customer_id, e)
        return None
