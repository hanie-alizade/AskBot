"""
Start command handler module.
Handles the /start command for the Telegram bot.
This module now delegates to the verification system.
"""

import logging
from aiogram import Router, types
from aiogram.filters import CommandStart

# Create router for start commands
router = Router()
logger = logging.getLogger(__name__)


@router.message(CommandStart())
async def handle_start_command(message: types.Message) -> None:
    """
    Handle the /start command by delegating to verification system.
    
    Args:
        message: The incoming message object
    """
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    
    logger.info(f"User {username} (ID: {user_id}) started the bot")
    
    # Import here to avoid circular imports
    from .verify import handle_start as verify_handle_start
    
    # Delegate to verification handler
    await verify_handle_start(message)
