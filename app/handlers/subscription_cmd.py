"""
User-facing subscription commands (read-only + mock subscribe entry).
"""

import logging

from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.enums import ChatType

from database.crud import get_user
from database.db import SessionLocal
from app.config import config
from services.entitlement_policy import EntitlementPolicy
from services.i18n import t_user
from services.subscription_service import SubscriptionService
from services.subscription_readout import (
    build_subscription_view,
    format_user_subscription_message,
    subscribe_placeholder_message,
)
from services.payments.factory import build_payment_gateway
from services.payments.webhook_service import WebhookService
from services.stripe_checkout import StripeCheckoutConfigError, create_checkout_session
from services.vip_invite import notify_vip_invite_if_eligible

logger = logging.getLogger(__name__)

router = Router()
policy = EntitlementPolicy()


def _build_view(db, telegram_id: int):
    svc = SubscriptionService(db)
    user = get_user(db, telegram_id)
    snap = svc.get_subscription_snapshot(telegram_id, user=user)
    explanation = policy.explain_question_entitlement(user)
    return user, build_subscription_view(snap, explanation)


@router.message(Command("subscription"))
@router.message(Command("plan"))
async def handle_subscription_status(message: Message) -> None:
    """Show subscription snapshot and entitlement (read-only)."""
    if message.chat.type != ChatType.PRIVATE:
        return

    user_id = message.from_user.id
    db = SessionLocal()
    try:
        user, vm = _build_view(db, user_id)
        lang = getattr(user, "language", None)
        text = format_user_subscription_message(vm, lang=lang)
        await message.answer(text)
        logger.info("subscription_cmd user_id=%s mode=%s", user_id, vm.mode_label)
    finally:
        db.close()


@router.message(Command("subscribe"))
@router.message(Command("renew"))
async def handle_subscribe_or_renew(message: Message) -> None:
    """Mock: simulate paid activation. Real: placeholder only."""
    if message.chat.type != ChatType.PRIVATE:
        return

    user_id = message.from_user.id
    logger.info("SUBSCRIBE COMMAND RECEIVED")
    logger.info(f"MOCK_PAYMENT_ENABLED={config.mock_payment_enabled}")
    db = SessionLocal()
    try:
        user = get_user(db, user_id)
        if not user or user.status != "APPROVED":
            await message.answer(t_user(user, "sub.cmd_not_approved"))
            return

        if config.mock_payment_enabled:
            logger.info("ENTERING MOCK PAYMENT FLOW")
            gateway = build_payment_gateway()
            webhook = WebhookService(db, gateway)
            ok = webhook.process_mock_event(event_type="payment.succeeded", user_id=user_id)
            if ok:
                await message.answer(t_user(user, "sub.cmd_mock_success"))
                await notify_vip_invite_if_eligible(message.bot, user_id)
            else:
                await message.answer(t_user(user, "sub.cmd_mock_failed"))
            logger.info("subscribe_cmd mock user_id=%s ok=%s", user_id, ok)
            return

        logger.info("ENTERING STRIPE CHECKOUT FLOW")
        # Real path: create a Stripe Checkout Session and send the URL to the user.
        # Webhook handling / subscription activation are not implemented yet.
        try:
            checkout_url = create_checkout_session(telegram_id=user_id)
        except StripeCheckoutConfigError as e:
            logger.error("subscribe_cmd stripe_config_error user_id=%s err=%s", user_id, e)
            await message.answer(
                "⚠️ Subscription checkout is not configured yet. Please try again later."
            )
            return
        except Exception as e:
            logger.exception("subscribe_cmd stripe_error user_id=%s err=%s", user_id, e)
            await message.answer(
                "⚠️ We couldn't start the checkout right now. Please try again in a moment."
            )
            return

        await message.answer(
            "💳 Tap the link below to start your subscription:\n\n"
            f"{checkout_url}"
        )
        logger.info("subscribe_cmd stripe user_id=%s", user_id)
    finally:
        db.close()
