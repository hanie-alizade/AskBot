"""
Stripe Checkout Session creation.

Reads credentials from environment at call time so the module imports cleanly
even when Stripe is not configured (e.g. mock-payment mode).

Intentionally minimal: it returns the Checkout URL. Webhook handling and
subscription activation live elsewhere (not implemented in this step).
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import stripe

logger = logging.getLogger(__name__)

SUCCESS_URL = "https://askbot-uu5o.onrender.com/payment-success"
CANCEL_URL = "https://askbot-uu5o.onrender.com/payment-cancel"


class StripeCheckoutConfigError(RuntimeError):
    """Raised when Stripe env vars required to build a Checkout Session are missing."""


def create_checkout_session(telegram_id: int) -> str:
    """Create a Stripe Checkout Session for a Telegram user and return its URL.

    Raises StripeCheckoutConfigError if STRIPE_SECRET_KEY or STRIPE_PRICE_ID are
    not set. Stripe SDK errors propagate as stripe.error.StripeError.
    """
    secret_key = os.getenv("STRIPE_SECRET_KEY")
    price_id = os.getenv("STRIPE_PRICE_ID")

    missing = [
        name
        for name, value in (("STRIPE_SECRET_KEY", secret_key), ("STRIPE_PRICE_ID", price_id))
        if not value
    ]
    if missing:
        raise StripeCheckoutConfigError(
            f"Missing required Stripe env vars: {', '.join(missing)}"
        )

    stripe.api_key = secret_key

    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=SUCCESS_URL,
        cancel_url=CANCEL_URL,
        metadata={"telegram_id": str(telegram_id)},
    )

    logger.info(
        "stripe_checkout_session_created telegram_id=%s session_id=%s",
        telegram_id,
        session.id,
    )

    url: Optional[str] = session.url
    if not url:
        raise RuntimeError("Stripe returned a Checkout Session without a URL")
    return url
