"""
User-information commands surfaced by the client document:

  /menu        — single screen: subscription status, remaining VIP Legal
                 questions this month, membership benefits, links to docs.
  /rules       — community rules (placeholder).
  /privacy     — privacy policy (placeholder).
  /terms       — terms & conditions (placeholder).
  /disclaimer  — disclaimer (placeholder).
  /benefits    — membership benefit tiers (placeholder).

Legal-document copy lives in services/legal_documents.py so onboarding and
re-display use the same source. Benefits / rules text are placeholders the
client will replace with final wording.
"""

from __future__ import annotations

import logging
from datetime import datetime

from aiogram import Router
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.types import Message

from database.crud import get_user
from database.db import SessionLocal
from services.legal_documents import (
    DISCLAIMER_TEXT,
    PRIVACY_TEXT,
    TERMS_TEXT,
    LIABILITY_TEXT,
)

logger = logging.getLogger(__name__)

router = Router()


# Placeholder constants — final text will be supplied by the client.
RULES_TEXT = (
    "📋 <b>Community Rules</b>\n\n"
    "1. No spam.\n"
    "2. No offensive language.\n"
    "3. No unwanted private contact.\n\n"
    "Violation may result in removal from the VIP group.\n\n"
    "[PLACEHOLDER — final wording will be supplied by the client.]"
)

BENEFITS_TEXT = (
    "🎁 <b>Membership Benefits</b>\n\n"
    "• <b>Quick Questions:</b> Unlimited.\n"
    "• <b>VIP Legal Questions:</b> 2 per month.\n"
    "• <b>Before 6 months:</b> 20% discount on private consultation.\n"
    "• <b>After 6 months of active subscription:</b> eligible for a 15-minute lawyer call.\n"
    "• <b>After 2 years of active subscription:</b> 50% discount.\n\n"
    "[PLACEHOLDER — final wording will be supplied by the client.]"
)

RIGHTS_OBLIGATIONS_TEXT = (
    "⚖️ <b>Rights and Obligations</b>\n\n"
    "[PLACEHOLDER — final wording will be supplied by the client.]"
)


def _is_new_month(last, now: datetime) -> bool:
    if last is None:
        return True
    return (last.year, last.month) != (now.year, now.month)


def _build_menu_text(user) -> str:
    status = user.status if user else "UNKNOWN"
    sub = getattr(user, "subscription", None) if user else None
    sub_status = str(sub.status) if sub else "—"
    plan = sub.plan_name if sub else "—"
    end_date = (
        sub.end_date.strftime("%Y-%m-%d") if sub and sub.end_date else "—"
    )

    # Remaining VIP Legal questions this month (matches the monthly reset logic
    # in database.crud._is_new_month — duplicated tiny check to avoid coupling).
    now = datetime.now()
    if user and _is_new_month(user.last_question_date, now):
        remaining = user.question_limit
    else:
        remaining = max(0, (user.question_limit if user else 0) - (user.questions_used if user else 0))
    limit = user.question_limit if user else 0

    return (
        "👤 <b>Your Menu</b>\n\n"
        f"<b>Account status:</b> {status}\n"
        f"<b>Subscription:</b> {sub_status} ({plan})\n"
        f"<b>Period end:</b> {end_date}\n\n"
        f"📊 <b>Remaining VIP Legal questions this month:</b> {remaining}/{limit}\n\n"
        "🎁 <b>Membership benefits:</b> /benefits\n"
        "📋 <b>Community rules:</b> /rules\n"
        "📄 <b>Privacy Policy:</b> /privacy\n"
        "📄 <b>Terms &amp; Conditions:</b> /terms\n"
        "📄 <b>Disclaimer:</b> /disclaimer\n"
        "⚖️ <b>Rights &amp; Obligations:</b> built into /benefits and /rules"
    )


@router.message(Command("menu"))
async def handle_menu(message: Message) -> None:
    if message.chat.type != ChatType.PRIVATE:
        return
    db = SessionLocal()
    try:
        user = get_user(db, message.from_user.id)
        await message.answer(_build_menu_text(user), parse_mode="HTML")
        logger.info("menu shown user_id=%s", message.from_user.id)
    finally:
        db.close()


@router.message(Command("rules"))
async def handle_rules(message: Message) -> None:
    if message.chat.type != ChatType.PRIVATE:
        return
    await message.answer(RULES_TEXT, parse_mode="HTML")


@router.message(Command("benefits"))
async def handle_benefits(message: Message) -> None:
    if message.chat.type != ChatType.PRIVATE:
        return
    await message.answer(BENEFITS_TEXT, parse_mode="HTML")


@router.message(Command("privacy"))
async def handle_privacy(message: Message) -> None:
    if message.chat.type != ChatType.PRIVATE:
        return
    await message.answer(PRIVACY_TEXT, parse_mode="HTML")


@router.message(Command("terms"))
async def handle_terms(message: Message) -> None:
    if message.chat.type != ChatType.PRIVATE:
        return
    await message.answer(TERMS_TEXT, parse_mode="HTML")


@router.message(Command("disclaimer"))
async def handle_disclaimer(message: Message) -> None:
    if message.chat.type != ChatType.PRIVATE:
        return
    await message.answer(DISCLAIMER_TEXT, parse_mode="HTML")


@router.message(Command("liability"))
async def handle_liability(message: Message) -> None:
    """Bonus: also expose the liability text directly so the client has a stable URL for it."""
    if message.chat.type != ChatType.PRIVATE:
        return
    await message.answer(LIABILITY_TEXT, parse_mode="HTML")
