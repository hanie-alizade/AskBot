"""
Access request handlers for the user flow.
Handles access requests and user state transitions.
"""

import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.enums import ChatType
from aiogram.filters import Command
from sqlalchemy.orm import Session

from database.crud import create_user, get_user, update_user_status, get_user_count_by_status
from database.db import SessionLocal
from ..config import config
from services.entitlement_policy import EntitlementPolicy
from services.i18n import t_user

logger = logging.getLogger(__name__)

router = Router()

# Global bot instance for sending messages
_bot_instance = None
policy = EntitlementPolicy()

def setup_bot_instance(bot: Bot) -> None:
    """Setup bot instance for sending messages."""
    global _bot_instance
    _bot_instance = bot


@router.callback_query(F.data == "request_access")
async def handle_request_access_callback(callback: CallbackQuery) -> None:
    """Handle access request button click."""
    user_id = callback.from_user.id

    db = SessionLocal()
    try:
        user = get_user(db, user_id)
        if not user or user.status != "VERIFIED":
            await callback.answer(
                t_user(user, "access.alert_cannot_request"),
                show_alert=True,
            )
            return

        # Legal-acceptance gate (defense-in-depth — the /start flow already
        # blocks NEW→VERIFIED until all four are accepted, but bumped versions
        # invalidate prior acceptance).
        from services.legal_documents import has_accepted_all

        if not has_accepted_all(user):
            await callback.answer(
                t_user(user, "legal.gate_message_alert"),
                show_alert=True,
            )
            resume_kb = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=t_user(user, "btn.resume_legal"),
                        callback_data="legal_resume",
                    )
                ],
            ])
            await callback.message.answer(
                t_user(user, "legal.gate_message"),
                reply_markup=resume_kb,
            )
            return

        # Check if user already has a pending request
        if user.status == "PENDING_APPROVAL":
            await callback.answer(
                t_user(user, "access.alert_already_pending"),
                show_alert=True,
            )
            return

        # Set user state to pending approval
        update_user_status(db, user_id, "PENDING_APPROVAL")

        # Notify admin (admin-facing — kept English internally)
        await notify_admin_about_request(user_id, callback.from_user.full_name)

        # Update user message
        await callback.message.edit_text(t_user(user, "access.submitted"))

        await callback.answer(t_user(user, "access.alert_submitted"))
        logger.info(f"User {user_id} ({callback.from_user.full_name}) requested access")
    finally:
        db.close()


async def notify_admin_about_request(user_id: int, user_name: str) -> None:
    """Send notification to admin about new access request with inline buttons. Admin text stays in English."""
    try:
        admin_text = (
            f"🔔 New Access Request\n\n"
            f"👤 User: {user_name}\n"
            f"🆔 ID: {user_id}\n"
            f"📅 Time: Request received\n\n"
            f"Quick actions below:"
        )

        # Create inline keyboard for approve/reject actions
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Approve",
                    callback_data=f"approve:{user_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Reject",
                    callback_data=f"reject:{user_id}"
                )
            ]
        ])

        if _bot_instance:
            await _bot_instance.send_message(
                config.admin_id,
                admin_text,
                reply_markup=keyboard
            )
            logger.info(f"Admin notification sent for user {user_id} with inline buttons")
        else:
            logger.warning(f"Bot instance not available. Admin notification for user {user_id}: {admin_text}")

    except Exception as e:
        logger.error(f"Failed to notify admin about access request from user {user_id}: {e}")


_STATUS_KEY = {
    "NEW": "status.new",
    "VERIFIED": "status.verified",
    "PENDING_APPROVAL": "status.pending",
    "APPROVED": "status.approved",
    "REJECTED": "status.rejected",
}


@router.message(Command("status"))
async def handle_status_command(message: Message) -> None:
    """Handle /status command to show current user status."""
    user_id = message.from_user.id

    logger.info(f"📊 STATUS command triggered by user {user_id}")

    db = SessionLocal()
    try:
        user = get_user(db, user_id)
        if not user:
            await message.answer(t_user(None, "status.not_registered_dm"))
            logger.info(f"User {user_id} checked status but not found in database")
            return

        status_key = _STATUS_KEY.get(user.status, "status.unknown")
        status_text = t_user(user, status_key)

        if user.status == "APPROVED":
            expl = policy.explain_question_entitlement(user)
            if expl.allows_questions:
                status_text += t_user(user, "status.vip_active")
            else:
                status_text += t_user(user, "status.vip_inactive")
        status_text += t_user(user, "status.billing_link")

        await message.answer(t_user(user, "status.label", status=status_text))
        logger.info(f"User {user_id} checked their status: {user.status}")
    finally:
        db.close()


_HELP_KEY = {
    "NEW": "help.new",
    "VERIFIED": "help.verified",
    "PENDING_APPROVAL": "help.pending",
    # access.py's help body for APPROVED users emphasises subscription/billing,
    # which is different from verify.py's variant — keep them distinct keys.
    "APPROVED": "help.approved_billing",
}


@router.message(Command("help"))
async def handle_help_command(message: Message) -> None:
    """Handle /help command to show available commands."""
    user_id = message.from_user.id

    logger.info(f"❓ HELP command triggered by user {user_id}")

    db = SessionLocal()
    try:
        user = get_user(db, user_id)
        if not user:
            user = create_user(
                db,
                telegram_id=user_id,
                username=message.from_user.username,
                first_name=message.from_user.full_name,
            )

        body_key = _HELP_KEY.get(user.status, "help.new")
        help_text = t_user(user, "help.title") + t_user(user, body_key)
        await message.answer(help_text)
        logger.info(f"User {user_id} requested help")
    finally:
        db.close()
