"""
Stripe Checkout Session creation.

Reads credentials from config (single source of truth) so the env-var names
match what `app/config.py` reads and nothing is duplicated.

Intentionally minimal: it returns the Checkout URL. Webhook handling and
subscription activation live elsewhere (not implemented in this step).
"""

from __future__ import annotations

import logging
from typing import Optional

import stripe

from app.config import config

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
    secret_key = config.stripe_api_key  # env: STRIPE_SECRET_KEY
    price_id = config.stripe_price_id   # env: STRIPE_PRICE_ID

    logger.info("STRIPE_SECRET_KEY present = %s", bool(secret_key))
    logger.info("STRIPE_PRICE_ID present = %s", bool(price_id))

    if not secret_key:
        logger.error("Stripe config error: STRIPE_SECRET_KEY missing")
        raise StripeCheckoutConfigError("STRIPE_SECRET_KEY missing")
    if not price_id:
        logger.error("Stripe config error: STRIPE_PRICE_ID missing")
        raise StripeCheckoutConfigError("STRIPE_PRICE_ID missing")

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
