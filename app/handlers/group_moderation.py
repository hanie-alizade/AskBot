"""
Group moderation for VIP group: delete user posts, optional forward-to-admin via private UI.
"""

import logging
from typing import Optional

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from database.crud import get_user
from database.db import SessionLocal
from ..config import config
from services.entitlement_policy import EntitlementPolicy
from services.vip_invite import (
    store_pending_group_question,
    discard_pending_group_question,
    take_pending_group_question,
)

logger = logging.getLogger(__name__)

router = Router()
_bot_instance: Optional[Bot] = None
_policy = EntitlementPolicy()


def setup_bot_instance(bot: Bot) -> None:
    global _bot_instance
    _bot_instance = bot


async def delete_user_message(message: Message) -> None:
    """Delete user message from the group."""
    try:
        await message.delete()
        logger.info(f"Deleted message {message.message_id} from user {message.from_user.id}")
    except TelegramBadRequest as e:
        if "message to delete not found" in str(e):
            logger.warning(f"Message {message.message_id} already deleted or not found")
        else:
            logger.error(f"Failed to delete message {message.message_id}: {e}")
    except TelegramForbiddenError as e:
        logger.error(f"Bot doesn't have permission to delete messages: {e}")
    except Exception as e:
        logger.error(f"Unexpected error deleting message: {e}")


async def send_private_subscription_required(user_id: int) -> None:
    if not _bot_instance:
        return
    try:
        await _bot_instance.send_message(
            chat_id=user_id,
            text=(
                "Your message in the VIP group was removed (announcements only).\n\n"
                "You need an active subscription to forward questions from the group. "
                "Use /subscription to check status, then /subscribe or /renew when eligible."
            ),
        )
    except TelegramForbiddenError:
        logger.warning("Cannot DM user %s (blocked or no chat)", user_id)
    except Exception as e:
        logger.error("send_private_subscription_required failed: %s", e)


async def send_private_redirect_unapproved(user_id: int) -> None:
    """Notify non-approved users after their group message was removed."""
    if not _bot_instance:
        return
    try:
        await _bot_instance.send_message(
            chat_id=user_id,
            text=(
                "Your message in the VIP group was removed to keep the channel clean.\n\n"
                "Please use private chat with this bot to continue onboarding or ask questions "
                "once you are approved and subscribed."
            ),
        )
    except TelegramForbiddenError:
        logger.warning("Cannot DM user %s", user_id)
    except Exception as e:
        logger.error("send_private_redirect_unapproved failed: %s", e)


async def send_group_forward_offer(user_id: int, question_text: str) -> None:
    """Ask whether to send the removed group line to the admin (private)."""
    if not _bot_instance:
        return
    token = store_pending_group_question(user_id, question_text)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Yes", callback_data=f"grpq:y:{token}"),
                InlineKeyboardButton(text="No", callback_data=f"grpq:n:{token}"),
            ]
        ]
    )
    preview = question_text.strip()
    if len(preview) > 400:
        preview = preview[:397] + "..."
    try:
        await _bot_instance.send_message(
            chat_id=user_id,
            text=(
                "Your message in the VIP group was removed (announcements only).\n\n"
                "Would you like to send this question to the admin instead?\n\n"
                f"—\n{preview}"
            ),
            reply_markup=keyboard,
        )
    except TelegramForbiddenError:
        logger.warning("Cannot DM user %s for group forward offer", user_id)
    except Exception as e:
        logger.error("send_group_forward_offer failed: %s", e)


async def send_non_text_group_notice(user_id: int) -> None:
    if not _bot_instance:
        return
    try:
        await _bot_instance.send_message(
            chat_id=user_id,
            text=(
                "Your post in the VIP group was removed. Only text can be forwarded as a question.\n\n"
                "Send your question in private chat with this bot if you need help."
            ),
        )
    except Exception:
        pass


async def _handle_vip_group_user_message(message: Message, *, has_text: bool) -> None:
    if message.chat.id != config.vip_group_id:
        return
    if not message.from_user or message.from_user.id == config.admin_id:
        return

    db = SessionLocal()
    try:
        user = get_user(db, message.from_user.id)
        uid = message.from_user.id

        if not user or user.status != "APPROVED":
            await delete_user_message(message)
            await send_private_redirect_unapproved(uid)
            logger.info("VIP group message removed (not approved) user=%s", uid)
            return

        entitled = _policy.explain_question_entitlement(user).allows_questions

        if not has_text:
            await delete_user_message(message)
            if entitled:
                await send_non_text_group_notice(uid)
            else:
                await send_private_subscription_required(uid)
            return

        text = (message.text or "").strip()
        await delete_user_message(message)

        if not entitled:
            await send_private_subscription_required(uid)
            return

        await send_group_forward_offer(uid, text)
        logger.info("VIP group text removed; forward offer sent user=%s", uid)

    except Exception as e:
        logger.error("Error handling VIP group message: %s", e)
    finally:
        db.close()


@router.message(F.chat.type == ChatType.GROUP, F.text)
async def handle_group_message(message: Message) -> None:
    await _handle_vip_group_user_message(message, has_text=True)


@router.message(F.chat.type == ChatType.SUPERGROUP, F.text)
async def handle_supergroup_message(message: Message) -> None:
    await _handle_vip_group_user_message(message, has_text=True)


@router.message(F.chat.type == ChatType.GROUP)
async def handle_group_content(message: Message) -> None:
    if message.chat.id != config.vip_group_id:
        return
    if not message.from_user or message.from_user.id == config.admin_id:
        return
    if message.text:
        return
    await _handle_vip_group_user_message(message, has_text=False)


@router.message(F.chat.type == ChatType.SUPERGROUP)
async def handle_supergroup_content(message: Message) -> None:
    if message.chat.id != config.vip_group_id:
        return
    if not message.from_user or message.from_user.id == config.admin_id:
        return
    if message.text:
        return
    await _handle_vip_group_user_message(message, has_text=False)


@router.callback_query(F.data.startswith("grpq:"))
async def handle_group_question_callback(callback: CallbackQuery) -> None:
    """Yes/No after VIP group message was removed."""
    if not callback.data or not callback.from_user:
        await callback.answer()
        return

    parts = callback.data.split(":", 2)
    if len(parts) != 3 or parts[0] != "grpq":
        await callback.answer()
        return

    action, token = parts[1], parts[2]
    uid = callback.from_user.id

    if action == "n":
        discard_pending_group_question(token, uid)
        await callback.answer("Cancelled")
        if callback.message:
            try:
                await callback.message.edit_reply_markup(reply_markup=None)
            except TelegramBadRequest:
                pass
        return

    if action != "y":
        await callback.answer()
        return

    text = take_pending_group_question(token, uid)
    await callback.answer()
    if callback.message:
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except TelegramBadRequest:
            pass

    if not text:
        if _bot_instance and callback.message:
            await _bot_instance.send_message(
                chat_id=uid,
                text="That offer expired. Please send your question again from the group or in private chat.",
            )
        return

    from app.handlers.questions import process_private_question_submission

    if not callback.message:
        return
    await process_private_question_submission(callback.message, uid, text)
