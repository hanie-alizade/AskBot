"""
Bot initialization and setup module.
Creates and configures the Telegram bot instance.
"""

import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from .config import config


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Create bot instance with default properties
bot = Bot(
    token=config.bot_token,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML
    )
)

# Create dispatcher instance
dp = Dispatcher()


async def setup_bot() -> None:
    """
    Setup bot with all handlers and middleware.
    This function should be called before starting the bot.
    """
    logger.info("Setting up bot handlers...")
    
    # Import and register handlers here
    from .handlers import start, verify, access, admin, group_moderation, questions
    
    # Register all routers (order matters - first matching handler wins)
    logger.info("Registering routers in order:")
    
    # Group moderation should come first for group messages
    logger.info("1. group_moderation.router")
    dp.include_router(group_moderation.router)
    
    # Command handlers should come before generic handlers
    logger.info("2. verify.router")
    dp.include_router(verify.router)
    logger.info("3. access.router")
    dp.include_router(access.router)
    logger.info("4. admin.router")
    dp.include_router(admin.router)
    logger.info("5. start.router")
    dp.include_router(start.router)
    
    # Questions router should be last to catch only actual questions
    logger.info("6. questions.router (last)")
    dp.include_router(questions.router)
    
    logger.info("Router registration completed")
    
    # Pass bot instance to handlers for sending messages
    admin.setup_bot_instance(bot)
    access.setup_bot_instance(bot)
    group_moderation.setup_bot_instance(bot)
    questions.setup_bot_instance(bot)
    
    logger.info("Bot setup completed")


async def start_bot() -> None:
    """
    Start polling for bot updates with retry logic.
    """
    logger.info("Starting bot polling...")
    
    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            await dp.start_polling(bot)
            break
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Bot startup failed (attempt {attempt + 1}/{max_retries}): {e}")
                logger.info(f"Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error(f"Failed to start bot after {max_retries} attempts: {e}")
                raise


async def stop_bot() -> None:
    """
    Stop the bot gracefully.
    """
    logger.info("Stopping bot...")
    await bot.session.close()
    logger.info("Bot stopped successfully")
