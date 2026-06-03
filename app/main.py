"""
Main entry point for the Telegram bot application.
Handles bot startup and shutdown gracefully.
"""

import asyncio
import logging
import os
import signal
import sys

import uvicorn

from .bot import setup_bot, start_bot, stop_bot
from .web import app as web_app
from database.db import init_db
from .config import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def validate_startup_config() -> bool:
    """Validate critical configuration before starting bot."""
    logger.info("Validating startup configuration...")
    
    # Check critical environment variables
    if not config.bot_token:
        logger.critical("CRITICAL: BOT_TOKEN is not set!")
        logger.critical("Please set BOT_TOKEN in your environment variables")
        return False
    
    if not config.admin_id:
        logger.critical("CRITICAL: ADMIN_ID is not set!")
        logger.critical("Please set ADMIN_ID in your environment variables")
        return False
    
    if not config.vip_group_id:
        logger.critical("CRITICAL: VIP_GROUP_ID is not set!")
        logger.critical("Please set VIP_GROUP_ID in your environment variables")
        return False
    
    logger.info("✅ Startup configuration validation passed")
    logger.info(f"MOCK_PAYMENT_ENABLED={config.mock_payment_enabled}")
    logger.info(f"STRIPE_SECRET_KEY present = {bool(config.stripe_api_key)}")
    logger.info(f"STRIPE_PRICE_ID present = {bool(config.stripe_price_id)}")
    return True


async def _run_http_server() -> None:
    """Run the FastAPI health server so Render Free detects an open port."""
    port = int(os.getenv("PORT", "10000"))
    server_config = uvicorn.Config(
        web_app,
        host="0.0.0.0",
        port=port,
        log_level="info",
        access_log=False,
    )
    server = uvicorn.Server(server_config)
    logger.info(f"Starting HTTP server on 0.0.0.0:{port}")
    await server.serve()


async def main() -> None:
    """
    Main application entry point.
    Sets up and starts the Telegram bot plus the HTTP health server.
    """
    try:
        logger.info("Starting Telegram bot application...")

        # Validate startup configuration
        if not validate_startup_config():
            logger.critical("Startup validation failed. Exiting.")
            sys.exit(1)

        # Initialize database
        init_db()

        # Setup bot with all handlers
        await setup_bot()

        # Start polling and the HTTP server concurrently. If either stops,
        # cancel the other so the process exits cleanly.
        await asyncio.gather(start_bot(), _run_http_server())

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
    finally:
        # Ensure graceful shutdown
        await stop_bot()


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)


if __name__ == "__main__":
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run the main application
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application terminated by user")
    except Exception as e:
        logger.error(f"Application failed to start: {e}", exc_info=True)
        sys.exit(1)
