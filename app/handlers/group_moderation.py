"""
Group moderation handlers for VIP group content separation.
Handles automatic deletion of user messages and redirects to private chat.
"""

import logging
from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.filters import ChatMemberUpdatedFilter, IS_MEMBER
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from database.crud import get_user
from database.db import SessionLocal
from ..config import config

logger = logging.getLogger(__name__)

router = Router()

# Global bot instance for sending messages
_bot_instance = None

def setup_bot_instance(bot: Bot) -> None:
    """Setup bot instance for sending messages."""
    global _bot_instance
    _bot_instance = bot


@router.message(F.chat.type == ChatType.GROUP, F.text)
async def handle_group_message(message: Message) -> None:
    """Handle messages in the VIP group - delete non-admin messages."""
    
    # Only process messages in the configured VIP group
    if message.chat.id != config.vip_group_id:
        return
    
    # Check if sender is admin
    if message.from_user.id == config.admin_id:
        logger.info(f"Admin message in VIP group allowed: {message.from_user.id}")
        return
    
    # Check if user is approved
    db = SessionLocal()
    try:
        user = get_user(db, message.from_user.id)
        if not user or user.status != "APPROVED":
            await handle_unauthorized_message(message)
            return
        
        # Delete the message from approved users too (keep group clean)
        await delete_user_message(message)
        await send_private_redirect(message.from_user.id)
        
        logger.info(f"Deleted message from approved user {message.from_user.id} in VIP group")
        
    except Exception as e:
        logger.error(f"Error handling group message from {message.from_user.id}: {e}")
    finally:
        db.close()


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


async def send_private_redirect(user_id: int) -> None:
    """Send private message to user redirecting them to chat with bot."""
    try:
        if not _bot_instance:
            logger.warning("Bot instance not available for private redirect")
            return
        
        redirect_message = (
            "📢 **Group Message Notice**\n\n"
            "Your message in the VIP group has been removed to keep the channel clean.\n\n"
            "👉 Please ask your questions directly in **private chat** with this bot.\n\n"
            "This helps maintain a clean environment for important announcements only."
        )
        
        await _bot_instance.send_message(
            chat_id=user_id,
            text=redirect_message,
            parse_mode="Markdown"
        )
        
        logger.info(f"Sent private redirect message to user {user_id}")
        
    except TelegramForbiddenError as e:
        logger.warning(f"Cannot send private message to user {user_id}: {e}")
        logger.info("User may have blocked the bot or disabled private messages")
    except Exception as e:
        logger.error(f"Failed to send private redirect to user {user_id}: {e}")


async def handle_unauthorized_message(message: Message) -> None:
    """Handle messages from non-approved users."""
    try:
        # Delete the message
        await delete_user_message(message)
        
        # Try to send a private message
        await send_private_redirect(message.from_user.id)
        
        logger.info(f"Handled unauthorized message from user {message.from_user.id}")
        
    except Exception as e:
        logger.error(f"Error handling unauthorized message: {e}")


@router.message(F.chat.type == ChatType.SUPERGROUP, F.text)
async def handle_supergroup_message(message: Message) -> None:
    """Handle messages in supergroups (same logic as regular groups)."""
    # Delegate to the group message handler
    await handle_group_message(message)


# Handle other message types (photos, documents, etc.) in the group
@router.message(F.chat.type == ChatType.GROUP)
async def handle_group_content(message: Message) -> None:
    """Handle any content in the VIP group."""
    # Only process messages in the configured VIP group
    if message.chat.id != config.vip_group_id:
        return
    
    # Check if sender is admin
    if message.from_user.id == config.admin_id:
        return
    
    # Delete any content from non-admin users
    await delete_user_message(message)
    await send_private_redirect(message.from_user.id)
    
    logger.info(f"Deleted content from user {message.from_user.id} in VIP group")


@router.message(F.chat.type == ChatType.SUPERGROUP)
async def handle_supergroup_content(message: Message) -> None:
    """Handle any content in supergroups."""
    await handle_group_content(message)
