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
            await callback.answer("❌ You cannot request access at this stage!", show_alert=True)
            return
        
        # Check if user already has a pending request
        if user.status == "PENDING_APPROVAL":
            await callback.answer("⏳ Your request is already under review!", show_alert=True)
            return
        
        # Set user state to pending approval
        update_user_status(db, user_id, "PENDING_APPROVAL")
        
        # Notify admin
        await notify_admin_about_request(user_id, callback.from_user.full_name)
        
        # Update user message
        await callback.message.edit_text(
            "📝 Your access request has been submitted!\n\n"
            "⏳ Your request is now under review. "
            "An admin will review your request and you'll be notified once a decision is made.\n\n"
            "Please be patient - this usually takes a few hours."
        )
        
        await callback.answer("✅ Request submitted!")
        logger.info(f"User {user_id} ({callback.from_user.full_name}) requested access")
    finally:
        db.close()


async def notify_admin_about_request(user_id: int, user_name: str) -> None:
    """Send notification to admin about new access request with inline buttons."""
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


@router.message(Command("status"))
async def handle_status_command(message: Message) -> None:
    """Handle /status command to show current user status."""
    user_id = message.from_user.id
    
    logger.info(f"📊 STATUS command triggered by user {user_id}")
    
    db = SessionLocal()
    try:
        user = get_user(db, user_id)
        if not user:
            # User not found - show informational message
            await message.answer(
                "📊 Your Current Status: ❓ Not Registered\n\n"
                "You haven't started the verification process yet.\n\n"
                "👉 Please send **/start** to begin the registration process."
            )
            logger.info(f"User {user_id} checked status but not found in database")
        else:
            # User found - show their actual status
            status_messages = {
                "NEW": "🆕 New User - Please verify your account",
                "VERIFIED": "✅ Verified - You can request access",
                "PENDING_APPROVAL": "⏳ Pending Approval - Your request is under review",
                "APPROVED": "🎉 Approved - You have access to the VIP group",
                "REJECTED": "❌ Rejected - Your access request has been denied"
            }
            
            status_text = status_messages.get(user.status, "❓ Unknown Status")
            if user.status == "APPROVED":
                expl = policy.explain_question_entitlement(user)
                if expl.allows_questions:
                    status_text += "\n💳 VIP entitlement: Active"
                else:
                    status_text += "\n💳 VIP entitlement: Inactive (subscription required)"
            status_text += "\n\n📎 Billing & access: /subscription"

            await message.answer(
                f"📊 Your Current Status: {status_text}"
            )
            
            logger.info(f"User {user_id} checked their status: {user.status}")
    finally:
        db.close()


@router.message(Command("help"))
async def handle_help_command(message: Message) -> None:
    """Handle /help command to show available commands."""
    user_id = message.from_user.id
    
    logger.info(f"❓ HELP command triggered by user {user_id}")
    
    db = SessionLocal()
    try:
        user = get_user(db, user_id)
        if not user:
            # Create user if they don't exist
            user = create_user(
                db,
                telegram_id=user_id,
                username=message.from_user.username,
                first_name=message.from_user.full_name
            )
        
        help_text = "🤖 AskBot Help\n\n"
        
        if user.status == "NEW":
            help_text += "Available commands:\n"
            help_text += "/start - Begin verification process\n"
            help_text += "/help - Show this help message\n"
            help_text += "/status - Check your current status\n\n"
            help_text += "Click the 'Verify' button to get started!"
        
        elif user.status == "VERIFIED":
            help_text += "Available commands:\n"
            help_text += "/start - Show access request option\n"
            help_text += "/help - Show this help message\n"
            help_text += "/status - Check your current status\n\n"
            help_text += "Click the 'Request Access' button to continue!"
        
        elif user.status == "PENDING_APPROVAL":
            help_text += "Available commands:\n"
            help_text += "/start - Show pending status\n"
            help_text += "/help - Show this help message\n"
            help_text += "/status - Check your current status\n\n"
            help_text += "Your request is under review. Please wait for admin approval."
        
        elif user.status == "APPROVED":
            help_text += "Available commands:\n"
            help_text += "/start - Show approved status\n"
            help_text += "/help - Show this help message\n"
            help_text += "/status - Check your current status\n\n"
            help_text += "You have access to the VIP group! Check your messages for the invite link."
        
        await message.answer(help_text)
        logger.info(f"User {user_id} requested help")
    finally:
        db.close()
