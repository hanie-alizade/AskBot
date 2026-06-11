"""
HTTP surface served alongside the Telegram bot.

Three jobs:
1. Health endpoints so Render Free detects an open port.
2. Stripe Checkout return pages (/payment-success, /payment-cancel).
3. Stripe webhook receiver — verifies signature, normalizes the event, hands it
   off to the existing SubscriptionService, then triggers the existing VIP
   invite flow on activation.

No business logic lives here; everything is delegated to:
  - services.subscription_service.SubscriptionService.process_payment_event
  - services.vip_invite.notify_vip_invite_if_eligible
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

import stripe
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse

from app.config import config
from database.crud import (
    append_webhook_processing_log,
    get_checkout_by_stripe_session_id,
    mark_checkout_activated,
    mark_checkout_completed,
)
from database.db import SessionLocal
from database.models_checkout import CheckoutSessionStatus
from database.models_subscription import Subscription
from services.payments.types import NormalizedPaymentEvent
from services.subscription_service import SubscriptionService
from services.vip_invite import notify_vip_invite_if_eligible

logger = logging.getLogger(__name__)

app = FastAPI(title="AskBot HTTP server")

# Stripe event types we act on. Anything else is logged and acknowledged.
_HANDLED_STRIPE_EVENTS = {
    "checkout.session.completed",
    "invoice.paid",
    "invoice.payment_failed",
    "customer.subscription.updated",
    "customer.subscription.deleted",
}


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/")
async def root() -> dict:
    return {"status": "ok"}


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy"}


# ---------------------------------------------------------------------------
# Stripe Checkout return pages
# ---------------------------------------------------------------------------


_SUCCESS_HTML = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Payment successful</title>
<style>
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;max-width:480px;
margin:4rem auto;padding:1.5rem;text-align:center;color:#111}
h1{font-size:1.6rem;margin-bottom:0.5rem}
p{color:#444;font-size:1.05rem}
</style></head>
<body>
<h1>Payment successful.</h1>
<p>You may now return to Telegram.</p>
</body></html>"""

_CANCEL_HTML = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Payment cancelled</title>
<style>
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;max-width:480px;
margin:4rem auto;padding:1.5rem;text-align:center;color:#111}
h1{font-size:1.6rem;margin-bottom:0.5rem}
p{color:#444;font-size:1.05rem}
</style></head>
<body>
<h1>Payment cancelled.</h1>
</body></html>"""


@app.get("/payment-success", response_class=HTMLResponse)
async def payment_success() -> str:
    return _SUCCESS_HTML


@app.get("/payment-cancel", response_class=HTMLResponse)
async def payment_cancel() -> str:
    return _CANCEL_HTML


# ---------------------------------------------------------------------------
# Admin/dev-only: simulate a subscription state change → branded email
# ---------------------------------------------------------------------------


@app.post("/admin/test-email-state")
async def admin_test_email_state(
    state: str,
    user_id: int = 0,
    email: str = "",
    force_send: bool = False,
) -> dict:
    """Manually fire the state-change email path WITHOUT Stripe.

    Disabled unless EMAIL_TEST_ENDPOINT_ENABLED=true (never exposed in prod).

    Query params:
      state      — ACTIVE | PAST_DUE | CANCELLED | EXPIRED (required)
      user_id    — optional: pull customer_id/dates from this user's subscription
      email      — optional: send directly to this address (overrides resolution)
      force_send — optional: bypass idempotency dedup for repeat testing

    Routes through the SAME dispatcher + idempotency layer used in production, so
    repeated calls with the same (user_id, state) are deduped unless force_send.
    """
    if not config.email_test_endpoint_enabled:
        raise HTTPException(status_code=404, detail="Not found")

    state = (state or "").upper()
    valid = {"ACTIVE", "PAST_DUE", "CANCELLED", "EXPIRED"}
    if state not in valid:
        raise HTTPException(status_code=400, detail=f"state must be one of {sorted(valid)}")

    from datetime import timedelta

    from services.email.notification_dispatcher import dispatch_state_email

    context: dict = {"user_id": user_id}
    if email:
        context["email"] = email

    # Pull real customer/date context from the DB when a user_id is supplied.
    if user_id:
        db = SessionLocal()
        try:
            sub = (
                db.query(Subscription)
                .filter(Subscription.user_id == user_id)
                .order_by(Subscription.created_at.desc())
                .first()
            )
            if sub is not None:
                context.setdefault("customer_id", sub.provider_customer_id)
                context["end_date"] = sub.end_date
                context["grace_until"] = sub.grace_until
                context["last_failure_event_id"] = sub.last_failure_event_id
                context["failure_reason"] = sub.last_failure_reason
        finally:
            db.close()

    # Provide a sensible synthetic date when none is available, so the email body
    # has something to show in pure-simulation mode.
    context.setdefault("end_date", datetime.utcnow() + timedelta(days=30))
    if force_send:
        context["force_token"] = str(int(datetime.utcnow().timestamp() * 1000))

    sent = await asyncio.to_thread(
        dispatch_state_email, (user_id or 0), None, state, context, force=force_send
    )
    return {"requested": True, "state": state, "user_id": user_id, "force_send": force_send, "sent": sent}


@app.delete("/admin/email-idempotency")
async def admin_clear_email_idempotency(user_id: int) -> dict:
    """Clear a user's email idempotency rows so notifications can re-send.

    Disabled unless EMAIL_TEST_ENDPOINT_ENABLED=true (never exposed in prod).
    Use during testing to clear keys burned by a prior failed send, so the next
    state change re-delivers instead of being deduped as "already sent".

    Query params:
      user_id — telegram id whose email_notification_log rows to delete (required)
    """
    if not config.email_test_endpoint_enabled:
        raise HTTPException(status_code=404, detail="Not found")
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")

    from database.crud import clear_email_notifications_for_user

    db = SessionLocal()
    try:
        removed = clear_email_notifications_for_user(db, user_id=user_id)
    finally:
        db.close()
    logger.info("admin_clear_email_idempotency user_id=%s removed=%s", user_id, removed)
    return {"cleared": True, "user_id": user_id, "removed": removed}


# ---------------------------------------------------------------------------
# Stripe webhook
# ---------------------------------------------------------------------------


def _resolve_telegram_id_by_subscription(
    db, stripe_subscription_id: Optional[str]
) -> Optional[int]:
    """Find the local Subscription row for a Stripe subscription id, return user_id."""
    if not stripe_subscription_id:
        return None
    row = (
        db.query(Subscription)
        .filter(Subscription.external_subscription_id == stripe_subscription_id)
        .first()
    )
    return row.user_id if row else None


def _normalize_amount(stripe_obj: dict) -> Optional[float]:
    cents = (
        stripe_obj.get("amount_total")
        or stripe_obj.get("amount_paid")
        or stripe_obj.get("amount")
    )
    return (float(cents) / 100.0) if cents is not None else None


def _ts_to_datetime(ts: Optional[int]) -> Optional[datetime]:
    """Stripe sends Unix timestamps; convert to naive UTC for our DB columns.

    The rest of the codebase uses `datetime.utcnow()` (naive UTC), so we strip
    tzinfo after converting to keep comparisons consistent.
    """
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).replace(tzinfo=None)
    except (TypeError, ValueError, OSError):
        return None


def _invoice_period(invoice_obj: dict) -> tuple[Optional[datetime], Optional[datetime]]:
    """Pull the billing period from a Stripe invoice object.

    Invoices put the canonical period on the first line item; some webhook
    payloads also set period_start/period_end on the invoice root. We try both.
    """
    lines = (invoice_obj.get("lines") or {}).get("data") or []
    if lines:
        period = lines[0].get("period") or {}
        ps = _ts_to_datetime(period.get("start"))
        pe = _ts_to_datetime(period.get("end"))
        if ps or pe:
            return ps, pe
    return (
        _ts_to_datetime(invoice_obj.get("period_start")),
        _ts_to_datetime(invoice_obj.get("period_end")),
    )


def _fetch_subscription_period(
    stripe_subscription_id: Optional[str],
) -> tuple[Optional[datetime], Optional[datetime]]:
    """Fetch current_period_start / current_period_end from Stripe by sub ID.

    Returns (None, None) if the call fails or the subscription cannot be read.
    Stripe's Checkout Session event does not include period dates, so we look
    them up here.
    """
    if not stripe_subscription_id or not config.stripe_secret_key:
        return None, None
    try:
        stripe.api_key = config.stripe_secret_key
        sub = stripe.Subscription.retrieve(stripe_subscription_id)
        return (
            _ts_to_datetime(sub.get("current_period_start")),
            _ts_to_datetime(sub.get("current_period_end")),
        )
    except Exception as e:
        logger.warning(
            "stripe_subscription_retrieve_failed subscription_id=%s err=%s",
            stripe_subscription_id,
            e,
        )
        return None, None


def _failure_reason_from_invoice(invoice_obj: dict) -> Optional[str]:
    """Best-effort extraction of why a payment failed."""
    # Invoice-level fields.
    msg = invoice_obj.get("last_finalization_error") or {}
    if isinstance(msg, dict) and msg.get("message"):
        return str(msg["message"])
    # Charge-level failure if present.
    charge = invoice_obj.get("charge")
    if isinstance(charge, dict):
        if charge.get("failure_message"):
            return str(charge["failure_message"])
        if charge.get("failure_code"):
            return str(charge["failure_code"])
    return None


def _build_event(
    *,
    event_id: str,
    internal_event_type: str,
    user_id: int,
    status: str,
    stripe_obj: dict,
    period_start: Optional[datetime] = None,
    period_end: Optional[datetime] = None,
    failure_reason: Optional[str] = None,
) -> NormalizedPaymentEvent:
    return NormalizedPaymentEvent(
        event_id=event_id,
        event_type=internal_event_type,
        user_id=user_id,
        status=status,
        provider="STRIPE",
        amount=_normalize_amount(stripe_obj),
        currency=str(stripe_obj.get("currency") or "usd").upper(),
        external_payment_id=stripe_obj.get("payment_intent"),
        external_subscription_id=stripe_obj.get("subscription") or stripe_obj.get("id"),
        external_customer_id=stripe_obj.get("customer"),
        raw_payload=stripe_obj,
        period_start=period_start,
        period_end=period_end,
        failure_reason=failure_reason,
    )


def _record_webhook_log(
    *,
    user_id: Optional[int],
    event_type: Optional[str],
    success: bool,
    detail: str,
    external_event_id: Optional[str],
) -> None:
    """Persist one admin-visible WebhookProcessingLog row in its OWN session.

    Deliberately decoupled from the business `db` session used by the handler:
    append_webhook_processing_log commits, so sharing the session would commit
    partial subscription state early (or have it rolled back on a later error).
    A separate short-lived session keeps the audit log independent of — and
    resilient to — the outcome of the business transaction.

    This is the missing link that made the admin "Webhook Event Log" stay empty:
    the live /stripe/webhook path never wrote here (only the mock gateway did).
    """
    log_db = SessionLocal()
    try:
        append_webhook_processing_log(
            log_db,
            user_id=user_id,
            event_type=event_type,
            success=success,
            detail=detail,
            external_event_id=external_event_id,
        )
    finally:
        log_db.close()


@app.post("/stripe/webhook")
async def stripe_webhook(request: Request) -> dict:
    """Verify Stripe signature, route to SubscriptionService, trigger VIP invite."""
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")
    webhook_secret = config.stripe_webhook_secret

    if not webhook_secret:
        logger.error(
            "STRIPE WEBHOOK: STRIPE_WEBHOOK_SECRET missing — rejecting all events"
        )
        _record_webhook_log(
            user_id=None,
            event_type=None,
            success=False,
            detail="webhook_secret_missing",
            external_event_id=None,
        )
        raise HTTPException(status_code=503, detail="Webhook not configured")

    try:
        event = stripe.Webhook.construct_event(payload, signature, webhook_secret)
    except stripe.SignatureVerificationError as e:
        logger.warning("STRIPE WEBHOOK: invalid signature: %s", e)
        _record_webhook_log(
            user_id=None,
            event_type=None,
            success=False,
            detail="invalid_signature",
            external_event_id=None,
        )
        raise HTTPException(status_code=400, detail="Invalid signature")
    except ValueError as e:
        logger.warning("STRIPE WEBHOOK: invalid payload: %s", e)
        _record_webhook_log(
            user_id=None,
            event_type=None,
            success=False,
            detail="invalid_payload",
            external_event_id=None,
        )
        raise HTTPException(status_code=400, detail="Invalid payload")

    event_type = event["type"]
    event_id = event.get("id", "")
    logger.info("Webhook received event_id=%s event_type=%s", event_id, event_type)

    if event_type not in _HANDLED_STRIPE_EVENTS:
        logger.info(
            "Webhook ignored unhandled event_type=%s event_id=%s",
            event_type,
            event_id,
        )
        _record_webhook_log(
            user_id=None,
            event_type=event_type,
            success=False,
            detail="unhandled_event_type",
            external_event_id=event_id,
        )
        return {"received": True, "handled": False, "reason": "unhandled_event_type"}

    # NOTE: branded email notifications are NOT dispatched here. They are driven
    # by subscription *state changes* via the after_subscription_mutation hook
    # (services/email/notification_dispatcher.py), giving a single idempotent
    # email path. Webhook behaviour below is unchanged.

    stripe_obj = event["data"]["object"]
    telegram_id: Optional[int] = None
    internal_event_type = event_type
    status = "PENDING"
    stripe_session_id: Optional[str] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    failure_reason: Optional[str] = None

    db = SessionLocal()
    activation_ok = False
    try:
        if event_type == "checkout.session.completed":
            stripe_session_id = stripe_obj.get("id")
            meta = stripe_obj.get("metadata") or {}
            tg_raw = meta.get("telegram_id")
            if tg_raw:
                try:
                    telegram_id = int(tg_raw)
                except ValueError:
                    logger.error(
                        "STRIPE WEBHOOK: metadata.telegram_id non-numeric: %r", tg_raw
                    )

            # Look up the local CheckoutSession row. Three branches:
            #   - row exists, ACTIVATED → duplicate; skip activation entirely
            #   - row exists, otherwise → idempotently mark COMPLETED + capture IDs
            #   - row missing → recovery scenario; activate anyway, the user paid
            checkout_row = (
                get_checkout_by_stripe_session_id(db, stripe_session_id)
                if stripe_session_id
                else None
            )
            if checkout_row is not None:
                if telegram_id is None:
                    telegram_id = checkout_row.telegram_id
                    logger.info(
                        "Webhook resolved telegram_id from CheckoutSession session_id=%s",
                        stripe_session_id,
                    )
                if checkout_row.status == CheckoutSessionStatus.ACTIVATED.value:
                    logger.info(
                        "duplicate_session_detected: checkout already ACTIVATED "
                        "session_id=%s telegram_id=%s event_id=%s",
                        stripe_session_id,
                        telegram_id,
                        event_id,
                    )
                    _record_webhook_log(
                        user_id=telegram_id,
                        event_type=event_type,
                        success=True,
                        detail="duplicate_session_already_activated",
                        external_event_id=event_id,
                    )
                    return {
                        "received": True,
                        "handled": True,
                        "reason": "duplicate_session_already_activated",
                        "telegram_id": telegram_id,
                    }
                mark_checkout_completed(
                    db,
                    stripe_session_id=stripe_session_id,
                    stripe_subscription_id=stripe_obj.get("subscription"),
                    stripe_customer_id=stripe_obj.get("customer"),
                    amount_total_cents=stripe_obj.get("amount_total"),
                    currency=stripe_obj.get("currency"),
                )
                logger.info(
                    "checkout_session_resolved session_id=%s status=%s telegram_id=%s",
                    stripe_session_id,
                    "COMPLETED",
                    telegram_id,
                )
            else:
                logger.warning(
                    "RECOVERY: webhook for unknown checkout session — activating anyway. "
                    "session_id=%s telegram_id=%s event_id=%s",
                    stripe_session_id,
                    telegram_id,
                    event_id,
                )
            # Session object has no period dates — fetch from Stripe Subscription API.
            period_start, period_end = _fetch_subscription_period(
                stripe_obj.get("subscription")
            )
            status = "PAID"

        elif event_type == "invoice.paid":
            billing_reason = stripe_obj.get("billing_reason")
            stripe_sub_id = stripe_obj.get("subscription")
            # First-payment invoice fires alongside checkout.session.completed.
            # Skip it so we don't re-activate or DM a second VIP invite.
            if billing_reason == "subscription_create":
                logger.info(
                    "duplicate_event_skipped: invoice.paid billing_reason=subscription_create "
                    "event_id=%s subscription_id=%s",
                    event_id,
                    stripe_sub_id,
                )
                _record_webhook_log(
                    user_id=_resolve_telegram_id_by_subscription(db, stripe_sub_id),
                    event_type=event_type,
                    success=True,
                    detail="duplicate_first_invoice",
                    external_event_id=event_id,
                )
                return {
                    "received": True,
                    "handled": True,
                    "reason": "duplicate_first_invoice",
                }
            telegram_id = _resolve_telegram_id_by_subscription(db, stripe_sub_id)
            period_start, period_end = _invoice_period(stripe_obj)
            status = "PAID"

        elif event_type == "invoice.payment_failed":
            stripe_sub_id = stripe_obj.get("subscription")
            telegram_id = _resolve_telegram_id_by_subscription(db, stripe_sub_id)
            internal_event_type = "invoice.payment_failed"
            status = "FAILED"
            failure_reason = _failure_reason_from_invoice(stripe_obj)
            # Prefer Stripe's next_payment_attempt as the grace cliff; fall back
            # to None so SubscriptionService applies the configured grace window.
            period_end = _ts_to_datetime(stripe_obj.get("next_payment_attempt"))

        elif event_type == "customer.subscription.updated":
            # Source of truth for current_period_end; we mirror it onto our row.
            stripe_sub_id = stripe_obj.get("id")
            telegram_id = _resolve_telegram_id_by_subscription(db, stripe_sub_id)
            period_start = _ts_to_datetime(stripe_obj.get("current_period_start"))
            period_end = _ts_to_datetime(stripe_obj.get("current_period_end"))
            stripe_status = stripe_obj.get("status")
            # Map Stripe sub status onto our internal event types where useful.
            if stripe_status == "past_due":
                internal_event_type = "invoice.payment_failed"
                status = "FAILED"
            elif stripe_status in {"active", "trialing"}:
                # Keep dates fresh by treating as a renewal-shaped event.
                internal_event_type = "subscription.renewed"
                status = "PAID"
            elif stripe_status in {"canceled", "incomplete_expired", "unpaid"}:
                internal_event_type = "subscription.cancelled"
                status = "CANCELLED"
            else:
                logger.info(
                    "customer.subscription.updated ignored stripe_status=%s "
                    "subscription_id=%s event_id=%s",
                    stripe_status,
                    stripe_sub_id,
                    event_id,
                )
                _record_webhook_log(
                    user_id=telegram_id,
                    event_type=event_type,
                    success=False,
                    detail=f"sub_status_ignored:{stripe_status}",
                    external_event_id=event_id,
                )
                return {
                    "received": True,
                    "handled": False,
                    "reason": f"sub_status_ignored:{stripe_status}",
                }

        elif event_type == "customer.subscription.deleted":
            # Stripe subscription id is the object id itself.
            telegram_id = _resolve_telegram_id_by_subscription(
                db, stripe_obj.get("id")
            )
            # Keep access until current_period_end (user paid for the period).
            period_end = _ts_to_datetime(stripe_obj.get("current_period_end"))
            internal_event_type = "subscription.cancelled"
            status = "CANCELLED"

        logger.info(
            "Webhook resolved telegram_id=%s event_id=%s event_type=%s",
            telegram_id,
            event_id,
            event_type,
        )

        if telegram_id is None:
            logger.error(
                "STRIPE WEBHOOK: could not resolve telegram_id event_id=%s event_type=%s",
                event_id,
                event_type,
            )
            # 200 so Stripe does not retry forever; we already logged the cause.
            _record_webhook_log(
                user_id=None,
                event_type=event_type,
                success=False,
                detail="telegram_id_unresolved",
                external_event_id=event_id,
            )
            return {
                "received": True,
                "handled": False,
                "reason": "telegram_id_unresolved",
            }

        normalized = _build_event(
            event_id=event_id,
            internal_event_type=internal_event_type,
            user_id=telegram_id,
            status=status,
            stripe_obj=stripe_obj,
            period_start=period_start,
            period_end=period_end,
            failure_reason=failure_reason,
        )

        svc = SubscriptionService(db)
        activation_ok = svc.process_payment_event(normalized)
        logger.info(
            "Webhook user activation result event_id=%s telegram_id=%s ok=%s",
            event_id,
            telegram_id,
            activation_ok,
        )

        # On successful activation tied to a tracked checkout, close the loop.
        if activation_ok and stripe_session_id:
            mark_checkout_activated(db, stripe_session_id=stripe_session_id)
            logger.info(
                "checkout_session_activated session_id=%s telegram_id=%s",
                stripe_session_id,
                telegram_id,
            )
    finally:
        db.close()

    invite_result: Optional[str] = None
    if activation_ok and event_type in {
        "checkout.session.completed",
        "invoice.paid",
    }:
        try:
            # Lazy import: app.bot owns the live Bot/Dispatcher singletons that
            # we want to reuse here. Top-level import would couple module load
            # order to no benefit.
            from app.bot import bot

            await notify_vip_invite_if_eligible(bot, telegram_id)
            invite_result = "ok"
            logger.info(
                "Webhook VIP invite triggered telegram_id=%s event_id=%s",
                telegram_id,
                event_id,
            )
        except Exception as e:
            invite_result = f"error:{e.__class__.__name__}"
            logger.exception(
                "Webhook VIP invite failed telegram_id=%s event_id=%s err=%s",
                telegram_id,
                event_id,
                e,
            )

    _record_webhook_log(
        user_id=telegram_id,
        event_type=internal_event_type,
        success=activation_ok,
        detail=(
            f"processed status={status} activation_ok={activation_ok} "
            f"vip_invite={invite_result}"
        ),
        external_event_id=event_id,
    )

    return {
        "received": True,
        "handled": activation_ok,
        "event_type": event_type,
        "telegram_id": telegram_id,
        "vip_invite": invite_result,
    }
