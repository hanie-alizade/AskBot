"""
Language selection + persistent reply-keyboard menu handler.

Responsibilities:
- /language command: open the picker any time.
- lang:<code> callback: persist the choice and continue the user's flow.
- Persistent 3-button menu (Check status / Subscription / Change language) —
  the keyboard is sent at the end of every welcome screen, and taps are
  matched against the pre-computed label-set across all 4 locales so a tap
  works whatever language the user has chosen.

First-time language selection is enforced inside verify.handle_start (a NULL
`language` column is the sentinel for "user has not picked yet").
"""

import logging
from typing import Iterable, List, Optional

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)

from app.config import config
from database.crud import create_user, get_user
from database.db import SessionLocal
from services.i18n import LANGUAGE_LABELS, SUPPORTED_LANGUAGES, is_supported, t, t_user

logger = logging.getLogger(__name__)

router = Router(name="language")


# --------------------------------------------------------------------------- #
# Persistent reply-keyboard menu
# --------------------------------------------------------------------------- #


_MENU_KEYS = (
    "menu.btn_check_status",
    "menu.btn_subscription",
    "menu.btn_my_questions",
    "menu.btn_benefits",
    "menu.btn_rules",
    "menu.btn_rights",
    "menu.btn_privacy",
    "menu.btn_terms",
    "menu.btn_disclaimer",
    "menu.btn_change_language",
)


def build_reply_menu(lang: Optional[str]) -> ReplyKeyboardMarkup:
    """Persistent reply keyboard grouped by section.

    Existing three buttons (Check status / Subscription / Change language) are
    preserved exactly — the new rows are appended underneath, grouped by:
      • Account      — Check status, Subscription
      • Membership   — Membership benefits
      • Community    — Rules, Rights & Obligations
      • Legal        — Privacy Policy, Terms, Disclaimer
      • Settings     — Change language
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            # Account
            [
                KeyboardButton(text=t(lang, "menu.btn_check_status")),
                KeyboardButton(text=t(lang, "menu.btn_subscription")),
            ],
            [KeyboardButton(text=t(lang, "menu.btn_my_questions"))],
            # Membership
            [KeyboardButton(text=t(lang, "menu.btn_benefits"))],
            # Community
            [
                KeyboardButton(text=t(lang, "menu.btn_rules")),
                KeyboardButton(text=t(lang, "menu.btn_rights")),
            ],
            # Legal
            [
                KeyboardButton(text=t(lang, "menu.btn_privacy")),
                KeyboardButton(text=t(lang, "menu.btn_terms")),
            ],
            [KeyboardButton(text=t(lang, "menu.btn_disclaimer"))],
            # Settings
            [KeyboardButton(text=t(lang, "menu.btn_change_language"))],
        ],
        resize_keyboard=True,
        is_persistent=True,
        selective=False,
    )


def _label_set(key: str) -> frozenset:
    """All localized variants of one menu label — used for tap dispatch."""
    return frozenset(t(code, key) for code in SUPPORTED_LANGUAGES)


# Built once at import-time; restart needed if locales are edited live.
_CHECK_STATUS_LABELS = _label_set("menu.btn_check_status")
_SUBSCRIPTION_LABELS = _label_set("menu.btn_subscription")
_CHANGE_LANGUAGE_LABELS = _label_set("menu.btn_change_language")
_BENEFITS_LABELS = _label_set("menu.btn_benefits")
_RULES_LABELS = _label_set("menu.btn_rules")
_RIGHTS_LABELS = _label_set("menu.btn_rights")
_PRIVACY_LABELS = _label_set("menu.btn_privacy")
_TERMS_LABELS = _label_set("menu.btn_terms")
_DISCLAIMER_LABELS = _label_set("menu.btn_disclaimer")
_MY_QUESTIONS_LABELS = _label_set("menu.btn_my_questions")


# --------------------------------------------------------------------------- #
# Menu tap → command dispatchers
#
# These run before questions.router (which is registered last) so taps on the
# 3 buttons aren't accidentally treated as user questions. Admin is excluded
# because admin uses the admin_panel reply keyboard.
# --------------------------------------------------------------------------- #


@router.message(
    F.chat.type == ChatType.PRIVATE,
    F.from_user.id != config.admin_id,
    F.text.in_(_CHECK_STATUS_LABELS),
)
async def handle_menu_check_status(message: Message) -> None:
    from .access import handle_status_command
    await handle_status_command(message)


@router.message(
    F.chat.type == ChatType.PRIVATE,
    F.from_user.id != config.admin_id,
    F.text.in_(_SUBSCRIPTION_LABELS),
)
async def handle_menu_subscription(message: Message) -> None:
    from .subscription_cmd import handle_subscription_status
    await handle_subscription_status(message)


@router.message(
    F.chat.type == ChatType.PRIVATE,
    F.from_user.id != config.admin_id,
    F.text.in_(_CHANGE_LANGUAGE_LABELS),
)
async def handle_menu_change_language(message: Message) -> None:
    await handle_language_cmd(message)


# --------------------------------------------------------------------------- #
# Picker (inline language buttons)
# --------------------------------------------------------------------------- #


def _picker_keyboard(codes: Iterable[str] = SUPPORTED_LANGUAGES) -> InlineKeyboardMarkup:
    """Two buttons per row, native-script label, payload is `lang:<code>`."""
    rows: List[List[InlineKeyboardButton]] = []
    row: List[InlineKeyboardButton] = []
    for code in codes:
        label = LANGUAGE_LABELS.get(code, code)
        row.append(InlineKeyboardButton(text=label, callback_data=f"lang:{code}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def send_first_time_picker(message: Message) -> None:
    """Initial picker shown the very first time a user runs /start."""
    await message.answer(
        t(None, "lang.picker_first_time"),
        reply_markup=_picker_keyboard(),
    )


@router.message(Command("language"))
async def handle_language_cmd(message: Message) -> None:
    """User runs /language at any later point to change preference."""
    if message.chat.type != ChatType.PRIVATE:
        return

    user_id = message.from_user.id
    db = SessionLocal()
    try:
        user = get_user(db, user_id)
        # Localize the prompt to the user's CURRENT language so the menu is familiar;
        # falls back to English if they haven't picked yet.
        prompt = t_user(user, "lang.picker_change")
    finally:
        db.close()

    await message.answer(prompt, reply_markup=_picker_keyboard())


@router.callback_query(F.data.startswith("lang:"))
async def handle_language_pick(callback: CallbackQuery) -> None:
    """User tapped a language button — persist choice and continue their flow."""
    if not callback.data or not callback.from_user:
        await callback.answer()
        return

    parts = callback.data.split(":", 1)
    if len(parts) != 2:
        await callback.answer()
        return

    code = parts[1].strip().lower()
    if not is_supported(code):
        await callback.answer("Unsupported language", show_alert=True)
        return

    user_id = callback.from_user.id
    db = SessionLocal()
    try:
        user = get_user(db, user_id)
        if not user:
            # Race: callback before /start created a row. Create on the fly so
            # the choice isn't lost. Telegram user names come from the callback.
            user = create_user(
                db,
                telegram_id=user_id,
                username=callback.from_user.username,
                first_name=callback.from_user.full_name,
            )
        user.language = code
        db.commit()
        db.refresh(user)
        logger.info("language_set user_id=%s lang=%s", user_id, code)

        confirmation = t(code, "lang.set_confirmation")
        if callback.message:
            try:
                await callback.message.edit_text(confirmation)
            except TelegramBadRequest:
                # Message can't be edited (e.g. too old) — send fresh.
                await callback.message.answer(confirmation)

        # Refresh this user's "/" command palette in the new language so it
        # updates immediately (no Telegram app restart needed).
        if callback.message:
            from services.bot_commands import set_user_commands_for_chat

            await set_user_commands_for_chat(callback.message.bot, user_id, code)

        await callback.answer()

        # Continue the user's normal flow in their new language.
        # Imported lazily to avoid a circular import with verify.py.
        from .verify import send_welcome_for_status

        if callback.message:
            await send_welcome_for_status(callback.message, user)
    finally:
        db.close()


# --------------------------------------------------------------------------- #
# Menu-button taps (reply-keyboard text). Dispatched by matching the user's
# message text against the pre-computed multilingual label sets so a tap works
# in whichever language the user picked. Must be registered before the generic
# "any private text → question" handler in questions.py (router order is
# enforced in app/bot.py: language router is included before verify/questions).
# --------------------------------------------------------------------------- #


@router.message(F.chat.type == ChatType.PRIVATE, F.text.in_(_CHECK_STATUS_LABELS))
async def handle_menu_check_status(message: Message) -> None:
    """Reply-keyboard tap: behaves like /status."""
    from .access import handle_status_command

    await handle_status_command(message)


@router.message(F.chat.type == ChatType.PRIVATE, F.text.in_(_SUBSCRIPTION_LABELS))
async def handle_menu_subscription(message: Message) -> None:
    """Reply-keyboard tap: behaves like /subscription."""
    from .subscription_cmd import handle_subscription_status

    await handle_subscription_status(message)


@router.message(F.chat.type == ChatType.PRIVATE, F.text.in_(_CHANGE_LANGUAGE_LABELS))
async def handle_menu_change_language(message: Message) -> None:
    """Reply-keyboard tap: behaves like /language."""
    await handle_language_cmd(message)


# --------------------------------------------------------------------------- #
# New menu sections: Membership / Community / Legal.
# Each tap delegates to the existing /command handler in app.handlers.user_menu
# so there is exactly one implementation per feature.
# --------------------------------------------------------------------------- #


@router.message(F.chat.type == ChatType.PRIVATE, F.text.in_(_BENEFITS_LABELS))
async def handle_menu_benefits(message: Message) -> None:
    """Reply-keyboard tap: behaves like /benefits."""
    from .user_menu import handle_benefits

    await handle_benefits(message)


@router.message(F.chat.type == ChatType.PRIVATE, F.text.in_(_RULES_LABELS))
async def handle_menu_rules(message: Message) -> None:
    """Reply-keyboard tap: behaves like /rules."""
    from .user_menu import handle_rules

    await handle_rules(message)


@router.message(F.chat.type == ChatType.PRIVATE, F.text.in_(_RIGHTS_LABELS))
async def handle_menu_rights(message: Message) -> None:
    """Reply-keyboard tap: behaves like /rights."""
    from .user_menu import handle_rights

    await handle_rights(message)


@router.message(F.chat.type == ChatType.PRIVATE, F.text.in_(_PRIVACY_LABELS))
async def handle_menu_privacy(message: Message) -> None:
    """Reply-keyboard tap: behaves like /privacy."""
    from .user_menu import handle_privacy

    await handle_privacy(message)


@router.message(F.chat.type == ChatType.PRIVATE, F.text.in_(_TERMS_LABELS))
async def handle_menu_terms(message: Message) -> None:
    """Reply-keyboard tap: behaves like /terms."""
    from .user_menu import handle_terms

    await handle_terms(message)


@router.message(F.chat.type == ChatType.PRIVATE, F.text.in_(_DISCLAIMER_LABELS))
async def handle_menu_disclaimer(message: Message) -> None:
    """Reply-keyboard tap: behaves like /disclaimer."""
    from .user_menu import handle_disclaimer

    await handle_disclaimer(message)


@router.message(F.chat.type == ChatType.PRIVATE, F.text.in_(_MY_QUESTIONS_LABELS))
async def handle_menu_my_questions(message: Message) -> None:
    """Reply-keyboard tap: behaves like /my_questions."""
    from .user_menu import handle_my_questions

    await handle_my_questions(message)
