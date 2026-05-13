"""
VIP group invite: only users who pass entitlement (APPROVED + ACTIVE or GRACE) get the link.
"""

import logging
import secrets
import time
from typing import Dict, Optional, Tuple

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError

from app.config import config
from database.crud import get_user
from database.db import SessionLocal
from services.entitlement_policy import EntitlementPolicy

logger = logging.getLogger(__name__)

_policy = EntitlementPolicy()

# token -> (telegram_user_id, question_text, monotonic_created)
_PENDING_GROUP_QUESTIONS: Dict[str, Tuple[int, str, float]] = {}
_PENDING_TTL_SEC = 600


def _prune_pending() -> None:
    now = time.monotonic()
    dead = [k for k, (_, _, t) in _PENDING_GROUP_QUESTIONS.items() if now - t > _PENDING_TTL_SEC]
    for k in dead:
        del _PENDING_GROUP_QUESTIONS[k]


def store_pending_group_question(user_id: int, text: str) -> str:
    """Store text for a short-lived VIP group → private forward; returns callback token."""
    _prune_pending()
    token = secrets.token_hex(8)
    _PENDING_GROUP_QUESTIONS[token] = (user_id, text, time.monotonic())
    return token


def discard_pending_group_question(token: str, user_id: int) -> None:
    """Remove pending entry when user taps No (only if it belongs to them)."""
    _prune_pending()
    entry = _PENDING_GROUP_QUESTIONS.get(token)
    if entry and entry[0] == user_id:
        del _PENDING_GROUP_QUESTIONS[token]


def take_pending_group_question(token: str, user_id: int) -> Optional[str]:
    """Atomically take question text if token exists and belongs to user_id."""
    _prune_pending()
    entry = _PENDING_GROUP_QUESTIONS.get(token)
    if not entry:
        return None
    stored_uid, text, _ = entry
    if stored_uid != user_id:
        return None
    del _PENDING_GROUP_QUESTIONS[token]
    return text


def build_vip_invite_message() -> str:
    return (
        "🎉 Your subscription is active.\n\n"
        "You can join the VIP group using this invite link:\n\n"
        f"{config.group_invite_link}\n\n"
        "Welcome to the community."
    )


async def send_vip_group_invite(bot: Bot, telegram_id: int) -> bool:
    """Send the private VIP invite link. Returns False if the user blocked the bot."""
    try:
        await bot.send_message(chat_id=telegram_id, text=build_vip_invite_message())
        logger.info("vip_invite sent telegram_id=%s", telegram_id)
        return True
    except TelegramForbiddenError:
        logger.warning("vip_invite blocked or chat closed telegram_id=%s", telegram_id)
        return False
    except Exception as e:
        logger.error("vip_invite failed telegram_id=%s err=%s", telegram_id, e)
        return False


async def notify_vip_invite_if_eligible(bot: Bot, telegram_id: int) -> None:
    """After subscription becomes valid, send the VIP invite once conditions are met."""
    db = SessionLocal()
    try:
        user = get_user(db, telegram_id)
        if not user or user.status != "APPROVED":
            return
        if not _policy.explain_question_entitlement(user).allows_questions:
            return
        await send_vip_group_invite(bot, telegram_id)
    finally:
        db.close()
