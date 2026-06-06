"""
VIP Telegram group membership vs paid subscription (ACTIVE or valid GRACE).

Tracks users who may be in the VIP group, starts a removal countdown when entitlement
lapses, removes them after a configurable delay, and restores access on renewal.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from sqlalchemy.orm import Session

from app.config import config
from database.models import User
from services.entitlement_policy import EntitlementPolicy

logger = logging.getLogger(__name__)

_policy = EntitlementPolicy()


def ensure_vip_group_candidate_tracked(db: Session, user: User) -> None:
    """Mark user as subject to VIP/subscription sync (e.g. they posted in the VIP group)."""
    if user.status != "APPROVED":
        return
    if user.vip_invite_sent_at is None:
        user.vip_invite_sent_at = datetime.utcnow()
        db.commit()


def apply_vip_subscription_markers(db: Session, user: User) -> bool:
    """
    After subscription rows change: maintain invalid-since timestamp (not removal).

    Returns True if the user row was modified (caller should commit if not using autoflush).
    """
    if user.status != "APPROVED":
        return False

    entitled = _policy.explain_question_entitlement(user).allows_questions
    changed = False

    if entitled:
        if user.vip_sub_invalid_since is not None:
            user.vip_sub_invalid_since = None
            changed = True
    else:
        if (
            user.vip_invite_sent_at is not None
            and user.vip_billing_removal_at is None
            and user.vip_sub_invalid_since is None
        ):
            user.vip_sub_invalid_since = datetime.utcnow()
            changed = True

    if changed:
        db.add(user)
    return changed


def sync_vip_markers_after_subscription_change(db: Session, user_id: int) -> None:
    """Call after any subscription mutation for this user (webhooks, admin tools, etc.)."""
    user = db.query(User).filter(User.telegram_id == user_id).first()
    if not user:
        return
    if apply_vip_subscription_markers(db, user):
        db.commit()


async def unban_vip_group_member(bot: Bot, telegram_id: int) -> bool:
    """Lift VIP-group ban so invite links work again after renewal."""
    if not config.vip_group_id:
        return False
    try:
        await bot.unban_chat_member(
            chat_id=config.vip_group_id,
            user_id=telegram_id,
            only_if_banned=True,
        )
        logger.info("vip_membership unban telegram_id=%s", telegram_id)
        return True
    except TelegramBadRequest as e:
        logger.warning("vip_membership unban skipped telegram_id=%s err=%s", telegram_id, e)
        return False
    except TelegramForbiddenError:
        logger.warning("vip_membership unban forbidden telegram_id=%s", telegram_id)
        return False
    except Exception as e:
        logger.error("vip_membership unban failed telegram_id=%s err=%s", telegram_id, e)
        return False


async def ban_vip_group_for_billing(bot: Bot, telegram_id: int) -> bool:
    if not config.vip_group_id:
        return False
    try:
        await bot.ban_chat_member(chat_id=config.vip_group_id, user_id=telegram_id)
        logger.info(
            "VIP ACCESS REMOVED telegram_id=%s reason=subscription_lapsed",
            telegram_id,
        )
        return True
    except TelegramBadRequest as e:
        logger.warning("vip_membership ban bad_request telegram_id=%s err=%s", telegram_id, e)
        return False
    except TelegramForbiddenError:
        logger.warning("vip_membership ban forbidden telegram_id=%s", telegram_id)
        return False
    except Exception as e:
        logger.error("vip_membership ban failed telegram_id=%s err=%s", telegram_id, e)
        return False


async def reconcile_vip_group_membership(bot: Bot, db: Session) -> None:
    """
    Periodic job: start/continue lapse timers, remove from group after delay, unban on renewal.

    Also runs the subscription lapse sweep so CANCELLED rows past end_date and
    PAST_DUE rows past grace_until flip to EXPIRED before entitlement runs.
    """
    if not config.vip_group_id:
        return

    # Flip stale CANCELLED / PAST_DUE rows to EXPIRED so entitlement denies
    # cleanly and the VIP ban path engages on the next iteration.
    try:
        from services.subscription_service import SubscriptionService

        SubscriptionService(db).sweep_lapsed_subscriptions()
    except Exception as e:
        logger.error("sweep_lapsed_subscriptions failed: %s", e, exc_info=True)

    now = datetime.utcnow()
    delay = timedelta(seconds=max(1, config.vip_subscription_lapse_removal_delay_seconds))

    users = (
        db.query(User)
        .filter(
            User.status == "APPROVED",
            User.vip_invite_sent_at.isnot(None),
        )
        .all()
    )

    for user in users:
        entitled = _policy.explain_question_entitlement(user).allows_questions

        if entitled:
            changed = False
            if user.vip_sub_invalid_since is not None:
                user.vip_sub_invalid_since = None
                changed = True
            if user.vip_billing_removal_at is not None:
                from services.vip_invite import send_vip_group_invite

                if await unban_vip_group_member(bot, user.telegram_id):
                    user.vip_billing_removal_at = None
                    changed = True
                    if await send_vip_group_invite(bot, user.telegram_id):
                        user.vip_invite_sent_at = datetime.utcnow()
                        changed = True
            if changed:
                db.commit()
            continue

        if user.vip_billing_removal_at is not None:
            continue

        if apply_vip_subscription_markers(db, user):
            db.commit()

        db.refresh(user)
        if user.vip_sub_invalid_since is None:
            continue

        if now < user.vip_sub_invalid_since + delay:
            continue

        if await ban_vip_group_for_billing(bot, user.telegram_id):
            user.vip_billing_removal_at = datetime.utcnow()
            user.vip_sub_invalid_since = None
            db.commit()


def after_subscription_mutation(db: Session, user_id: int) -> None:
    """Public hook: keep VIP lapse markers in sync with subscription rows."""
    sync_vip_markers_after_subscription_change(db, user_id)
