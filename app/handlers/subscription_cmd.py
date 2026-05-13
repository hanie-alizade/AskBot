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
from services.subscription_service import SubscriptionService
from services.subscription_readout import (
    build_subscription_view,
    format_user_subscription_message,
    subscribe_placeholder_message,
)
from services.payments.factory import build_payment_gateway
from services.payments.webhook_service import WebhookService
from services.vip_invite import notify_vip_invite_if_eligible

logger = logging.getLogger(__name__)

router = Router()
policy = EntitlementPolicy()


def _build_view(db, telegram_id: int):
    svc = SubscriptionService(db)
    user = get_user(db, telegram_id)
    snap = svc.get_subscription_snapshot(telegram_id, user=user)
    explanation = policy.explain_question_entitlement(user)
    return build_subscription_view(snap, explanation)


@router.message(Command("subscription"))
@router.message(Command("plan"))
async def handle_subscription_status(message: Message) -> None:
    """Show subscription snapshot and entitlement (read-only)."""
    if message.chat.type != ChatType.PRIVATE:
        return

    user_id = message.from_user.id
    db = SessionLocal()
    try:
        vm = _build_view(db, user_id)
        text = format_user_subscription_message(vm)
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
    db = SessionLocal()
    try:
        user = get_user(db, user_id)
        if not user or user.status != "APPROVED":
            await message.answer(
                "You need an approved account before subscribing.\n"
                "Use /start to continue onboarding."
            )
            return

        if config.mock_payment_enabled:
            gateway = build_payment_gateway()
            webhook = WebhookService(db, gateway)
            ok = webhook.process_mock_event(event_type="payment.succeeded", user_id=user_id)
            if ok:
                await message.answer(
                    "✅ Mock payment applied. Your subscription has been updated.\n"
                    "Use /subscription to see details."
                )
                await notify_vip_invite_if_eligible(message.bot, user_id)
            else:
                await message.answer(
                    "❌ Mock activation failed. Please try again or contact an admin."
                )
            logger.info("subscribe_cmd mock user_id=%s ok=%s", user_id, ok)
            return

        await message.answer(subscribe_placeholder_message())
        logger.info("subscribe_cmd placeholder user_id=%s", user_id)
    finally:
        db.close()
