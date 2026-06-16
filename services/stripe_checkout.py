"""
Stripe Checkout Session creation.

Creates the Stripe-side session, persists a local CheckoutSession row in
CREATED state, and returns the URL. The local row is the single source of
truth for webhook idempotency and operator recovery queries.

Reads credentials from `app.config.config` (single source of truth).
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Optional

import stripe
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import config
from database.crud import (
    create_checkout_session_record,
    get_latest_checkout_for_user,
    mark_checkout_expired,
)
from database.models_checkout import CheckoutSession, CheckoutSessionStatus

logger = logging.getLogger(__name__)

# Post-checkout redirect targets come from config (BASE_URL / PAYMENT_*_URL
# env vars), read at call time so a deployment is never tied to a hardcoded host.

# Window during which a CREATED CheckoutSession is reused instead of creating
# a new one. Stripe sessions live ~24h server-side; the 30-minute cap keeps
# users from accumulating multiple parallel Stripe Subscriptions if they tap
# /subscribe repeatedly.
CHECKOUT_REUSE_WINDOW_SECONDS = 30 * 60


class StripeCheckoutConfigError(RuntimeError):
    """Raised when Stripe env vars required to build a Checkout Session are missing."""


def _stripe_session_payability(session_id: str) -> str:
    """Ask Stripe whether a Checkout Session is still payable.

    A local CheckoutSession row in CREATED state reflects only *our* knowledge:
    the session may already be completed (webhook not processed yet), expired,
    or cancelled on Stripe's side. Reusing such a link sends the user to a
    "session timed out" page. This is the authoritative check against Stripe.

    Returns one of:
      - "open"     → still payable; safe to reuse.
      - "complete" → already paid; do NOT reuse and do NOT expire our row
                     (the completion webhook still needs the CREATED row to
                     advance it to COMPLETED).
      - "expired"  → genuinely dead; safe to mark our row EXPIRED.
      - "unknown"  → missing key / retrieve failure / unexpected status; treat
                     as not reusable but leave our row untouched.
    """
    secret_key = config.stripe_secret_key
    if not secret_key:
        return "unknown"
    try:
        stripe.api_key = secret_key
        session = stripe.checkout.Session.retrieve(session_id)
    except Exception as e:  # noqa: BLE001 - any error → not reusable, row untouched
        logger.warning(
            "stripe_session_retrieve_failed session_id=%s err=%s", session_id, e
        )
        return "unknown"

    # status: "open" (payable) | "complete" (paid) | "expired".
    status = getattr(session, "status", None)
    if status == "complete":
        return "complete"
    if status == "expired":
        return "expired"
    if status != "open":
        logger.info(
            "stripe_session_unexpected_status session_id=%s status=%s",
            session_id,
            status,
        )
        return "unknown"

    # Open per status, but honour expires_at (unix seconds, UTC) in case Stripe
    # has not yet flipped the status at the moment of the check.
    expires_at = getattr(session, "expires_at", None)
    if expires_at is not None and expires_at <= time.time():
        logger.info(
            "stripe_session_past_expiry session_id=%s expires_at=%s",
            session_id,
            expires_at,
        )
        return "expired"

    return "open"


def get_reusable_checkout(
    db: Session,
    telegram_id: int,
    *,
    reuse_window_seconds: int = CHECKOUT_REUSE_WINDOW_SECONDS,
) -> Optional[CheckoutSession]:
    """Return a still-payable CREATED CheckoutSession for this user, if one exists.

    A row is only reused when it passes BOTH the local recency window AND a live
    check against Stripe (status "open", not past expiry). If the latest CREATED
    row is past the reuse window, or Stripe reports it is expired, the row is
    marked EXPIRED and None is returned — the caller then creates a brand-new
    Stripe session. A session Stripe reports as "complete" (or that cannot be
    verified) returns None without expiring the row, so the completion webhook
    can still advance it. Returns None when there is nothing to reuse.
    """
    row = get_latest_checkout_for_user(db, telegram_id)
    if row is None:
        return None
    if row.status != CheckoutSessionStatus.CREATED.value:
        return None
    if not row.checkout_url:
        # Legacy row from before the URL column existed; can't hand it back.
        return None
    age = (datetime.utcnow() - row.created_at).total_seconds()
    if age >= reuse_window_seconds:
        mark_checkout_expired(db, stripe_session_id=row.stripe_session_id)
        logger.info(
            "checkout_session_expired_stale telegram_id=%s stripe_session_id=%s age_seconds=%.0f",
            telegram_id,
            row.stripe_session_id,
            age,
        )
        return None

    # Local row looks fresh; confirm it is actually still payable on Stripe
    # before handing the link back (guards against used/expired/cancelled
    # sessions whose completion webhook has not reached us yet).
    payability = _stripe_session_payability(row.stripe_session_id)
    if payability == "open":
        return row

    # Not reusable. Only expire the row when Stripe says it is genuinely dead;
    # for "complete" (and any uncertain "unknown") leave the CREATED row intact
    # so the completion webhook can still advance it to COMPLETED → ACTIVATED.
    if payability == "expired":
        mark_checkout_expired(db, stripe_session_id=row.stripe_session_id)
    logger.info(
        "checkout_session_not_reusable telegram_id=%s stripe_session_id=%s stripe_state=%s",
        telegram_id,
        row.stripe_session_id,
        payability,
    )
    return None


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
        success_url=config.payment_success_url,
        cancel_url=config.payment_cancel_url,
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
            checkout_url=session.url,
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
