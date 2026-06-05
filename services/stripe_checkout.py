"""
Stripe Checkout Session creation.

Creates the Stripe-side session, persists a local CheckoutSession row in
CREATED state, and returns the URL. The local row is the single source of
truth for webhook idempotency and operator recovery queries.

Reads credentials from `app.config.config` (single source of truth).
"""

from __future__ import annotations

import logging
from typing import Optional

import stripe
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import config
from database.crud import create_checkout_session_record

logger = logging.getLogger(__name__)

SUCCESS_URL = "https://askbot-uu5o.onrender.com/payment-success"
CANCEL_URL = "https://askbot-uu5o.onrender.com/payment-cancel"


class StripeCheckoutConfigError(RuntimeError):
    """Raised when Stripe env vars required to build a Checkout Session are missing."""


def create_checkout_session(telegram_id: int, db: Session) -> str:
    """Create a Stripe Checkout Session, persist it locally, return the URL.

    Raises StripeCheckoutConfigError if STRIPE_SECRET_KEY or STRIPE_PRICE_ID are
    not set. Stripe SDK errors propagate as stripe.error.StripeError.

    The caller supplies a DB session so the CheckoutSession row is written in
    the same transactional context as the rest of the /subscribe handler.
    """
    logger.warning("stripe checkout called telegram_id=%s", telegram_id)

    secret_key = config.stripe_secret_key  # env: STRIPE_SECRET_KEY
    price_id = config.stripe_price_id      # env: STRIPE_PRICE_ID

    # Diagnostics BEFORE any validation, so the log always shows actual state.
    logger.info("STRIPE_SECRET_KEY exists = %s", bool(secret_key))
    logger.info("STRIPE_PRICE_ID exists = %s", bool(price_id))

    if not secret_key:
        logger.error("STRIPE CONFIG ERROR: STRIPE_SECRET_KEY missing")
        raise StripeCheckoutConfigError("STRIPE_SECRET_KEY missing")
    if not price_id:
        logger.error("STRIPE CONFIG ERROR: STRIPE_PRICE_ID missing")
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

    # Persist BEFORE returning so a slow/lost DM doesn't cost us the linkage.
    try:
        create_checkout_session_record(
            db,
            telegram_id=telegram_id,
            stripe_session_id=session.id,
        )
        logger.info(
            "checkout_session_stored telegram_id=%s session_id=%s",
            telegram_id,
            session.id,
        )
    except IntegrityError:
        # Shouldn't happen — Stripe Checkout Session IDs are globally unique.
        # Log and continue; the row already exists, so recovery still works.
        db.rollback()
        logger.warning(
            "checkout_session_store_duplicate telegram_id=%s session_id=%s",
            telegram_id,
            session.id,
        )
    except Exception as e:
        # Persistence failure is non-fatal for the user — they can still pay.
        # But operator visibility drops to zero for this session, so shout.
        db.rollback()
        logger.exception(
            "checkout_session_store_failed telegram_id=%s session_id=%s err=%s",
            telegram_id,
            session.id,
            e,
        )

    url: Optional[str] = session.url
    if not url:
        raise RuntimeError("Stripe returned a Checkout Session without a URL")
    return url
