"""
Subscription state-change → branded email dispatcher.

This is the single email side-effect path. It is attached to the existing
`after_subscription_mutation` hook (services/vip_membership.py), which already
runs after every subscription state transition (webhooks, admin tools, and the
periodic lapse sweep). It does NOT touch subscription/state-machine logic.

Guarantees (per spec):
  - NEVER blocks the caller — the actual IO runs in a daemon thread.
  - NEVER raises to the caller — every error is logged internally.
  - Idempotent — a given (user, resulting-state, snapshot) emails at most once,
    enforced by a DB unique key (database.models_email_idempotency).

State → email mapping:
  ACTIVE    → Payment Successful / Access Activated
  PAST_DUE  → Payment Failed / Action Required
  CANCELLED → Subscription Cancelled
  EXPIRED   → Subscription Expired
Other states (INACTIVE, GRACE, PENDING_PAYMENT, SUSPENDED) produce no email.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Optional

from database.crud import claim_email_notification
from database.db import SessionLocal
from database.models_subscription import SubscriptionStatus
from services.email import (
    send_payment_failed,
    send_payment_successful,
    send_subscription_cancelled,
    send_subscription_expired,
)
from services.stripe_events import build_portal_url, resolve_customer_email

logger = logging.getLogger(__name__)

# Resulting states that produce an email. Anything else is ignored.
_NOTIFIABLE = {
    SubscriptionStatus.ACTIVE.value,
    SubscriptionStatus.PAST_DUE.value,
    SubscriptionStatus.CANCELLED.value,
    SubscriptionStatus.EXPIRED.value,
}


def _norm(state: Any) -> Optional[str]:
    """Accept a SubscriptionStatus enum or a raw string; return the str value."""
    if state is None:
        return None
    return getattr(state, "value", state)


def _fmt_date(value: Any) -> Optional[str]:
    if value is None:
        return None
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    return str(value)


def _fingerprint(new_state: str, context: dict) -> str:
    """Snapshot value that distinguishes one logical transition from a repeat.

    Renewals (new end_date) and new failures (new failure event id) get a fresh
    key → a fresh email; redelivery of the same transition reuses the key → skip.
    """
    if new_state == SubscriptionStatus.PAST_DUE.value:
        value = context.get("last_failure_event_id") or _fmt_date(context.get("grace_until"))
    elif new_state == SubscriptionStatus.EXPIRED.value:
        value = _fmt_date(context.get("end_date")) or _fmt_date(context.get("grace_until"))
    else:  # ACTIVE / CANCELLED keyed on the paid-period end
        value = _fmt_date(context.get("end_date"))
    return str(value or "")


def _send_for_state(new_state: str, email: str, portal_url: Optional[str], context: dict) -> bool:
    end_date = _fmt_date(context.get("end_date"))
    if new_state == SubscriptionStatus.ACTIVE.value:
        return send_payment_successful(email, portal_url=portal_url, period_end=end_date)
    if new_state == SubscriptionStatus.PAST_DUE.value:
        return send_payment_failed(email, portal_url=portal_url, reason=context.get("failure_reason"))
    if new_state == SubscriptionStatus.CANCELLED.value:
        return send_subscription_cancelled(email, portal_url=portal_url, access_until=end_date)
    if new_state == SubscriptionStatus.EXPIRED.value:
        return send_subscription_expired(email, portal_url=portal_url, expired_on=end_date)
    return False


def dispatch_state_email(
    user_id: int,
    old_state: Optional[str],
    new_state: str,
    context: Optional[dict] = None,
    *,
    force: bool = False,
) -> bool:
    """Blocking worker: idempotency claim → resolve email → send. Returns whether
    an email was actually sent. Never raises (returns False on any error).

    Runs its own DB session so the idempotency write never touches the caller's
    subscription transaction. Used directly by the test endpoint; production
    callers use `on_subscription_state_changed` (which runs this in a thread).
    """
    context = dict(context or {})
    new_state = _norm(new_state)
    db = SessionLocal()
    try:
        if new_state not in _NOTIFIABLE:
            return False

        customer_id = context.get("customer_id")
        # Resolve recipient: explicit context email (test/override) wins, else
        # via the Stripe Customer id stored on the subscription.
        email = context.get("email") or resolve_customer_email(customer_id)

        key = f"{user_id}:{new_state}:{_fingerprint(new_state, context)}"
        if force:
            # Test bypass: unique suffix so the email always sends, while still
            # being recorded in the idempotency ledger.
            key = f"{key}:force:{context.get('force_token', '')}"

        logger.info(
            "email_state_change_received user_id=%s old=%s new=%s email=%s key=%s",
            user_id, old_state, new_state, email, key,
        )

        if not claim_email_notification(
            db, idempotency_key=key, user_id=user_id, new_state=new_state, email=email
        ):
            logger.info("email_idempotent_skip user_id=%s key=%s", user_id, key)
            return False

        if not email:
            logger.warning("email_skipped_no_email user_id=%s new_state=%s", user_id, new_state)
            return False

        portal_url = build_portal_url(customer_id)
        sent = _send_for_state(new_state, email, portal_url, context)
        logger.info("email_state_change_done user_id=%s new=%s sent=%s", user_id, new_state, sent)
        return bool(sent)
    except Exception as e:  # noqa: BLE001 - must never raise
        logger.exception("email_dispatch_failed user_id=%s new=%s err=%s", user_id, new_state, e)
        return False
    finally:
        db.close()


def on_subscription_state_changed(
    user: Any,
    old_state: Any,
    new_state: Any,
    context: Optional[dict] = None,
) -> None:
    """Public hook. Schedules a branded email for a notable state change.

    Returns immediately (work runs in a daemon thread) and never raises. Safe to
    call from synchronous code deep inside the subscription mutation path.
    """
    try:
        context = dict(context or {})
        new_s = _norm(new_state)
        if new_s not in _NOTIFIABLE:
            return
        user_id = getattr(user, "telegram_id", None) if user is not None else None
        if user_id is None:
            user_id = context.get("user_id")
        if user_id is None:
            logger.warning("email_state_change_no_user new_state=%s", new_s)
            return
        old_s = _norm(old_state)
        threading.Thread(
            target=dispatch_state_email,
            args=(user_id, old_s, new_s, context),
            kwargs={"force": bool(context.get("force_send"))},
            daemon=True,
            name=f"email-notify-{user_id}",
        ).start()
    except Exception as e:  # noqa: BLE001 - scheduling must never raise to caller
        logger.exception("on_subscription_state_changed_failed err=%s", e)
