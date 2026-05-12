"""
Verification handlers for the user flow.
Handles the initial verification step for new users.
"""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from sqlalchemy.orm import Session

from database.crud import create_user, get_user, update_user_status
from database.db import SessionLocal
from ..config import config

logger = logging.getLogger(__name__)

router = Router()


@router.message(Command("start"))
async def handle_start(message: Message) -> None:
    """Handle /start command based on user state."""
    user_id = message.from_user.id
    
    logger.info(f"🚀 START command triggered by user {user_id}")
    
    # Get or create user in database
    db = SessionLocal()
    try:
        user = get_user(db, user_id)
        if not user:
            user = create_user(
                db, 
                telegram_id=user_id,
                username=message.from_user.username,
                first_name=message.from_user.full_name
            )
        
        logger.info(f"User {user_id} sent /start command. Current state: {user.status}")
        
        if user.status == "NEW":
            await handle_new_user(message, user)
        elif user.status == "VERIFIED":
            await handle_verified_user(message, user)
        elif user.status == "PENDING_APPROVAL":
            await handle_pending_user(message, user)
        elif user.status == "APPROVED":
            await handle_approved_user(message, user)
    finally:
        db.close()


async def handle_new_user(message: Message, user) -> None:
    """Handle new user - show welcome message and verification button."""
    user_id = message.from_user.id
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Verify", callback_data="verify_user")],
        [InlineKeyboardButton(text="📊 Check Status", callback_data="check_status")],
        [InlineKeyboardButton(text="❓ Help", callback_data="show_help")]
    ])
    
    await message.answer(
        "👋 Welcome to AskBot!\n\n"
        "To get started, please verify your account by clicking the button below.",
        reply_markup=keyboard
    )
    
    logger.info(f"Sent welcome message to new user {user_id}")


async def handle_verified_user(message: Message, user) -> None:
    """Handle already verified user - show access request option."""
    user_id = message.from_user.id
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔑 Request Access", callback_data="request_access")],
        [InlineKeyboardButton(text="📊 Check Status", callback_data="check_status")],
        [InlineKeyboardButton(text="❓ Help", callback_data="show_help")]
    ])
    
    await message.answer(
        "✅ You are verified!\n\n"
        "You can now request access to the VIP group by clicking the button below.",
        reply_markup=keyboard
    )
    
    logger.info(f"Sent verified message to user {user_id}")


async def handle_pending_user(message: Message, user) -> None:
    """Handle user with pending approval."""
    user_id = message.from_user.id
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Check Status", callback_data="check_status")],
        [InlineKeyboardButton(text="❓ Help", callback_data="show_help")]
    ])
    
    await message.answer(
        "⏳ Your access request is currently under review.\n\n"
        "Please wait for an admin to approve your request. "
        "You'll be notified once a decision is made.",
        reply_markup=keyboard
    )
    
    logger.info(f"Sent pending message to user {user_id}")


async def handle_approved_user(message: Message, user) -> None:
    """Handle already approved user."""
    user_id = message.from_user.id
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎉 Join VIP Group", url=config.group_invite_link)],
        [InlineKeyboardButton(text="📊 Check Status", callback_data="check_status")],
        [InlineKeyboardButton(text="❓ Help", callback_data="show_help")]
    ])
    
    await message.answer(
        "🎉 Congratulations! You already have access to the VIP group.\n\n"
        "Click the button below to join or check your messages for the invite link.",
        reply_markup=keyboard
    )
    
    logger.info(f"Sent approved message to user {user_id}")


@router.callback_query(F.data == "verify_user")
async def handle_verify_callback(callback: CallbackQuery) -> None:
    """Handle verification button click."""
    user_id = callback.from_user.id
    
    db = SessionLocal()
    try:
        user = get_user(db, user_id)
        if not user or user.status != "NEW":
            await callback.answer("❌ You are already verified!", show_alert=True)
            return
        
        # Mark user as verified
        update_user_status(db, user_id, "VERIFIED")
        
        # Create keyboard for access request
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔑 Request Access", callback_data="request_access")]
        ])
        
        await callback.message.edit_text(
            "✅ Verification complete!\n\n"
            "You can now request access to VIP group by clicking the button below.",
            reply_markup=keyboard
        )
        
        await callback.answer("✅ Successfully verified!")
        logger.info(f"User {user_id} completed verification")
    finally:
        db.close()


@router.callback_query(F.data == "check_status")
async def handle_status_callback(callback: CallbackQuery) -> None:
    """Handle status button click."""
    user_id = callback.from_user.id
    
    db = SessionLocal()
    try:
        user = get_user(db, user_id)
        if not user:
            # User not found - show informational message
            await callback.message.answer(
                "📊 Your Current Status: ❓ Not Registered\n\n"
                "You haven't started the verification process yet.\n\n"
                "👉 Please click the **'✅ Verify'** button to begin the registration process."
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
            
            await callback.message.answer(
                f"📊 Your Current Status: {status_text}"
            )
            
            logger.info(f"User {user_id} checked their status via button: {user.status}")
    finally:
        db.close()
    
    await callback.answer()


@router.callback_query(F.data == "show_help")
async def handle_help_callback(callback: CallbackQuery) -> None:
    """Handle help button click."""
    user_id = callback.from_user.id
    
    db = SessionLocal()
    try:
        user = get_user(db, user_id)
        if not user:
            # Create user if they don't exist
            user = create_user(
                db,
                telegram_id=user_id,
                username=callback.from_user.username,
                first_name=callback.from_user.full_name
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
        
        await callback.message.answer(help_text)
        logger.info(f"User {user_id} requested help via button: {user.status}")
    finally:
        db.close()
    
    await callback.answer()
