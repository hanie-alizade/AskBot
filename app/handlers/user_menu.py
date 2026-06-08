"""
User-information commands surfaced by the client document:

  /menu        — single screen: subscription status, remaining VIP Legal
                 questions this month, membership benefits, links to docs.
  /rules       — community rules (placeholder).
  /privacy     — privacy policy (placeholder).
  /terms       — terms & conditions (placeholder).
  /disclaimer  — disclaimer (placeholder).
  /benefits    — membership benefit tiers (placeholder).

Legal-document copy lives in services/legal_documents.py so onboarding and
re-display use the same source. Benefits / rules text are placeholders the
client will replace with final wording.
"""

from __future__ import annotations

import logging
from datetime import datetime

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from database.crud import (
    get_user,
    get_user_question_by_id,
    list_user_questions_paginated,
)
from database.db import SessionLocal
from database.models import QuestionStatus, QuestionType
from services.legal_documents import (
    DISCLAIMER_TEXT,
    PRIVACY_TEXT,
    TERMS_TEXT,
    LIABILITY_TEXT,
)

logger = logging.getLogger(__name__)

router = Router()


# Placeholder constants — final text will be supplied by the client.
RULES_TEXT = (
    "📋 <b>Community Rules</b>\n\n"
    "1. No spam.\n"
    "2. No offensive language.\n"
    "3. No unwanted private contact.\n\n"
    "Violation may result in removal from the VIP group.\n\n"
    "[PLACEHOLDER — final wording will be supplied by the client.]"
)

BENEFITS_TEXT = (
    "🎁 <b>Membership Benefits</b>\n\n"
    "• <b>Quick Questions:</b> Unlimited.\n"
    "• <b>VIP Legal Questions:</b> 2 per month.\n"
    "• <b>Before 6 months:</b> 20% discount on private consultation.\n"
    "• <b>After 6 months of active subscription:</b> eligible for a 15-minute lawyer call.\n"
    "• <b>After 2 years of active subscription:</b> 50% discount.\n\n"
    "[PLACEHOLDER — final wording will be supplied by the client.]"
)

RIGHTS_OBLIGATIONS_TEXT = (
    "⚖️ <b>Rights and Obligations</b>\n\n"
    "[PLACEHOLDER — final wording will be supplied by the client.]"
)


def _is_new_month(last, now: datetime) -> bool:
    if last is None:
        return True
    return (last.year, last.month) != (now.year, now.month)


def _build_menu_text(user) -> str:
    status = user.status if user else "UNKNOWN"
    sub = getattr(user, "subscription", None) if user else None
    sub_status = str(sub.status) if sub else "—"
    plan = sub.plan_name if sub else "—"
    end_date = (
        sub.end_date.strftime("%Y-%m-%d") if sub and sub.end_date else "—"
    )

    # Remaining VIP Legal questions this month (matches the monthly reset logic
    # in database.crud._is_new_month — duplicated tiny check to avoid coupling).
    now = datetime.now()
    if user and _is_new_month(user.last_question_date, now):
        remaining = user.question_limit
    else:
        remaining = max(0, (user.question_limit if user else 0) - (user.questions_used if user else 0))
    limit = user.question_limit if user else 0

    return (
        "👤 <b>Main Menu</b>\n\n"
        f"<b>Account status:</b> {status}\n"
        f"<b>Subscription:</b> {sub_status} ({plan})\n"
        f"<b>Period end:</b> {end_date}\n\n"
        f"📊 <b>Remaining VIP Legal questions this month:</b> {remaining}/{limit}\n\n"
        "Pick a section below."
    )


def _build_menu_keyboard() -> InlineKeyboardMarkup:
    """Inline-button hub grouped by section.

    Every button has callback_data=`menu:<key>`. The single dispatcher
    `handle_menu_callback` parses the suffix and delegates to the existing
    `/command` handler so there is one implementation per feature.
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        # 👤 Account
        [
            InlineKeyboardButton(text="📊 Check status", callback_data="menu:status"),
            InlineKeyboardButton(text="💳 Subscription", callback_data="menu:subscription"),
        ],
        [
            InlineKeyboardButton(text="📚 My Questions", callback_data="menu:my_questions"),
        ],
        # 🎁 Membership
        [
            InlineKeyboardButton(text="🎁 Membership benefits", callback_data="menu:benefits"),
        ],
        # 📋 Community
        [
            InlineKeyboardButton(text="📋 Rules", callback_data="menu:rules"),
            InlineKeyboardButton(text="⚖️ Rights & Obligations", callback_data="menu:rights"),
        ],
        # 📄 Legal
        [
            InlineKeyboardButton(text="📄 Privacy Policy", callback_data="menu:privacy"),
            InlineKeyboardButton(text="📄 Terms", callback_data="menu:terms"),
        ],
        [
            InlineKeyboardButton(text="📄 Disclaimer", callback_data="menu:disclaimer"),
        ],
        # 🌐 Settings
        [
            InlineKeyboardButton(text="🌐 Change language", callback_data="menu:language"),
        ],
    ])


@router.message(Command("menu"))
async def handle_menu(message: Message) -> None:
    if message.chat.type != ChatType.PRIVATE:
        return
    db = SessionLocal()
    try:
        user = get_user(db, message.from_user.id)
        await message.answer(
            _build_menu_text(user),
            reply_markup=_build_menu_keyboard(),
            parse_mode="HTML",
        )
        logger.info("menu shown user_id=%s", message.from_user.id)
    finally:
        db.close()


def _spoof_message_as_user(callback: CallbackQuery) -> Message:
    """Build a Message clone whose `from_user` is the user who clicked.

    `callback.message` belongs to the bot, so `message.from_user.id` would
    return the bot's id and break every handler that identifies the caller
    that way. We clone the message, swap `from_user`, and re-bind the bot via
    aiogram's `as_(bot)` so `.answer()` still works.
    """
    return callback.message.model_copy(
        update={"from_user": callback.from_user}
    ).as_(callback.bot)


# Map each callback_data suffix to the lazily-imported handler that owns the
# feature. Lazy imports avoid module-load cycles between user_menu, access,
# subscription_cmd, and language. We pass the spoofed message so the existing
# handlers see the right user id.
async def _delegate_menu_action(key: str, callback: CallbackQuery) -> None:
    if callback.message is None:
        return
    spoofed = _spoof_message_as_user(callback)

    if key == "status":
        from .access import handle_status_command

        await handle_status_command(spoofed)
        return
    if key == "subscription":
        from .subscription_cmd import handle_subscription_status

        await handle_subscription_status(spoofed)
        return
    if key == "my_questions":
        await handle_my_questions(spoofed)
        return
    if key == "benefits":
        await handle_benefits(spoofed)
        return
    if key == "rules":
        await handle_rules(spoofed)
        return
    if key == "rights":
        await handle_rights(spoofed)
        return
    if key == "privacy":
        await handle_privacy(spoofed)
        return
    if key == "terms":
        await handle_terms(spoofed)
        return
    if key == "disclaimer":
        await handle_disclaimer(spoofed)
        return
    if key == "language":
        from .language import handle_language_cmd

        await handle_language_cmd(spoofed)
        return


@router.callback_query(F.data.startswith("menu:"))
async def handle_menu_callback(callback: CallbackQuery) -> None:
    """Single dispatcher for every menu:* inline-button tap."""
    if not callback.data:
        await callback.answer()
        return
    key = callback.data.split(":", 1)[1]
    try:
        await _delegate_menu_action(key, callback)
    finally:
        await callback.answer()
    logger.info("menu_action telegram_id=%s key=%s", callback.from_user.id, key)


@router.message(Command("rules"))
async def handle_rules(message: Message) -> None:
    if message.chat.type != ChatType.PRIVATE:
        return
    await message.answer(RULES_TEXT, parse_mode="HTML")


@router.message(Command("benefits"))
async def handle_benefits(message: Message) -> None:
    if message.chat.type != ChatType.PRIVATE:
        return
    await message.answer(BENEFITS_TEXT, parse_mode="HTML")


@router.message(Command("privacy"))
async def handle_privacy(message: Message) -> None:
    if message.chat.type != ChatType.PRIVATE:
        return
    await message.answer(PRIVACY_TEXT, parse_mode="HTML")


@router.message(Command("terms"))
async def handle_terms(message: Message) -> None:
    if message.chat.type != ChatType.PRIVATE:
        return
    await message.answer(TERMS_TEXT, parse_mode="HTML")


@router.message(Command("disclaimer"))
async def handle_disclaimer(message: Message) -> None:
    if message.chat.type != ChatType.PRIVATE:
        return
    await message.answer(DISCLAIMER_TEXT, parse_mode="HTML")


@router.message(Command("liability"))
async def handle_liability(message: Message) -> None:
    """Bonus: also expose the liability text directly so the client has a stable URL for it."""
    if message.chat.type != ChatType.PRIVATE:
        return
    await message.answer(LIABILITY_TEXT, parse_mode="HTML")


@router.message(Command("rights"))
async def handle_rights(message: Message) -> None:
    """Rights and obligations — content placeholder until client supplies wording."""
    if message.chat.type != ChatType.PRIVATE:
        return
    await message.answer(RIGHTS_OBLIGATIONS_TEXT, parse_mode="HTML")


# --------------------------------------------------------------------------- #
# My Questions — paginated list + detail view
# --------------------------------------------------------------------------- #


_MY_Q_PAGE_SIZE = 5


def _qtype_icon(qtype: str) -> str:
    return "🟢" if qtype == QuestionType.QUICK else "⚖️"


def _qtype_label(qtype: str) -> str:
    return "Quick" if qtype == QuestionType.QUICK else "VIP Legal"


def _qstatus_label(status: str) -> str:
    return {
        QuestionStatus.PENDING: "⏳ Pending",
        QuestionStatus.ANSWERED: "✅ Answered",
        QuestionStatus.FAILED_DELIVERY: "⚠️ Delivery failed",
        QuestionStatus.QUOTA_BLOCKED: "🚫 Blocked (quota exhausted)",
    }.get(status, status or "—")


def _fmt_date(dt) -> str:
    return dt.strftime("%Y-%m-%d") if dt else "—"


def _short_button_label(q) -> str:
    """Compact one-line button label that fits Telegram's button width."""
    icon = _qtype_icon(q.question_type)
    status_short = {
        QuestionStatus.PENDING: "Pending",
        QuestionStatus.ANSWERED: "Answered",
        QuestionStatus.FAILED_DELIVERY: "Failed",
        QuestionStatus.QUOTA_BLOCKED: "Blocked",
    }.get(q.status, "—")
    date = _fmt_date(q.created_at)
    return f"{icon} #{q.id} · {status_short} · {date}"


_SEPARATOR = "━━━━━━━━━━━━"


def _build_my_questions_list(rows, *, offset: int, total: int):
    """Build the (text, keyboard) for the My Questions paginated list."""
    page = (offset // _MY_Q_PAGE_SIZE) + 1
    page_count = max(1, (total + _MY_Q_PAGE_SIZE - 1) // _MY_Q_PAGE_SIZE)

    if total == 0:
        text = (
            "📚 <b>Your Questions Inbox</b>\n\n"
            f"{_SEPARATOR}\n\n"
            "You haven't submitted any questions yet.\n\n"
            "Send me a private message to ask your first question. "
            "Quick questions are unlimited; VIP Legal questions count toward your monthly allowance.\n\n"
            f"{_SEPARATOR}"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[])
        return text, kb

    body_lines = [
        f"📚 <b>My Questions</b>  (page {page} of {page_count}, {total} total)\n"
    ]
    for q in rows:
        body_lines.append(
            f"\n{_qtype_icon(q.question_type)} <b>#{q.id}</b>"
        )
        body_lines.append(f"    Status: {_qstatus_label(q.status)}")
        body_lines.append(f"    Date: {_fmt_date(q.created_at)}")

    rows_kb: list = [
        [InlineKeyboardButton(
            text=_short_button_label(q),
            callback_data=f"myq:view:{q.id}:{offset}",
        )]
        for q in rows
    ]

    # Pagination row (only show buttons that lead somewhere).
    pag_row: list = []
    if offset > 0:
        pag_row.append(InlineKeyboardButton(
            text="⬅️ Prev",
            callback_data=f"myq:list:{max(0, offset - _MY_Q_PAGE_SIZE)}",
        ))
    if offset + _MY_Q_PAGE_SIZE < total:
        pag_row.append(InlineKeyboardButton(
            text="➡️ Next",
            callback_data=f"myq:list:{offset + _MY_Q_PAGE_SIZE}",
        ))
    if pag_row:
        rows_kb.append(pag_row)

    return "\n".join(body_lines), InlineKeyboardMarkup(inline_keyboard=rows_kb)


def _build_my_question_detail(q, *, back_offset: int):
    type_line = f"{_qtype_icon(q.question_type)} {_qtype_label(q.question_type)}"
    reply = (q.admin_reply_text or "").strip()
    reply_block = reply if reply else "⏳ Waiting for response"
    answered_at_block = (
        _fmt_date(q.answered_at) if q.answered_at else "⏳ Not yet answered"
    )

    text = (
        f"📖 <b>Question #{q.id}</b>\n\n"
        f"<b>Question Type:</b>\n{type_line}\n\n"
        f"<b>Status:</b>\n{_qstatus_label(q.status)}\n\n"
        f"<b>Submitted:</b>\n{_fmt_date(q.created_at)}\n\n"
        f"<b>Answered:</b>\n{answered_at_block}\n\n"
        f"<b>Your Question:</b>\n{(q.question_text or '').strip() or '—'}\n\n"
        f"<b>Admin Reply:</b>\n{reply_block}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="⬅️ Back to list",
            callback_data=f"myq:list:{back_offset}",
        )],
    ])
    return text, kb


@router.message(Command("my_questions"))
async def handle_my_questions(message: Message) -> None:
    if message.chat.type != ChatType.PRIVATE:
        return
    user_id = message.from_user.id
    db = SessionLocal()
    try:
        rows, total = list_user_questions_paginated(
            db, user_id, offset=0, limit=_MY_Q_PAGE_SIZE,
        )
        text, kb = _build_my_questions_list(rows, offset=0, total=total)
    finally:
        db.close()
    await message.answer(text, reply_markup=kb, parse_mode="HTML")
    logger.info("my_questions shown user_id=%s total=%s", user_id, total)


@router.callback_query(F.data.startswith("myq:list:"))
async def handle_my_questions_list_page(callback: CallbackQuery) -> None:
    """Render the requested page (used by Prev/Next and Back-to-list)."""
    if not callback.data or callback.message is None:
        await callback.answer()
        return
    try:
        offset = int(callback.data.split(":", 2)[2])
    except (ValueError, IndexError):
        await callback.answer()
        return
    if offset < 0:
        offset = 0

    user_id = callback.from_user.id
    db = SessionLocal()
    try:
        rows, total = list_user_questions_paginated(
            db, user_id, offset=offset, limit=_MY_Q_PAGE_SIZE,
        )
        text, kb = _build_my_questions_list(rows, offset=offset, total=total)
    finally:
        db.close()
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception as e:
        logger.warning("my_questions list edit failed user_id=%s err=%s", user_id, e)
        await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("myq:view:"))
async def handle_my_question_detail(callback: CallbackQuery) -> None:
    """Open a single question — scoped to the caller so ids can't be guessed."""
    if not callback.data or callback.message is None:
        await callback.answer()
        return
    parts = callback.data.split(":")
    if len(parts) != 4:
        await callback.answer()
        return
    try:
        qid = int(parts[2])
        back_offset = int(parts[3])
    except ValueError:
        await callback.answer()
        return

    user_id = callback.from_user.id
    db = SessionLocal()
    try:
        q = get_user_question_by_id(db, user_id, qid)
    finally:
        db.close()

    if not q:
        await callback.answer("Question not found.", show_alert=True)
        return

    text, kb = _build_my_question_detail(q, back_offset=back_offset)
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception as e:
        logger.warning("my_questions detail edit failed user_id=%s err=%s", user_id, e)
        await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()
