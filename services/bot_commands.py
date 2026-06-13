"""Telegram bot-command menu (the "/" command palette) management.

The palette shown in Telegram's chat input is set via the Bot API
`setMyCommands`. Telegram caches it client-side, so a list set only once (or via
BotFather) never reflects an in-bot language change until the app is restarted.

Fix: push a PER-CHAT command list (`BotCommandScopeChat`) whenever a user or the
admin changes language. A per-chat scope overrides the language defaults for
that single chat and Telegram refreshes it promptly — no app restart needed.

Roles are kept separate:
  - Regular users get the user command set, localized via the user i18n catalog.
  - The admin gets an admin command set, localized via the admin i18n catalog.

Every call is best-effort: a failed Bot API call is logged and swallowed so it
can never break the surrounding flow (language change, startup).
"""

from __future__ import annotations

import logging
from typing import List

from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault

from app.config import config
from services.i18n import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES, t
from services.i18n.admin import get_admin_language, get_admin_text

logger = logging.getLogger(__name__)

# (command, user-i18n description key). Only commands that have a real handler.
USER_COMMANDS = (
    ("start", "cmd_desc.start"),
    ("menu", "cmd_desc.menu"),
    ("status", "cmd_desc.status"),
    ("subscription", "cmd_desc.subscription"),
    ("language", "cmd_desc.language"),
    ("help", "cmd_desc.help"),
)

# (command, admin-i18n description key).
ADMIN_COMMANDS = (
    ("start", "cmd_desc.start"),
    ("help", "cmd_desc.help"),
    ("status", "cmd_desc.status"),
    ("language", "cmd_desc.language"),
    ("pending", "cmd_desc.pending"),
    ("users", "cmd_desc.users"),
    ("stats", "cmd_desc.stats"),
)


def _user_command_list(lang) -> List[BotCommand]:
    return [BotCommand(command=c, description=t(lang, key)) for c, key in USER_COMMANDS]


def _admin_command_list(lang) -> List[BotCommand]:
    return [BotCommand(command=c, description=get_admin_text(key, lang)) for c, key in ADMIN_COMMANDS]


async def set_user_commands_for_chat(bot: Bot, chat_id: int, lang) -> None:
    """Push the user command palette for ONE chat in `lang` (immediate refresh)."""
    try:
        await bot.set_my_commands(
            _user_command_list(lang), scope=BotCommandScopeChat(chat_id=chat_id)
        )
        logger.info("bot_commands user set chat_id=%s lang=%s", chat_id, lang)
    except Exception as e:  # noqa: BLE001 - menu update must never break the flow
        logger.warning("set_user_commands_for_chat failed chat_id=%s err=%s", chat_id, e)


async def set_admin_commands_for_chat(bot: Bot, chat_id: int, lang) -> None:
    """Push the admin command palette for the admin chat in `lang`."""
    try:
        await bot.set_my_commands(
            _admin_command_list(lang), scope=BotCommandScopeChat(chat_id=chat_id)
        )
        logger.info("bot_commands admin set chat_id=%s lang=%s", chat_id, lang)
    except Exception as e:  # noqa: BLE001
        logger.warning("set_admin_commands_for_chat failed chat_id=%s err=%s", chat_id, e)


async def setup_default_commands(bot: Bot) -> None:
    """Register baseline command palettes at startup.

    - Default scope in English (fallback for everyone).
    - Per-language defaults so a new user sees the menu in their Telegram-app
      language before they pick one in the bot.
    - The admin chat scope in the admin's currently-selected admin language.
    """
    try:
        await bot.set_my_commands(
            _user_command_list(DEFAULT_LANGUAGE), scope=BotCommandScopeDefault()
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("setup_default_commands default scope failed: %s", e)

    for code in SUPPORTED_LANGUAGES:
        try:
            await bot.set_my_commands(
                _user_command_list(code),
                scope=BotCommandScopeDefault(),
                language_code=code,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("setup_default_commands lang=%s failed: %s", code, e)

    # Admin gets the admin palette pinned to their chat in their admin language.
    await set_admin_commands_for_chat(bot, config.admin_id, get_admin_language())
