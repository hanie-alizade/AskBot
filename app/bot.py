"""
Bot initialization and setup module.
Creates and configures the Telegram bot instance.
"""

import asyncio
import contextlib
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import ErrorEvent
from database.db import SessionLocal
from .config import config


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def _vip_membership_background_loop(bot_instance: Bot) -> None:
    """Reconcile VIP group bans with subscription state (removal delay + renewal unban)."""
    interval = max(5, int(config.vip_membership_sync_interval_seconds))
    while True:
        try:
            if config.vip_group_id:
                db = SessionLocal()
                try:
                    from services.vip_membership import reconcile_vip_group_membership

                    await reconcile_vip_group_membership(bot_instance, db)
                finally:
                    db.close()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("VIP membership sync failed: %s", e, exc_info=True)
        await asyncio.sleep(interval)


# Create bot instance with default properties
bot = Bot(
    token=config.bot_token,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML
    )
)

# Create dispatcher instance
dp = Dispatcher()


@dp.error()
async def _swallow_stale_callback_errors(event: ErrorEvent) -> bool:
    """Silence "query is too old" callback answer errors.

    Telegram drops callback_query IDs after ~15 minutes. When the bot is
    restarted, polling replays any queued callback presses; by the time the
    handler runs and calls `callback.answer()` the ID is no longer valid and
    Telegram returns Bad Request. The handler itself already succeeded — only
    the trailing answer fails — so it's safe to log-and-swallow.
    """
    exc = event.exception
    if isinstance(exc, TelegramBadRequest) and "query is too old" in str(exc).lower():
        logger.info("Ignored stale callback_query answer: %s", exc)
        return True
    return False


async def setup_bot() -> None:
    """
    Setup bot with all handlers and middleware.
    This function should be called before starting the bot.
    """
    logger.info("Setting up bot handlers...")
    
    # Import and register handlers here
    from .handlers import start, verify, access, subscription_cmd, admin, group_moderation, questions, admin_panel, language, user_menu
    from .roles import bind_admin_only, bind_user_only

    # --- Centralized role separation (authorization at the router boundary) ---
    # Not UI-dependent: these filters gate EVERY handler in the router so an
    # admin can never fall into a user flow, and a user can never reach the
    # admin panel — regardless of routing order or a missing per-handler check.
    #
    # Admin-only surface (defense-in-depth; handlers also self-check):
    bind_admin_only(admin_panel.router)
    # User-only surfaces — onboarding, verification, legal, language picker,
    # the user menu, and subscription purchase/management. `admin.router`,
    # `questions.router`, `access.router` and `group_moderation.router` are
    # intentionally left mixed/shared: they serve both roles via their own
    # per-handler filters (e.g. admin reply vs user question submission, the
    # /status & /help info commands, and admin's unauthorized-command replies).
    for _user_router in (
        language.router,
        verify.router,
        start.router,
        subscription_cmd.router,
        user_menu.router,
    ):
        bind_user_only(_user_router)

    # Register all routers (order matters - first matching handler wins)
    logger.info("Registering routers in order:")

    logger.info("0. admin_panel.router (admin /start + menus)")
    dp.include_router(admin_panel.router)

    # Group moderation should come first for group messages
    logger.info("1. group_moderation.router")
    dp.include_router(group_moderation.router)

    # Language router handles /language + lang:* callbacks.
    # Placed before verify so the lang:* callback resolves here, but it does
    # NOT claim /start — verify.router still owns the start flow.
    logger.info("1b. language.router")
    dp.include_router(language.router)

    # Command handlers should come before generic handlers
    logger.info("2. verify.router")
    dp.include_router(verify.router)
    logger.info("3. access.router")
    dp.include_router(access.router)
    logger.info("3b. subscription_cmd.router")
    dp.include_router(subscription_cmd.router)
    logger.info("3c. user_menu.router")
    dp.include_router(user_menu.router)
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
    admin_panel.setup_bot_instance(bot)
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
    
    vip_sync_task = asyncio.create_task(_vip_membership_background_loop(bot))
    try:
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
    finally:
        vip_sync_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await vip_sync_task


async def stop_bot() -> None:
    """
    Stop the bot gracefully.
    """
    logger.info("Stopping bot...")
    await bot.session.close()
    logger.info("Bot stopped successfully")
