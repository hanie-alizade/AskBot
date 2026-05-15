"""
VIP group invite: only users who pass entitlement (APPROVED + ACTIVE or GRACE) get the link.
"""

import logging
import secrets
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from app.config import config
from database.crud import get_user
from database.db import SessionLocal
from services.entitlement_policy import EntitlementPolicy
from services.i18n import t, t_user
from services.vip_membership import unban_vip_group_member

logger = logging.getLogger(__name__)

_policy = EntitlementPolicy()

# Personal invite link: single-use, 30-day expiry. Generated fresh per send so
# leaked/forwarded links become useless the moment anyone else uses them.
_PERSONAL_LINK_TTL_DAYS = 30

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


async def get_personal_invite_link(bot: Bot, telegram_id: int) -> Optional[str]:
    """
    Create a single-use, ~30-day VIP invite link tied to one Telegram user.

    Returns the URL on success, or None if the bot can't create a link
    (no `VIP_GROUP_ID` configured, missing admin rights, API error). Callers
    should fall back to `config.group_invite_link` only as a last resort.
    """
    if not config.vip_group_id:
        return None
    expire_at = int((datetime.utcnow() + timedelta(days=_PERSONAL_LINK_TTL_DAYS)).timestamp())
    try:
        link = await bot.create_chat_invite_link(
            chat_id=config.vip_group_id,
            name=f"vip_user_{telegram_id}",
            expire_date=expire_at,
            member_limit=1,
        )
        logger.info(
            "personal_invite_link created telegram_id=%s expires_at=%s",
            telegram_id,
            expire_at,
        )
        return link.invite_link
    except TelegramBadRequest as e:
        # Most common cause: bot lacks "Invite Users via Link" admin right.
        logger.error(
            "create_chat_invite_link failed telegram_id=%s err=%s "
            "(does the bot have 'Invite Users via Link' admin right?)",
            telegram_id,
            e,
        )
        return None
    except Exception as e:
        logger.error("create_chat_invite_link unexpected error telegram_id=%s err=%s", telegram_id, e)
        return None


def build_vip_invite_message(lang: Optional[str] = None, link: Optional[str] = None) -> str:
    """Render the localized VIP invite DM. Caller supplies the URL."""
    url = link or config.group_invite_link
    return t(lang, "vip.invite", link=url)


async def send_vip_group_invite(bot: Bot, telegram_id: int) -> bool:
    """Send the private VIP invite link. Returns False if the user blocked the bot.

    Always tries to mint a fresh per-user single-use link; falls back to the
    static env link only if the API call fails.
    """
    db = SessionLocal()
    try:
        user = get_user(db, telegram_id)
        lang = getattr(user, "language", None) if user else None
    finally:
        db.close()

    personal_link = await get_personal_invite_link(bot, telegram_id)
    if not personal_link:
        logger.warning(
            "vip_invite falling back to static GROUP_INVITE_LINK for telegram_id=%s "
            "(personal link generation failed)",
            telegram_id,
        )

    try:
        await bot.send_message(
            chat_id=telegram_id,
            text=build_vip_invite_message(lang, link=personal_link),
        )
        logger.info(
            "vip_invite sent telegram_id=%s lang=%s personal=%s",
            telegram_id,
            lang,
            bool(personal_link),
        )
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
        # Always try to lift any existing VIP-group ban before sending the invite.
        # only_if_banned=True makes this a safe no-op when the user isn't banned.
        if await unban_vip_group_member(bot, telegram_id):
            if user.vip_billing_removal_at is not None:
                user.vip_billing_removal_at = None
                db.commit()
        sent = await send_vip_group_invite(bot, telegram_id)
        if sent:
            user.vip_invite_sent_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()
