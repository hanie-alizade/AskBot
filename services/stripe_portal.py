"""
Stripe Customer Portal session creation.

Generates a one-shot URL the user can open to update their card, change
billing details, or cancel the subscription. The portal itself is hosted by
Stripe; we only mint the session and hand the URL back.

Reuses Stripe credentials from `app.config.config` (single source of truth).
"""

from __future__ import annotations

import logging

import stripe

from app.config import config

logger = logging.getLogger(__name__)


class StripePortalConfigError(RuntimeError):
    """Raised when the Stripe secret key required for portal sessions is missing."""


def create_customer_portal_session(
    stripe_customer_id: str,
    *,
    return_url: str,
) -> str:
    """Create a Stripe Billing Portal session and return its URL.

    Raises StripePortalConfigError when STRIPE_SECRET_KEY is unset. Stripe SDK
    errors propagate as stripe.error.StripeError — the caller decides how to
    surface them to the user.
    """
    if not config.stripe_secret_key:
        logger.error("STRIPE PORTAL ERROR: STRIPE_SECRET_KEY missing")
        raise StripePortalConfigError("STRIPE_SECRET_KEY missing")

    stripe.api_key = config.stripe_secret_key

    session = stripe.billing_portal.Session.create(
        customer=stripe_customer_id,
        return_url=return_url,
    )

    url = session.url
    if not url:
        raise RuntimeError("Stripe returned a Billing Portal Session without a URL")
    return url
