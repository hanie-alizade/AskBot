"""
Button-driven admin panel (Telegram inline UI).

Persistent reply keyboard + /start for admin; all workflows use callbacks + optional
one-shot text only after "Compose reply" for a pending question.
"""

from __future__ import annotations

import html
import logging
from datetime import datetime
from typing import List, Optional

from aiogram import Bot, F, Router
from aiogram.filters import BaseFilter, CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from app.config import config
from database.crud import (
    answer_question,
    count_distinct_payment_users,
    count_users_total,
    get_pending_users,
    get_question_by_id,
    get_user,
    list_latest_payment_per_user_page,
    list_payments_paginated,
    list_questions_paginated,
    list_subscriptions_paginated,
    list_users_paginated,
    list_webhook_logs_paginated,
    mark_question_failed_delivery,
    reject_user,
    reset_user_completely,
    update_user_status,
)
from database.db import SessionLocal
from database.models import Question, User
from database.models_subscription import Payment, Subscription
from services.admin_panel_state import (
    append_id_digit,
    backspace_id_buffer,
    clear_id_search_buffer,
    clear_pending_answer,
    get_id_search_buffer,
    get_pending_answer,
    set_id_search_buffer,
    set_pending_answer,
)
from services.entitlement_policy import EntitlementPolicy
from services.subscription_readout import build_subscription_view, format_admin_subscription_status_message
from services.subscription_service import SubscriptionService
from services.vip_invite import notify_vip_invite_if_eligible

logger = logging.getLogger(__name__)

router = Router(name="admin_panel")

_bot: Optional[Bot] = None
PAGE = 6

REPLY_USER_MANAGEMENT = "User Management"
REPLY_QUESTIONS = "Questions"
REPLY_SUB_PAY = "Subscriptions & Payment"
REPLY_SYSTEM = "System Settings"

ADMIN_REPLY_SECTIONS = frozenset(
    {
        REPLY_USER_MANAGEMENT,
        REPLY_QUESTIONS,
        REPLY_SUB_PAY,
        REPLY_SYSTEM,
    }
)

_REJECT_REASONS = (
    ("0", "Standards", "Does not meet access standards."),
    ("1", "Spam", "Spam or automated behaviour."),
    ("2", "Other", "Access denied."),
)


def setup_bot_instance(bot: Bot) -> None:
    global _bot
    _bot = bot


def _is_admin(uid: int) -> bool:
    return uid == config.admin_id


def _admin_reply_keyboard() -> ReplyKeyboardMarkup:
    """Two buttons per row; Telegram shares row width between them."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=REPLY_USER_MANAGEMENT),
                KeyboardButton(text=REPLY_QUESTIONS),
            ],
            [
                KeyboardButton(text=REPLY_SUB_PAY),
                KeyboardButton(text=REPLY_SYSTEM),
            ],
        ],
        resize_keyboard=True,
        is_persistent=True,
        selective=False,
    )


def _kb_main() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="User Management", callback_data="adm:um"),
                InlineKeyboardButton(text="Questions", callback_data="adm:qm"),
            ],
            [
                InlineKeyboardButton(text="Subscriptions & Payment", callback_data="adm:sm"),
                InlineKeyboardButton(text="System Settings", callback_data="adm:sy"),
            ],
        ]
    )


def _kb_users_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔢 Find by Telegram ID", callback_data="adm:ids")],
            [InlineKeyboardButton(text="📋 All users (paged)", callback_data="adm:ul:0")],
            [InlineKeyboardButton(text="⏳ Pending approval", callback_data="adm:up")],
            *_nav("adm:h"),
        ]
    )


def _kb_questions_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📌 Pending", callback_data="adm:qp:0")],
            [InlineKeyboardButton(text="📚 All questions", callback_data="adm:qh:0")],
            *_nav("adm:h"),
        ]
    )


def _kb_subscriptions_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📜 Subscriptions", callback_data="adm:sl:0")],
            [InlineKeyboardButton(text="💵 Recent payments", callback_data="adm:pf:0")],
            [InlineKeyboardButton(text="📡 Webhook log", callback_data="adm:wl:0")],
            [InlineKeyboardButton(text="👤 Last payment / user", callback_data="adm:pp:0")],
            *_nav("adm:h"),
        ]
    )


def _system_settings_text() -> str:
    return "\n".join(
        [
            "<b>System Settings</b> (read-only)\n",
            f"VIP_GROUP_ID: <code>{config.vip_group_id}</code>",
            f"SUBSCRIPTION_ENFORCEMENT_ENABLED: <b>{config.subscription_enforcement_enabled}</b>",
            f"SUBSCRIPTION_GRANDFATHER_ENABLED: <b>{config.subscription_grandfather_enabled}</b>",
            f"MOCK_PAYMENT_ENABLED: <b>{config.mock_payment_enabled}</b>",
            f"MOCK_SUBSCRIPTION_ACTIVE_BY_DEFAULT: <b>{config.mock_subscription_active_by_default}</b>",
            f"VIP lapse removal delay (s): <code>{config.vip_subscription_lapse_removal_delay_seconds}</code>",
            f"VIP sync interval (s): <code>{config.vip_membership_sync_interval_seconds}</code>",
            f"Stripe key set: <b>{bool(config.stripe_api_key)}</b>",
            f"Webhook secret set: <b>{bool(config.stripe_webhook_secret)}</b>",
        ]
    )


def _kb_system_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Refresh", callback_data="adm:sy")],
            *_nav("adm:h"),
        ]
    )


def _nav(back_cb: Optional[str]) -> List[List[InlineKeyboardButton]]:
    row: List[InlineKeyboardButton] = []
    if back_cb:
        row.append(InlineKeyboardButton(text="◀ Back", callback_data=back_cb))
    row.append(InlineKeyboardButton(text="🏠 Home", callback_data="adm:h"))
    return [row]


async def _safe_edit(
    callback: CallbackQuery, text: str, reply_markup: Optional[InlineKeyboardMarkup] = None
) -> None:
    try:
        await callback.message.edit_text(
            text, reply_markup=reply_markup, parse_mode="HTML"
        )
    except TelegramBadRequest:
        await callback.message.answer(
            text, reply_markup=reply_markup, parse_mode="HTML"
        )


def _user_summary_line(u: User, sub: Optional[Subscription]) -> str:
    un = f"@{html.escape(u.username)}" if u.username else "—"
    sub_s = str(sub.status) if sub else "—"
    plan = html.escape(str(sub.plan_name)) if sub else "—"
    return (
        f"• <code>{u.telegram_id}</code> {html.escape(u.first_name[:24])} {un}\n"
        f"  status: <b>{html.escape(u.status)}</b> | sub: <b>{html.escape(sub_s)}</b> {plan}\n"
        f"  questions used: <b>{u.questions_used}</b> / {u.question_limit}"
    )


def _kb_user_actions(tid: int, u: User) -> List[List[InlineKeyboardButton]]:
    rows: List[List[InlineKeyboardButton]] = []
    tid_s = str(tid)
    if u.status == "PENDING_APPROVAL":
        rows.append(
            [
                InlineKeyboardButton(text="✅ Approve", callback_data=f"adm:ua:{tid_s}"),
                InlineKeyboardButton(text="❌ Reject", callback_data=f"adm:rjm:{tid_s}"),
            ]
        )
    if u.status not in ("NEW",):
        rows.append(
            [
                InlineKeyboardButton(text="🔄 Reset user", callback_data=f"adm:urx:{tid_s}"),
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(text="⏹ Expire subscription", callback_data=f"adm:ue:{tid_s}"),
            InlineKeyboardButton(text="⏳ Grace", callback_data=f"adm:ug:{tid_s}"),
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(text="▶️ Activate sub", callback_data=f"adm:uac:{tid_s}"),
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(text="🚫 Remove from VIP", callback_data=f"adm:uvp:{tid_s}"),
        ]
    )
    rows.extend(_nav("adm:um"))
    return rows


async def _render_user_detail(callback: CallbackQuery, tid: int, *, back: str) -> None:
    db = SessionLocal()
    try:
        u = get_user(db, tid)
        if not u:
            await _safe_edit(callback, f"User <code>{tid}</code> not found.", InlineKeyboardMarkup(inline_keyboard=_nav(back)))
            await callback.answer()
            return
        sub = getattr(u, "subscription", None)
        svc = SubscriptionService(db)
        snap = svc.get_subscription_snapshot(tid, user=u)
        expl = EntitlementPolicy().explain_question_entitlement(u)
        vm = build_subscription_view(snap, expl)
        sub_block = format_admin_subscription_status_message(tid, vm)
        text = (
            f"<b>User</b> <code>{tid}</code>\n"
            f"Name: {html.escape(u.first_name)}\n"
            f"Username: {('@' + html.escape(u.username)) if u.username else '—'}\n"
            f"Approval: <b>{html.escape(u.status)}</b>\n"
            f"Questions used: <b>{u.questions_used}</b> / limit {u.question_limit}\n\n"
            f"{html.escape(sub_block)}"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=_kb_user_actions(tid, u))
        await _safe_edit(callback, text, kb)
    finally:
        db.close()
    await callback.answer()


@router.message(CommandStart(), F.from_user.id == config.admin_id)
async def admin_start(message: Message) -> None:
    clear_pending_answer(message.from_user.id)
    clear_id_search_buffer(message.from_user.id)
    await message.answer(
        "<b>AskBot — Admin</b>\n\n"
        "Use the <b>keyboard below</b> (two buttons per row) to open a section, "
        "or use the <b>inline</b> shortcuts in the next message.\n"
        "All section actions stay button-driven.",
        reply_markup=_admin_reply_keyboard(),
        parse_mode="HTML",
    )
    await message.answer(
        "<b>Home</b> — choose a section:",
        reply_markup=_kb_main(),
        parse_mode="HTML",
    )


class AdminSectionReplyFilter(BaseFilter):
    """Reply-keyboard section opener; ignored while composing a question answer."""

    async def __call__(self, message: Message) -> bool:
        if not message.from_user or message.from_user.id != config.admin_id:
            return False
        if not message.text or message.text not in ADMIN_REPLY_SECTIONS:
            return False
        return get_pending_answer(message.from_user.id) is None


@router.message(AdminSectionReplyFilter())
async def admin_reply_section(message: Message) -> None:
    clear_pending_answer(message.from_user.id)
    clear_id_search_buffer(message.from_user.id)
    label = message.text or ""
    if label == REPLY_USER_MANAGEMENT:
        await message.answer(
            "<b>User Management</b>\n\nSelect:",
            reply_markup=_kb_users_menu(),
            parse_mode="HTML",
        )
    elif label == REPLY_QUESTIONS:
        await message.answer(
            "<b>Questions</b>\n\nSelect:",
            reply_markup=_kb_questions_menu(),
            parse_mode="HTML",
        )
    elif label == REPLY_SUB_PAY:
        await message.answer(
            "<b>Subscriptions &amp; Payment</b>\n\nSelect:",
            reply_markup=_kb_subscriptions_menu(),
            parse_mode="HTML",
        )
    elif label == REPLY_SYSTEM:
        await message.answer(
            _system_settings_text(),
            reply_markup=_kb_system_menu(),
            parse_mode="HTML",
        )


@router.callback_query(F.data == "adm:h", F.from_user.id == config.admin_id)
async def cb_home(callback: CallbackQuery) -> None:
    clear_pending_answer(callback.from_user.id)
    clear_id_search_buffer(callback.from_user.id)
    await _safe_edit(
        callback,
        "<b>Home</b>\n\nChoose a section:",
        _kb_main(),
    )
    await callback.answer()


@router.callback_query(F.data == "adm:um", F.from_user.id == config.admin_id)
async def cb_users_menu(callback: CallbackQuery) -> None:
    await _safe_edit(callback, "<b>User Management</b>\n\nSelect:", _kb_users_menu())
    await callback.answer()


@router.callback_query(F.data == "adm:up", F.from_user.id == config.admin_id)
async def cb_users_pending(callback: CallbackQuery) -> None:
    db = SessionLocal()
    try:
        pending = get_pending_users(db)
        if not pending:
            kb = InlineKeyboardMarkup(inline_keyboard=_nav("adm:um"))
            await _safe_edit(callback, "<b>Pending approval</b>\n\nNo users pending.", kb)
            await callback.answer()
            return
        rows: List[List[InlineKeyboardButton]] = []
        for u in pending[:PAGE]:
            label = f"{u.telegram_id} · {u.first_name[:20]}"
            rows.append([InlineKeyboardButton(text=label, callback_data=f"adm:uv:{u.telegram_id}")])
        rows.extend(_nav("adm:um"))
        await _safe_edit(
            callback,
            f"<b>Pending approval</b> ({len(pending)})\n\nOpen a user:",
            InlineKeyboardMarkup(inline_keyboard=rows),
        )
    finally:
        db.close()
    await callback.answer()


@router.callback_query(F.data.startswith("adm:ul:"), F.from_user.id == config.admin_id)
async def cb_users_list(callback: CallbackQuery) -> None:
    offset = int(callback.data.split(":")[2])
    db = SessionLocal()
    try:
        total = count_users_total(db)
        users = list_users_paginated(db, offset, PAGE)
        lines = [f"<b>All users</b> ({total}) — page {offset // PAGE + 1}\n"]
        for u in users:
            sub = getattr(u, "subscription", None)
            lines.append(_user_summary_line(u, sub))
            lines.append("")
        user_open_rows = [
            [InlineKeyboardButton(text=f"👤 {u.telegram_id}", callback_data=f"adm:uv:{u.telegram_id}")]
            for u in users
        ]
        nav_rows: List[List[InlineKeyboardButton]] = []
        nr: List[InlineKeyboardButton] = []
        if offset > 0:
            nr.append(InlineKeyboardButton(text="⬅️ Prev", callback_data=f"adm:ul:{max(0, offset - PAGE)}"))
        if offset + PAGE < total:
            nr.append(InlineKeyboardButton(text="➡️ Next", callback_data=f"adm:ul:{offset + PAGE}"))
        if nr:
            nav_rows.append(nr)
        nav_rows.extend(_nav("adm:um"))
        await _safe_edit(
            callback,
            "\n".join(lines).strip() or "Empty.",
            InlineKeyboardMarkup(inline_keyboard=user_open_rows + nav_rows),
        )
    finally:
        db.close()
    await callback.answer()


@router.callback_query(F.data == "adm:ids", F.from_user.id == config.admin_id)
async def cb_id_search_start(callback: CallbackQuery) -> None:
    clear_id_search_buffer(callback.from_user.id)
    rows = [
        [
            InlineKeyboardButton(text=str(d), callback_data=f"adm:idn:{d}")
            for d in range(1, 4)
        ],
        [
            InlineKeyboardButton(text=str(d), callback_data=f"adm:idn:{d}")
            for d in range(4, 7)
        ],
        [
            InlineKeyboardButton(text=str(d), callback_data=f"adm:idn:{d}")
            for d in range(7, 10)
        ],
        [
            InlineKeyboardButton(text="0", callback_data="adm:idn:0"),
            InlineKeyboardButton(text="⌫", callback_data="adm:idb"),
            InlineKeyboardButton(text="CLR", callback_data="adm:idc"),
        ],
        [
            InlineKeyboardButton(text="🔍 Search", callback_data="adm:idgo"),
        ],
        *_nav("adm:um"),
    ]
    await _safe_edit(
        callback,
        "<b>Search by Telegram ID</b>\n\nCurrent: <i>(empty)</i>\nTap digits, then Search.",
        InlineKeyboardMarkup(inline_keyboard=rows),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm:idn:"), F.from_user.id == config.admin_id)
async def cb_id_digit(callback: CallbackQuery) -> None:
    d = callback.data.split(":")[2]
    buf = append_id_digit(callback.from_user.id, d)
    await _cb_id_refresh(callback, buf)
    await callback.answer()


@router.callback_query(F.data == "adm:idb", F.from_user.id == config.admin_id)
async def cb_id_bs(callback: CallbackQuery) -> None:
    buf = backspace_id_buffer(callback.from_user.id)
    await _cb_id_refresh(callback, buf)
    await callback.answer()


@router.callback_query(F.data == "adm:idc", F.from_user.id == config.admin_id)
async def cb_id_clr(callback: CallbackQuery) -> None:
    set_id_search_buffer(callback.from_user.id, "")
    await _cb_id_refresh(callback, "")
    await callback.answer()


async def _cb_id_refresh(callback: CallbackQuery, buf: str) -> None:
    rows = [
        [
            InlineKeyboardButton(text=str(d), callback_data=f"adm:idn:{d}")
            for d in range(1, 4)
        ],
        [
            InlineKeyboardButton(text=str(d), callback_data=f"adm:idn:{d}")
            for d in range(4, 7)
        ],
        [
            InlineKeyboardButton(text=str(d), callback_data=f"adm:idn:{d}")
            for d in range(7, 10)
        ],
        [
            InlineKeyboardButton(text="0", callback_data="adm:idn:0"),
            InlineKeyboardButton(text="⌫", callback_data="adm:idb"),
            InlineKeyboardButton(text="CLR", callback_data="adm:idc"),
        ],
        [
            InlineKeyboardButton(text="🔍 Search", callback_data="adm:idgo"),
        ],
        *_nav("adm:um"),
    ]
    disp = html.escape(buf) if buf else "<i>(empty)</i>"
    await _safe_edit(
        callback,
        f"<b>Search by Telegram ID</b>\n\nCurrent: <code>{disp}</code>\nTap digits, then Search.",
        InlineKeyboardMarkup(inline_keyboard=rows),
    )


@router.callback_query(F.data == "adm:idgo", F.from_user.id == config.admin_id)
async def cb_id_go(callback: CallbackQuery) -> None:
    buf = get_id_search_buffer(callback.from_user.id).strip()
    if not buf.isdigit():
        await callback.answer("Enter digits only", show_alert=True)
        return
    tid = int(buf)
    clear_id_search_buffer(callback.from_user.id)
    await _render_user_detail(callback, tid, back="adm:um")
    # _render_user_detail already answers


@router.callback_query(F.data.startswith("adm:uv:"), F.from_user.id == config.admin_id)
async def cb_user_view(callback: CallbackQuery) -> None:
    tid = int(callback.data.split(":")[2])
    await _render_user_detail(callback, tid, back="adm:um")


@router.callback_query(F.data.startswith("adm:ua:"), F.from_user.id == config.admin_id)
async def cb_user_approve(callback: CallbackQuery) -> None:
    tid = int(callback.data.split(":")[2])
    db = SessionLocal()
    try:
        u = get_user(db, tid)
        if not u or u.status != "PENDING_APPROVAL":
            await callback.answer("Cannot approve this user from current state.", show_alert=True)
            return
        update_user_status(db, tid, "APPROVED", approved_at=datetime.utcnow())
        from app.handlers import admin as admin_legacy

        await admin_legacy.send_approval_notice(tid)
    finally:
        db.close()
    await _render_user_detail(callback, tid, back="adm:um")


@router.callback_query(F.data.startswith("adm:rjm:"), F.from_user.id == config.admin_id)
async def cb_reject_menu(callback: CallbackQuery) -> None:
    tid = int(callback.data.split(":")[2])
    tid_s = str(tid)
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"adm:rjc:{tid_s}:{code}")]
        for code, label, _ in _REJECT_REASONS
    ]
    rows.extend(_nav(f"adm:uv:{tid_s}"))
    await _safe_edit(callback, "<b>Reject</b> — pick a reason:", InlineKeyboardMarkup(inline_keyboard=rows))
    await callback.answer()


@router.callback_query(F.data.startswith("adm:rjc:"), F.from_user.id == config.admin_id)
async def cb_user_reject(callback: CallbackQuery) -> None:
    parts = callback.data.split(":")
    if len(parts) != 4:
        await callback.answer()
        return
    tid = int(parts[2])
    code = parts[3]
    reason = next((t for c, _, t in _REJECT_REASONS if c == code), "Access denied")
    db = SessionLocal()
    try:
        if not reject_user(db, tid, reason):
            await callback.answer("Reject failed", show_alert=True)
            return
        from app.handlers import admin as admin_legacy

        try:
            await admin_legacy.send_rejection_notification(tid, reason)
        except Exception as e:
            logger.warning("reject notify: %s", e)
        if _bot and config.vip_group_id:
            try:
                await _bot.ban_chat_member(chat_id=config.vip_group_id, user_id=tid)
            except Exception as e:
                logger.warning("vip ban on reject: %s", e)
    finally:
        db.close()
    await _render_user_detail(callback, tid, back="adm:um")


@router.callback_query(F.data.startswith("adm:urx:"), F.from_user.id == config.admin_id)
async def cb_reset_ask(callback: CallbackQuery) -> None:
    tid = int(callback.data.split(":")[2])
    tid_s = str(tid)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⚠️ Confirm reset", callback_data=f"adm:urc:{tid_s}"),
            ],
            *_nav(f"adm:uv:{tid_s}"),
        ]
    )
    await _safe_edit(
        callback,
        "<b>Reset user</b>\n\nThis deletes the user row, subscription, payments, and questions.",
        kb,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm:urc:"), F.from_user.id == config.admin_id)
async def cb_reset_do(callback: CallbackQuery) -> None:
    tid = int(callback.data.split(":")[2])
    db = SessionLocal()
    try:
        ok = reset_user_completely(db, tid)
    finally:
        db.close()
    await callback.answer("Reset done" if ok else "Reset failed", show_alert=True)
    await _safe_edit(
        callback,
        f"User <code>{tid}</code> removed from database." if ok else "Reset failed.",
        InlineKeyboardMarkup(inline_keyboard=_nav("adm:um")),
    )


@router.callback_query(F.data.startswith("adm:ue:"), F.from_user.id == config.admin_id)
async def cb_expire_sub(callback: CallbackQuery) -> None:
    tid = int(callback.data.split(":")[2])
    db = SessionLocal()
    try:
        svc = SubscriptionService(db)
        ok = svc.force_expire_subscription(tid, admin_user_id=callback.from_user.id)
    finally:
        db.close()
    await _render_user_detail(callback, tid, back="adm:um")


@router.callback_query(F.data.startswith("adm:ug:"), F.from_user.id == config.admin_id)
async def cb_grace(callback: CallbackQuery) -> None:
    tid = int(callback.data.split(":")[2])
    db = SessionLocal()
    try:
        svc = SubscriptionService(db)
        ok = svc.admin_move_to_grace(tid, admin_user_id=callback.from_user.id, grace_days=3)
        if ok and _bot:
            await notify_vip_invite_if_eligible(_bot, tid)
    finally:
        db.close()
    await _render_user_detail(callback, tid, back="adm:um")


@router.callback_query(F.data.startswith("adm:uac:"), F.from_user.id == config.admin_id)
async def cb_activate(callback: CallbackQuery) -> None:
    tid = int(callback.data.split(":")[2])
    db = SessionLocal()
    try:
        svc = SubscriptionService(db)
        ok = svc.admin_activate_subscription(tid, admin_user_id=callback.from_user.id)
        if ok and _bot:
            await notify_vip_invite_if_eligible(_bot, tid)
    finally:
        db.close()
    await _render_user_detail(callback, tid, back="adm:um")


@router.callback_query(F.data.startswith("adm:uvp:"), F.from_user.id == config.admin_id)
async def cb_vip_remove(callback: CallbackQuery) -> None:
    tid = int(callback.data.split(":")[2])
    if not _bot or not config.vip_group_id:
        await callback.answer("VIP group not configured", show_alert=True)
        return
    try:
        await _bot.ban_chat_member(chat_id=config.vip_group_id, user_id=tid)
    except TelegramBadRequest as e:
        await callback.answer(f"Telegram: {e}", show_alert=True)
        return
    except Exception as e:
        await callback.answer(str(e)[:200], show_alert=True)
        return
    await _render_user_detail(callback, tid, back="adm:um")


# --- Questions ---


@router.callback_query(F.data == "adm:qm", F.from_user.id == config.admin_id)
async def cb_q_menu(callback: CallbackQuery) -> None:
    await _safe_edit(callback, "<b>Questions</b>\n\nSelect:", _kb_questions_menu())
    await callback.answer()


def _question_list_rows(
    qrows: List[Question], offset: int, total: int, prefix: str, back: str
) -> InlineKeyboardMarkup:
    ik: List[List[InlineKeyboardButton]] = []
    for q in qrows:
        short = (q.question_text or "")[:40].replace("\n", " ")
        label = f"#{q.id} · {short}…" if len(q.question_text or "") > 40 else f"#{q.id} · {short}"
        label = label[:58]
        ik.append([InlineKeyboardButton(text=label, callback_data=f"adm:qd:{q.id}")])
    nav: List[InlineKeyboardButton] = []
    if offset > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"{prefix}:{max(0, offset - PAGE)}"))
    if offset + PAGE < total:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"{prefix}:{offset + PAGE}"))
    if nav:
        ik.append(nav)
    ik.extend(_nav(back))
    return InlineKeyboardMarkup(inline_keyboard=ik)


@router.callback_query(F.data.startswith("adm:qp:"), F.from_user.id == config.admin_id)
async def cb_q_pending(callback: CallbackQuery) -> None:
    offset = int(callback.data.split(":")[2])
    db = SessionLocal()
    try:
        rows, total = list_questions_paginated(db, status="PENDING", offset=offset, limit=PAGE)
        text = f"<b>Pending questions</b> ({total})\n"
        await _safe_edit(callback, text, _question_list_rows(rows, offset, total, "adm:qp", "adm:qm"))
    finally:
        db.close()
    await callback.answer()


@router.callback_query(F.data.startswith("adm:qh:"), F.from_user.id == config.admin_id)
async def cb_q_hist(callback: CallbackQuery) -> None:
    offset = int(callback.data.split(":")[2])
    db = SessionLocal()
    try:
        rows, total = list_questions_paginated(db, status=None, offset=offset, limit=PAGE)
        text = f"<b>All questions</b> ({total})\n"
        await _safe_edit(callback, text, _question_list_rows(rows, offset, total, "adm:qh", "adm:qm"))
    finally:
        db.close()
    await callback.answer()


@router.callback_query(F.data.startswith("adm:qd:"), F.from_user.id == config.admin_id)
async def cb_q_detail(callback: CallbackQuery) -> None:
    qid = int(callback.data.split(":")[2])
    db = SessionLocal()
    try:
        q = get_question_by_id(db, qid)
        if not q:
            await callback.answer("Not found", show_alert=True)
            return
        u = get_user(db, q.user_id)
        un = html.escape(u.username) if u and u.username else "—"
        text = (
            f"<b>Question #{q.id}</b>\n"
            f"User: <code>{q.user_id}</code> (@{un})\n"
            f"Status: <b>{html.escape(q.status)}</b>\n"
            f"Created: {q.created_at}\n\n"
            f"<b>Text</b>\n{html.escape(q.question_text or '')}\n"
        )
        if q.admin_reply_text:
            text += f"\n<b>Admin reply</b>\n{html.escape(q.admin_reply_text)}\n"
        rows: List[List[InlineKeyboardButton]] = []
        if q.status == "PENDING":
            rows.append(
                [
                    InlineKeyboardButton(text="✍️ Compose reply", callback_data=f"adm:qco:{q.id}"),
                ]
            )
        rows.extend(_nav("adm:qp:0"))
        await _safe_edit(callback, text, InlineKeyboardMarkup(inline_keyboard=rows))
    finally:
        db.close()
    await callback.answer()


@router.callback_query(F.data.startswith("adm:qco:"), F.from_user.id == config.admin_id)
async def cb_q_compose(callback: CallbackQuery) -> None:
    qid = int(callback.data.split(":")[2])
    set_pending_answer(callback.from_user.id, qid)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel compose", callback_data="adm:qcc")],
            *_nav(f"adm:qd:{qid}"),
        ]
    )
    await _safe_edit(
        callback,
        "<b>Compose reply</b>\n\n"
        "Send your <b>next text message</b> in this chat (not a command). "
        "It will be delivered to the user and the question marked answered.\n\n"
        "<i>This is the only step that uses a normal message, after you pressed the button.</i>",
        kb,
    )
    await callback.answer()


@router.callback_query(F.data == "adm:qcc", F.from_user.id == config.admin_id)
async def cb_q_compose_cancel(callback: CallbackQuery) -> None:
    clear_pending_answer(callback.from_user.id)
    await _safe_edit(
        callback,
        "Compose cancelled.",
        InlineKeyboardMarkup(inline_keyboard=_nav("adm:qm")),
    )
    await callback.answer()


class PendingAnswerFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        return _is_admin(message.from_user.id) and get_pending_answer(message.from_user.id) is not None


@router.message(PendingAnswerFilter(), F.text, ~F.reply_to_message)
async def admin_compose_answer(message: Message) -> None:
    qid = get_pending_answer(message.from_user.id)
    clear_pending_answer(message.from_user.id)
    if not qid or not _bot:
        return
    text = message.text or ""
    db = SessionLocal()
    try:
        q = get_question_by_id(db, qid)
        if not q or not q.is_pending():
            await message.answer("Question is no longer pending.")
            return
        reply_to_user = (
            f"📨 Admin response\n\n"
            f"Your question:\n{q.question_text}\n\n"
            f"Response:\n{text}\n"
        )
        try:
            await _bot.send_message(chat_id=q.user_id, text=reply_to_user)
        except TelegramForbiddenError:
            if mark_question_failed_delivery(db, qid, text):
                await message.answer("User blocked the bot. Saved as FAILED_DELIVERY.")
            return
        except Exception as e:
            await message.answer(f"Send failed: {e}")
            return
        if not answer_question(db, qid, text):
            await message.answer("Sent to user but DB update failed.")
            return
        await message.answer(f"✅ Answered question #{qid}")
    finally:
        db.close()


# --- Subscriptions ---


@router.callback_query(F.data == "adm:sm", F.from_user.id == config.admin_id)
async def cb_sub_menu(callback: CallbackQuery) -> None:
    await _safe_edit(
        callback,
        "<b>Subscriptions &amp; Payment</b>\n\nSelect:",
        _kb_subscriptions_menu(),
    )
    await callback.answer()


def _fmt_payment(p: Payment) -> str:
    return (
        f"<code>#{p.id}</code> user <code>{p.user_id}</code> "
        f"<b>{html.escape(str(p.payment_status))}</b> {p.amount} {html.escape(p.currency)} "
        f"{html.escape(str(p.provider))}"
    )


def _fmt_sub(s: Subscription) -> str:
    return (
        f"<code>#{s.id}</code> user <code>{s.user_id}</code> "
        f"<b>{html.escape(str(s.status))}</b> {html.escape(str(s.plan_name))}"
    )


@router.callback_query(F.data.startswith("adm:sl:"), F.from_user.id == config.admin_id)
async def cb_sub_list(callback: CallbackQuery) -> None:
    offset = int(callback.data.split(":")[2])
    db = SessionLocal()
    try:
        rows, total = list_subscriptions_paginated(db, offset, PAGE)
        lines = [f"<b>Subscriptions</b> ({total})\n"] + [_fmt_sub(s) for s in rows]
        ik: List[List[InlineKeyboardButton]] = []
        nav: List[InlineKeyboardButton] = []
        if offset > 0:
            nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"adm:sl:{max(0, offset - PAGE)}"))
        if offset + PAGE < total:
            nav.append(InlineKeyboardButton(text="➡️", callback_data=f"adm:sl:{offset + PAGE}"))
        if nav:
            ik.append(nav)
        ik.extend(_nav("adm:sm"))
        await _safe_edit(callback, "\n".join(lines), InlineKeyboardMarkup(inline_keyboard=ik))
    finally:
        db.close()
    await callback.answer()


@router.callback_query(F.data.startswith("adm:pf:"), F.from_user.id == config.admin_id)
async def cb_pay_recent(callback: CallbackQuery) -> None:
    offset = int(callback.data.split(":")[2])
    db = SessionLocal()
    try:
        rows, total = list_payments_paginated(db, offset, PAGE)
        lines = [f"<b>Recent payments</b> ({total})\n"] + [_fmt_payment(p) for p in rows]
        ik: List[List[InlineKeyboardButton]] = []
        nav: List[InlineKeyboardButton] = []
        if offset > 0:
            nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"adm:pf:{max(0, offset - PAGE)}"))
        if offset + PAGE < total:
            nav.append(InlineKeyboardButton(text="➡️", callback_data=f"adm:pf:{offset + PAGE}"))
        if nav:
            ik.append(nav)
        ik.extend(_nav("adm:sm"))
        await _safe_edit(callback, "\n".join(lines), InlineKeyboardMarkup(inline_keyboard=ik))
    finally:
        db.close()
    await callback.answer()


@router.callback_query(F.data.startswith("adm:wl:"), F.from_user.id == config.admin_id)
async def cb_webhook_log(callback: CallbackQuery) -> None:
    offset = int(callback.data.split(":")[2])
    db = SessionLocal()
    try:
        rows, total = list_webhook_logs_paginated(db, offset, PAGE)
        lines = [f"<b>Webhook / event log</b> ({total})\n"]
        for r in rows:
            ok = "✅" if r.success else "❌"
            lines.append(
                f"{ok} <code>#{r.id}</code> {html.escape(str(r.created_at))}\n"
                f"  user={r.user_id} type={html.escape(str(r.event_type))}\n"
                f"  {html.escape((r.detail or '')[:120])}"
            )
        ik: List[List[InlineKeyboardButton]] = []
        nav: List[InlineKeyboardButton] = []
        if offset > 0:
            nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"adm:wl:{max(0, offset - PAGE)}"))
        if offset + PAGE < total:
            nav.append(InlineKeyboardButton(text="➡️", callback_data=f"adm:wl:{offset + PAGE}"))
        if nav:
            ik.append(nav)
        ik.extend(_nav("adm:sm"))
        await _safe_edit(callback, "\n\n".join(lines), InlineKeyboardMarkup(inline_keyboard=ik))
    finally:
        db.close()
    await callback.answer()


@router.callback_query(F.data.startswith("adm:pp:"), F.from_user.id == config.admin_id)
async def cb_pay_per_user(callback: CallbackQuery) -> None:
    offset = int(callback.data.split(":")[2])
    db = SessionLocal()
    try:
        total = count_distinct_payment_users(db)
        rows = list_latest_payment_per_user_page(db, offset, PAGE)
        lines = [f"<b>Latest payment per user</b> ({total} users)\n"] + [_fmt_payment(p) for p in rows]
        ik: List[List[InlineKeyboardButton]] = []
        nav: List[InlineKeyboardButton] = []
        if offset > 0:
            nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"adm:pp:{max(0, offset - PAGE)}"))
        if offset + PAGE < total:
            nav.append(InlineKeyboardButton(text="➡️", callback_data=f"adm:pp:{offset + PAGE}"))
        if nav:
            ik.append(nav)
        ik.extend(_nav("adm:sm"))
        await _safe_edit(callback, "\n".join(lines), InlineKeyboardMarkup(inline_keyboard=ik))
    finally:
        db.close()
    await callback.answer()


# --- System ---


@router.callback_query(F.data == "adm:sy", F.from_user.id == config.admin_id)
async def cb_system(callback: CallbackQuery) -> None:
    await _safe_edit(callback, _system_settings_text(), _kb_system_menu())
    await callback.answer()
