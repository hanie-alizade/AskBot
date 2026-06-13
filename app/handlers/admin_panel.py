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
from aiogram.filters import BaseFilter, Command, CommandStart
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
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
    count_questions,
    count_users_by_sub_status,
    count_users_total,
    get_all_users,
    get_pending_users,
    get_question_by_id,
    get_user,
    get_user_count_by_status,
    list_users_by_sub_status,
    list_users_by_sub_status_paginated,
    list_latest_payment_per_user_page,
    list_payments_paginated,
    list_questions,
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
from database.models_subscription import Payment, Subscription, SubscriptionStatus
from services.user_segment import user_type_admin_label
from services.admin_panel_state import (
    clear_awaiting_id_search,
    clear_pending_answer,
    get_pending_answer,
    is_awaiting_id_search,
    set_awaiting_id_search,
    set_pending_answer,
)
from services.entitlement_policy import EntitlementPolicy
from services.excel_export import export_questions_xlsx, export_users_xlsx, safe_remove
from services.i18n.admin import (
    ADMIN_LANGUAGE_LABELS,
    ADMIN_SUPPORTED_LANGUAGES,
    get_admin_language,
    get_admin_text,
    set_admin_language,
)
from services.subscription_readout import build_subscription_view, format_admin_subscription_status_message
from services.subscription_service import SubscriptionService
from services.vip_invite import notify_vip_invite_if_eligible

logger = logging.getLogger(__name__)

router = Router(name="admin_panel")

_bot: Optional[Bot] = None
PAGE = 6


def _t(key: str, **kwargs) -> str:
    """Localize an admin string in the currently-selected admin language."""
    return get_admin_text(key, None, **kwargs)


# Canonical section ids (stable identity used for dispatch) -> catalog key for
# the localized reply-keyboard label.
_SECTION_LABEL_KEYS = {
    "user_management": "menu.user_management",
    "questions": "menu.questions",
    "subscriptions": "menu.subscriptions",
    "system": "menu.system",
}


def _section_label_to_id() -> dict:
    """Localized section label (in EVERY admin language) -> canonical section id.

    Built across all languages so a reply keyboard rendered before a language
    switch still resolves to the right section afterwards — functionality is
    unchanged regardless of the active language.
    """
    mapping: dict = {}
    for sid, key in _SECTION_LABEL_KEYS.items():
        for lang in ADMIN_SUPPORTED_LANGUAGES:
            mapping[get_admin_text(key, lang)] = sid
    return mapping


# (code, label_key, user-facing detail). The detail is sent to the rejected
# user via their OWN localized flow, so it stays as the stored English reason;
# only the admin-facing button label_key is localized here.
_REJECT_REASONS = (
    ("0", "rj.reason_standards", "Does not meet access standards."),
    ("1", "rj.reason_spam", "Spam or automated behaviour."),
    ("2", "rj.reason_other", "Access denied."),
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
                KeyboardButton(text=_t("menu.user_management")),
                KeyboardButton(text=_t("menu.questions")),
            ],
            [
                KeyboardButton(text=_t("menu.subscriptions")),
                KeyboardButton(text=_t("menu.system")),
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
                InlineKeyboardButton(text=_t("menu.user_management"), callback_data="adm:um"),
                InlineKeyboardButton(text=_t("menu.questions"), callback_data="adm:qm"),
            ],
            [
                InlineKeyboardButton(text=_t("menu.subscriptions"), callback_data="adm:sm"),
                InlineKeyboardButton(text=_t("menu.system"), callback_data="adm:sy"),
            ],
        ]
    )


# --------------------------------------------------------------------------- #
# User Management dashboard
#
# Subscription-status groupings power both the summary counters and the
# filtered list shortcuts (callback adm:uf:<filter>:<offset>). Defined once so
# the counts shown on a card always match the list that card opens.
# --------------------------------------------------------------------------- #
_SUB_ACTIVE_STATUSES = (SubscriptionStatus.ACTIVE.value,)
_SUB_GRACE_STATUSES = (SubscriptionStatus.GRACE.value, SubscriptionStatus.PAST_DUE.value)
_SUB_EXPIRED_STATUSES = (SubscriptionStatus.EXPIRED.value, SubscriptionStatus.CANCELLED.value)

# filter key -> (screen title, subscription statuses) for the shortcut lists.
# filter key -> (title catalog key, subscription statuses). Title is resolved
# at render time so it follows the active admin language.
_USER_FILTERS = {
    "active": ("filter.active_title", _SUB_ACTIVE_STATUSES),
    "expired": ("filter.expired_title", _SUB_EXPIRED_STATUSES),
    "grace": ("filter.grace_title", _SUB_GRACE_STATUSES),
}

# Excel export datasets shown on the User Management screen.
# key -> (button label key, dataset name key, dashboard count field, filename prefix)
# A button is rendered only when its count field is > 0, so empty datasets never
# get an export button. Order here is the on-screen order.
_EXPORT_SPECS = {
    "active": ("export.btn_active", "export.name_active", "active", "active_users"),
    "expired": ("export.btn_expired", "export.name_expired", "expired", "expired_users"),
    "grace": ("export.btn_grace", "export.name_grace", "grace", "grace_users"),
    "pending": ("export.btn_pending", "export.name_pending", "pending", "pending_users"),
    "all": ("export.btn_all", "export.name_all", "total", "all_users"),
}
_EXPORT_ORDER = ("active", "expired", "grace", "pending", "all")


def _export_rows(c: dict) -> List[List[InlineKeyboardButton]]:
    """Conditional export buttons (only datasets with count > 0), packed 2/row."""
    available = [
        InlineKeyboardButton(text=_t(_EXPORT_SPECS[k][0]), callback_data=f"adm:exp:{k}")
        for k in _EXPORT_ORDER
        if c.get(_EXPORT_SPECS[k][2], 0) > 0
    ]
    return [available[i:i + 2] for i in range(0, len(available), 2)]


def _export_dataset(db, key: str) -> List[User]:
    """Resolve the exact User rows for an export key (matches the dashboard card)."""
    if key == "all":
        return get_all_users(db)
    if key == "pending":
        return get_pending_users(db)
    statuses = {
        "active": _SUB_ACTIVE_STATUSES,
        "expired": _SUB_EXPIRED_STATUSES,
        "grace": _SUB_GRACE_STATUSES,
    }.get(key)
    if statuses is None:
        return []
    return list_users_by_sub_status(db, statuses)


def _users_dashboard_counts(db) -> dict:
    """Backend counters for the dashboard header + card subtitles."""
    return {
        "total": count_users_total(db),
        "active": count_users_by_sub_status(db, _SUB_ACTIVE_STATUSES),
        "grace": count_users_by_sub_status(db, _SUB_GRACE_STATUSES),
        "expired": count_users_by_sub_status(db, _SUB_EXPIRED_STATUSES),
        "pending": get_user_count_by_status(db).get("pending_approval", 0),
    }


def _users_dashboard_text(c: dict) -> str:
    """SaaS-style summary header answering: how many active/expired/pending?"""
    text = (
        f"<b>{_t('um.title')}</b>\n\n"
        f"{_UI_SEPARATOR}\n\n"
        f"{_t('um.total', total=c['total'])}\n\n"
        f"{_t('um.line_active_expired', active=c['active'], expired=c['expired'])}\n"
        f"{_t('um.line_grace_pending', grace=c['grace'], pending=c['pending'])}\n\n"
        f"{_t('um.hint')}\n\n"
        f"{_UI_SEPARATOR}"
    )
    # Export section header (only when there is at least one exportable dataset).
    if c.get("total", 0) > 0:
        text += f"\n\n{_t('export.section_title')}"
    return text


def _kb_users_dashboard(c: dict) -> InlineKeyboardMarkup:
    """Card-grid keyboard. Counts act as each card's subtitle.

    Layout (cards stack to 1-column automatically on narrow phones):
      [🟢 Active]   [🔴 Expired]      ← primary membership states
      [⏳ Grace]    [📝 Pending]      ← grace + attention queue
      [👥 All Users]                  ← neutral baseline
      [🔍  Search User  🔍]           ← distinct full-width "search bar"
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=_t("um.card_active", n=c['active']), callback_data="adm:uf:active:0"),
            InlineKeyboardButton(text=_t("um.card_expired", n=c['expired']), callback_data="adm:uf:expired:0"),
        ],
        [
            InlineKeyboardButton(text=_t("um.card_grace", n=c['grace']), callback_data="adm:uf:grace:0"),
            InlineKeyboardButton(text=_t("um.card_pending", n=c['pending']), callback_data="adm:up"),
        ],
        [
            InlineKeyboardButton(text=_t("um.card_all", n=c['total']), callback_data="adm:ul:0"),
        ],
        [
            InlineKeyboardButton(text=_t("um.card_search"), callback_data="adm:ids"),
        ],
        *_export_rows(c),
        *_nav("adm:h"),
    ])


def _build_users_dashboard(db) -> tuple:
    """(text, keyboard) for the User Management home — one source of truth."""
    counts = _users_dashboard_counts(db)
    return _users_dashboard_text(counts), _kb_users_dashboard(counts)


def _questions_counts(db) -> dict:
    """Counts powering the Questions menu labels + export-button visibility."""
    return {
        "pending": count_questions(db, status="PENDING"),
        "all": count_questions(db),
    }


def _kb_questions_menu(counts: dict) -> InlineKeyboardMarkup:
    """Two-column rows: [dataset (count)] [optional 📤 export].

    The export button on a row is rendered ONLY when that dataset has records,
    so an empty dataset shows just its (0) label and no export action. Proper
    Telegram rows are used for alignment — never spacing.
    """
    pending = counts.get("pending", 0)
    total = counts.get("all", 0)

    row_pending = [InlineKeyboardButton(text=_t("qm.btn_pending", n=pending), callback_data="adm:qp:0")]
    if pending > 0:
        row_pending.append(
            InlineKeyboardButton(text=_t("qm.btn_export_pending"), callback_data="adm:qexp:pending")
        )

    row_all = [InlineKeyboardButton(text=_t("qm.btn_all", n=total), callback_data="adm:qh:0")]
    if total > 0:
        row_all.append(
            InlineKeyboardButton(text=_t("qm.btn_export_all"), callback_data="adm:qexp:all")
        )

    return InlineKeyboardMarkup(inline_keyboard=[row_pending, row_all, *_nav("adm:h")])


def _kb_subscriptions_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=_t("sm.btn_subscriptions"), callback_data="adm:sl:0")],
            [InlineKeyboardButton(text=_t("sm.btn_recent_payments"), callback_data="adm:pf:0")],
            [InlineKeyboardButton(text=_t("sm.btn_webhook_log"), callback_data="adm:wl:0")],
            [InlineKeyboardButton(text=_t("sm.btn_last_payment"), callback_data="adm:pp:0")],
            *_nav("adm:h"),
        ]
    )


def _system_settings_text() -> str:
    # Env-var NAMES (e.g. VIP_GROUP_ID) are config identifiers, not prose, so
    # they stay literal; only the surrounding prose labels are localized.
    return "\n".join(
        [
            f"<b>{_t('sys.title')}</b>",
            "",
            _UI_SEPARATOR,
            "",
            _t("sys.desc"),
            "",
            _UI_SEPARATOR,
            "",
            f"VIP_GROUP_ID: <code>{config.vip_group_id}</code>",
            f"SUBSCRIPTION_ENFORCEMENT_ENABLED: <b>{config.subscription_enforcement_enabled}</b>",
            f"SUBSCRIPTION_GRANDFATHER_ENABLED: <b>{config.subscription_grandfather_enabled}</b>",
            f"MOCK_PAYMENT_ENABLED: <b>{config.mock_payment_enabled}</b>",
            f"MOCK_SUBSCRIPTION_ACTIVE_BY_DEFAULT: <b>{config.mock_subscription_active_by_default}</b>",
            f"{_t('sys.lbl_vip_lapse')} <code>{config.vip_subscription_lapse_removal_delay_seconds}</code>",
            f"{_t('sys.lbl_vip_sync')} <code>{config.vip_membership_sync_interval_seconds}</code>",
            f"{_t('sys.lbl_stripe_mode')} <b>{config.stripe_mode_name}</b> (live={config.stripe_live_mode})",
            f"{_t('sys.lbl_stripe_key_set')} <b>{bool(config.stripe_secret_key)}</b>",
            f"{_t('sys.lbl_webhook_secret_set')} <b>{bool(config.stripe_webhook_secret)}</b>",
        ]
    )


def _kb_system_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=_t("sys.btn_refresh"), callback_data="adm:sy")],
            [InlineKeyboardButton(text=_t("sys.btn_language"), callback_data="adm:lang")],
            *_nav("adm:h"),
        ]
    )


def _language_text() -> str:
    current = ADMIN_LANGUAGE_LABELS.get(get_admin_language(), get_admin_language())
    return (
        f"<b>{_t('lang.title')}</b>\n\n"
        f"{_UI_SEPARATOR}\n\n"
        f"{_t('lang.desc')}\n\n"
        f"{_t('lang.current', label=current)}\n\n"
        f"{_t('lang.prompt')}\n\n"
        f"{_UI_SEPARATOR}"
    )


def _kb_language_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=ADMIN_LANGUAGE_LABELS["en"], callback_data="adm:setlang:en")],
            [InlineKeyboardButton(text=ADMIN_LANGUAGE_LABELS["es"], callback_data="adm:setlang:es")],
            *_nav("adm:sy"),
        ]
    )


def _nav(back_cb: Optional[str]) -> List[List[InlineKeyboardButton]]:
    row: List[InlineKeyboardButton] = []
    if back_cb:
        row.append(InlineKeyboardButton(text=_t("nav.back"), callback_data=back_cb))
    row.append(InlineKeyboardButton(text=_t("nav.home"), callback_data="adm:h"))
    return [row]


# Visual separator and standardized empty-state template used across every
# admin panel screen so empty/zero-result pages don't collapse into tiny
# one-line messages.
_UI_SEPARATOR = "━━━━━━━━━━━━━━━━━━━━"


def _empty_state(title: str, body: str, hint: Optional[str] = None) -> str:
    """Render an empty-result page consistently.

    title : icon + 3+ word heading (e.g. "📋 Pending Approval Queue")
    body  : the "nothing here" sentence (full sentence, ends with period)
    hint  : optional second paragraph (e.g. "Approve requests will appear here.")
    """
    lines = [f"<b>{title}</b>", "", _UI_SEPARATOR, "", body]
    if hint:
        lines.extend(["", hint])
    lines.extend(["", _UI_SEPARATOR])
    return "\n".join(lines)


def _section_header(title: str, description: str, prompt: Optional[str] = None) -> str:
    """Render a section / sub-menu screen consistently.

    Mirrors `_empty_state` so every full-screen body in the admin panel has
    the same visual rhythm: icon + 3+ word title, separator, descriptive
    paragraph, action prompt, separator.
    """
    if prompt is None:
        prompt = _t("common.choose_option")
    return (
        f"<b>{title}</b>\n\n"
        f"{_UI_SEPARATOR}\n\n"
        f"{description}\n\n"
        f"{prompt}\n\n"
        f"{_UI_SEPARATOR}"
    )


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
    return _t(
        "ul.summary_line",
        tid=u.telegram_id,
        name=html.escape(u.first_name[:24]),
        un=un,
        status=html.escape(u.status),
        sub=html.escape(sub_s),
        plan=plan,
        used=u.questions_used,
        limit=u.question_limit,
    )


def _kb_user_actions(tid: int, u: User) -> List[List[InlineKeyboardButton]]:
    rows: List[List[InlineKeyboardButton]] = []
    tid_s = str(tid)
    if u.status == "PENDING_APPROVAL":
        rows.append(
            [
                InlineKeyboardButton(text=_t("btn.approve"), callback_data=f"adm:ua:{tid_s}"),
                InlineKeyboardButton(text=_t("btn.reject"), callback_data=f"adm:rjm:{tid_s}"),
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(text=_t("btn.reset_user"), callback_data=f"adm:urx:{tid_s}"),
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(text=_t("btn.expire_sub"), callback_data=f"adm:ue:{tid_s}"),
            InlineKeyboardButton(text=_t("btn.grace"), callback_data=f"adm:ug:{tid_s}"),
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(text=_t("btn.activate_sub"), callback_data=f"adm:uac:{tid_s}"),
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(text=_t("btn.remove_vip"), callback_data=f"adm:uvp:{tid_s}"),
        ]
    )
    rows.extend(_nav("adm:um"))
    return rows


async def _render_user_detail(callback: CallbackQuery, tid: int, *, back: str) -> None:
    db = SessionLocal()
    try:
        u = get_user(db, tid)
        if not u:
            # Popup keeps the admin on the menu/list they came from instead of
            # navigating them to a one-line "not found" page.
            await callback.answer(
                _t("ud.not_found_popup", tid=tid),
                show_alert=True,
            )
            return
        sub = getattr(u, "subscription", None)
        svc = SubscriptionService(db)
        snap = svc.get_subscription_snapshot(tid, user=u)
        expl = EntitlementPolicy().explain_question_entitlement(u)
        vm = build_subscription_view(snap, expl)
        sub_block = format_admin_subscription_status_message(tid, vm, lang=get_admin_language())
        text = _t(
            "ud.block",
            tid=tid,
            name=html.escape(u.first_name),
            username=("@" + html.escape(u.username)) if u.username else "—",
            approval=html.escape(u.status),
            category=html.escape(user_type_admin_label(u)),
            used=u.questions_used,
            limit=u.question_limit,
            sub_block=html.escape(sub_block),
        )
        kb = InlineKeyboardMarkup(inline_keyboard=_kb_user_actions(tid, u))
        await _safe_edit(callback, text, kb)
    finally:
        db.close()
    await callback.answer()


@router.message(CommandStart(), F.from_user.id == config.admin_id)
async def admin_start(message: Message) -> None:
    clear_pending_answer(message.from_user.id)
    clear_awaiting_id_search(message.from_user.id)
    await message.answer(
        f"{_t('start.title')}\n\n{_t('start.body')}",
        reply_markup=_admin_reply_keyboard(),
        parse_mode="HTML",
    )
    await message.answer(
        _section_header(
            _t("home.title"),
            _t("home.desc"),
            _t("home.prompt"),
        ),
        reply_markup=_kb_main(),
        parse_mode="HTML",
    )


class AdminSectionReplyFilter(BaseFilter):
    """Reply-keyboard section opener; ignored while composing a question answer."""

    async def __call__(self, message: Message) -> bool:
        if not message.from_user or message.from_user.id != config.admin_id:
            return False
        if not message.text or message.text not in _section_label_to_id():
            return False
        return get_pending_answer(message.from_user.id) is None


@router.message(AdminSectionReplyFilter())
async def admin_reply_section(message: Message) -> None:
    clear_pending_answer(message.from_user.id)
    clear_awaiting_id_search(message.from_user.id)
    section_id = _section_label_to_id().get(message.text or "")
    if section_id == "user_management":
        db = SessionLocal()
        try:
            text, kb = _build_users_dashboard(db)
        finally:
            db.close()
        await message.answer(text, reply_markup=kb, parse_mode="HTML")
    elif section_id == "questions":
        db = SessionLocal()
        try:
            kb = _kb_questions_menu(_questions_counts(db))
        finally:
            db.close()
        await message.answer(
            _section_header(
                _t("qm.title"),
                _t("qm.desc"),
            ),
            reply_markup=kb,
            parse_mode="HTML",
        )
    elif section_id == "subscriptions":
        await message.answer(
            _section_header(
                _t("sm.title"),
                _t("sm.desc"),
            ),
            reply_markup=_kb_subscriptions_menu(),
            parse_mode="HTML",
        )
    elif section_id == "system":
        await message.answer(
            _system_settings_text(),
            reply_markup=_kb_system_menu(),
            parse_mode="HTML",
        )


@router.callback_query(F.data == "adm:h", F.from_user.id == config.admin_id)
async def cb_home(callback: CallbackQuery) -> None:
    clear_pending_answer(callback.from_user.id)
    clear_awaiting_id_search(callback.from_user.id)
    await _safe_edit(
        callback,
        _section_header(
            _t("home.title"),
            _t("home.desc"),
            _t("home.prompt"),
        ),
        _kb_main(),
    )
    await callback.answer()


@router.callback_query(F.data == "adm:um", F.from_user.id == config.admin_id)
async def cb_users_menu(callback: CallbackQuery) -> None:
    db = SessionLocal()
    try:
        text, kb = _build_users_dashboard(db)
    finally:
        db.close()
    await _safe_edit(callback, text, kb)
    await callback.answer()


@router.callback_query(F.data == "adm:up", F.from_user.id == config.admin_id)
async def cb_users_pending(callback: CallbackQuery) -> None:
    db = SessionLocal()
    try:
        pending = get_pending_users(db)
        if not pending:
            kb = InlineKeyboardMarkup(inline_keyboard=_nav("adm:um"))
            await _safe_edit(
                callback,
                _empty_state(
                    _t("up.empty_title"),
                    _t("up.empty_body"),
                    _t("up.empty_hint"),
                ),
                kb,
            )
            await callback.answer()
            return
        rows: List[List[InlineKeyboardButton]] = []
        for u in pending[:PAGE]:
            label = f"{u.telegram_id} · {u.first_name[:20]}"
            rows.append([InlineKeyboardButton(text=label, callback_data=f"adm:uv:{u.telegram_id}")])
        rows.extend(_nav("adm:um"))
        await _safe_edit(
            callback,
            _t("up.header", n=len(pending)),
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
        if total == 0:
            await _safe_edit(
                callback,
                _empty_state(
                    _t("ul.empty_title"),
                    _t("ul.empty_body"),
                    _t("ul.empty_hint"),
                ),
                InlineKeyboardMarkup(inline_keyboard=_nav("adm:um")),
            )
            await callback.answer()
            return
        lines = [_t("ul.header", total=total, page=offset // PAGE + 1) + "\n"]
        for u in users:
            sub = getattr(u, "subscription", None)
            lines.append(_user_summary_line(u, sub))
            lines.append("")
        user_open_rows = [
            [InlineKeyboardButton(text=_t("btn.open_user", tid=u.telegram_id), callback_data=f"adm:uv:{u.telegram_id}")]
            for u in users
        ]
        nav_rows: List[List[InlineKeyboardButton]] = []
        nr: List[InlineKeyboardButton] = []
        if offset > 0:
            nr.append(InlineKeyboardButton(text=_t("pg.prev"), callback_data=f"adm:ul:{max(0, offset - PAGE)}"))
        if offset + PAGE < total:
            nr.append(InlineKeyboardButton(text=_t("pg.next"), callback_data=f"adm:ul:{offset + PAGE}"))
        if nr:
            nav_rows.append(nr)
        nav_rows.extend(_nav("adm:um"))
        await _safe_edit(
            callback,
            "\n".join(lines).strip(),
            InlineKeyboardMarkup(inline_keyboard=user_open_rows + nav_rows),
        )
    finally:
        db.close()
    await callback.answer()


@router.callback_query(F.data.startswith("adm:uf:"), F.from_user.id == config.admin_id)
async def cb_users_filtered(callback: CallbackQuery) -> None:
    """Paginated list for a dashboard shortcut: adm:uf:<filter>:<offset>.

    Reuses the All-Users rendering style; `filter` selects the subscription
    status group (active / expired / grace) defined in _USER_FILTERS.
    """
    parts = callback.data.split(":")  # ["adm", "uf", <filter>, <offset>]
    fkey = parts[2] if len(parts) > 2 else ""
    offset = int(parts[3]) if len(parts) > 3 else 0
    spec = _USER_FILTERS.get(fkey)
    if spec is None:
        await callback.answer()
        return
    title_key, statuses = spec
    title = _t(title_key)

    db = SessionLocal()
    try:
        users, total = list_users_by_sub_status_paginated(db, statuses, offset, PAGE)
        if total == 0:
            await _safe_edit(
                callback,
                _empty_state(
                    title,
                    _t("uf.empty_body"),
                    _t("uf.empty_hint"),
                ),
                InlineKeyboardMarkup(inline_keyboard=_nav("adm:um")),
            )
            await callback.answer()
            return

        lines = [_t("uf.header", title=title, total=total, page=offset // PAGE + 1) + "\n"]
        for u in users:
            sub = getattr(u, "subscription", None)
            lines.append(_user_summary_line(u, sub))
            lines.append("")

        open_rows = [
            [InlineKeyboardButton(text=_t("btn.open_user", tid=u.telegram_id), callback_data=f"adm:uv:{u.telegram_id}")]
            for u in users
        ]
        nav_rows: List[List[InlineKeyboardButton]] = []
        nr: List[InlineKeyboardButton] = []
        if offset > 0:
            nr.append(InlineKeyboardButton(
                text=_t("pg.prev"), callback_data=f"adm:uf:{fkey}:{max(0, offset - PAGE)}"))
        if offset + PAGE < total:
            nr.append(InlineKeyboardButton(
                text=_t("pg.next"), callback_data=f"adm:uf:{fkey}:{offset + PAGE}"))
        if nr:
            nav_rows.append(nr)
        nav_rows.extend(_nav("adm:um"))

        await _safe_edit(
            callback,
            "\n".join(lines).strip(),
            InlineKeyboardMarkup(inline_keyboard=open_rows + nav_rows),
        )
    finally:
        db.close()
    await callback.answer()


@router.callback_query(F.data.startswith("adm:exp:"), F.from_user.id == config.admin_id)
async def cb_export_users(callback: CallbackQuery) -> None:
    """Generate an .xlsx for the chosen dataset, send it to the admin, clean up.

    Additive, read-only: it queries users and writes a temp file. No
    subscription / Stripe / entitlement state is touched.
    """
    key = callback.data.split(":")[2]
    spec = _EXPORT_SPECS.get(key)
    if spec is None:
        await callback.answer()
        return
    _label_key, name_key, _count_field, file_prefix = spec
    name = _t(name_key)

    # Ack the tap with a lightweight toast while the file builds.
    await callback.answer(_t("export.generating"))

    headers = [
        _t("export.col_user_id"),
        _t("export.col_username"),
        _t("export.col_full_name"),
        _t("export.col_status"),
        _t("export.col_sub_status"),
        _t("export.col_case_type"),
        _t("export.col_created"),
        _t("export.col_approved"),
    ]

    db = SessionLocal()
    path: Optional[str] = None
    count = 0
    try:
        users = _export_dataset(db, key)
        count = len(users)
        if not users:
            await callback.message.answer(_t("export.empty"))
            return
        # Build the workbook while the session is open (rows read u.subscription
        # and user_type lazily); the file is fully materialized before we close.
        path = export_users_xlsx(
            users, headers, sheet_title=name, filename_prefix=file_prefix
        )
    except Exception as e:  # noqa: BLE001 - export must never crash the panel
        logger.exception("admin export build failed key=%s err=%s", key, e)
        await callback.message.answer(_t("export.failed"))
        return
    finally:
        db.close()

    try:
        await callback.message.answer_document(
            FSInputFile(path, filename=f"{file_prefix}.xlsx"),
            caption=_t("export.caption", name=name, n=count),
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("admin export send failed key=%s err=%s", key, e)
        await callback.message.answer(_t("export.failed"))
    finally:
        safe_remove(path)


def _id_search_prompt_kb() -> InlineKeyboardMarkup:
    """Single Cancel button shown while admin is asked for the user id."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=_t("ids.btn_cancel"), callback_data="adm:idcancel")],
        *_nav("adm:um"),
    ])


def _id_prompt_text() -> str:
    return _t("ids.prompt", sep=_UI_SEPARATOR)


def _id_invalid_text() -> str:
    return _t("ids.invalid", sep=_UI_SEPARATOR)


def _looks_like_telegram_id(text: str) -> bool:
    """Numeric only, between 5 and 15 digits (covers historic and modern ids)."""
    s = text.strip()
    if not s.isdigit():
        return False
    return 5 <= len(s) <= 15


@router.callback_query(F.data == "adm:ids", F.from_user.id == config.admin_id)
async def cb_id_search_start(callback: CallbackQuery) -> None:
    """Open the 'send me the id' prompt and mark the admin as awaiting input."""
    set_awaiting_id_search(callback.from_user.id)
    # Make sure no stale compose-answer state hijacks the next message.
    clear_pending_answer(callback.from_user.id)
    await _safe_edit(callback, _id_prompt_text(), _id_search_prompt_kb())
    await callback.answer()


@router.callback_query(F.data == "adm:idcancel", F.from_user.id == config.admin_id)
async def cb_id_search_cancel(callback: CallbackQuery) -> None:
    clear_awaiting_id_search(callback.from_user.id)
    db = SessionLocal()
    try:
        text, kb = _build_users_dashboard(db)
    finally:
        db.close()
    await _safe_edit(callback, text, kb)
    await callback.answer(_t("ids.cancelled"))


class AwaitingIdSearchFilter(BaseFilter):
    """Admin tapped Search by Telegram ID and the next text message is the id."""

    async def __call__(self, message: Message) -> bool:
        if not message.from_user or message.from_user.id != config.admin_id:
            return False
        if not message.text:
            return False
        return is_awaiting_id_search(message.from_user.id)


@router.message(AwaitingIdSearchFilter())
async def admin_consume_id_search(message: Message) -> None:
    """Admin sent the user id (typed or pasted). Validate, look up, render."""
    text = message.text or ""
    if not _looks_like_telegram_id(text):
        await message.answer(_id_invalid_text(), reply_markup=_id_search_prompt_kb())
        return

    tid = int(text.strip())
    clear_awaiting_id_search(message.from_user.id)

    db = SessionLocal()
    try:
        u = get_user(db, tid)
        if not u:
            kb = InlineKeyboardMarkup(inline_keyboard=_nav("adm:um"))
            await message.answer(
                _empty_state(
                    _t("ids.lookup_empty_title"),
                    _t("ids.lookup_empty_body", tid=tid),
                    _t("ids.lookup_empty_hint"),
                ),
                reply_markup=kb,
                parse_mode="HTML",
            )
            return
        # Re-use the existing detail renderer. It works against a CallbackQuery,
        # but everything it needs is the message instance + tid; build a shim.
        sub = getattr(u, "subscription", None)
        svc = SubscriptionService(db)
        snap = svc.get_subscription_snapshot(tid, user=u)
        expl = EntitlementPolicy().explain_question_entitlement(u)
        vm = build_subscription_view(snap, expl)
        sub_block = format_admin_subscription_status_message(tid, vm, lang=get_admin_language())
        body = _t(
            "ud.block",
            tid=tid,
            name=html.escape(u.first_name),
            username=("@" + html.escape(u.username)) if u.username else "—",
            approval=html.escape(u.status),
            category=html.escape(user_type_admin_label(u)),
            used=u.questions_used,
            limit=u.question_limit,
            sub_block=html.escape(sub_block),
        )
        kb = InlineKeyboardMarkup(inline_keyboard=_kb_user_actions(tid, u))
        await message.answer(body, reply_markup=kb, parse_mode="HTML")
    finally:
        db.close()


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
            await callback.answer(_t("approve.cannot"), show_alert=True)
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
        [InlineKeyboardButton(text=_t(label_key), callback_data=f"adm:rjc:{tid_s}:{code}")]
        for code, label_key, _ in _REJECT_REASONS
    ]
    rows.extend(_nav(f"adm:uv:{tid_s}"))
    await _safe_edit(
        callback,
        _section_header(
            _t("rj.title"),
            _t("rj.desc"),
            _t("rj.prompt"),
        ),
        InlineKeyboardMarkup(inline_keyboard=rows),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm:rjc:"), F.from_user.id == config.admin_id)
async def cb_user_reject(callback: CallbackQuery) -> None:
    parts = callback.data.split(":")
    if len(parts) != 4:
        await callback.answer()
        return
    tid = int(parts[2])
    code = parts[3]
    reason = next((detail for c, _, detail in _REJECT_REASONS if c == code), "Access denied")
    db = SessionLocal()
    try:
        if not reject_user(db, tid, reason):
            await callback.answer(_t("rj.failed"), show_alert=True)
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
                InlineKeyboardButton(text=_t("reset.confirm_btn"), callback_data=f"adm:urc:{tid_s}"),
            ],
            *_nav(f"adm:uv:{tid_s}"),
        ]
    )
    await _safe_edit(
        callback,
        _t("reset.ask"),
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
    await callback.answer(_t("reset.done") if ok else _t("reset.failed"), show_alert=True)
    await _safe_edit(
        callback,
        _t("reset.removed", tid=tid) if ok else _t("reset.failed_page"),
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
        await callback.answer(_t("vip.not_configured"), show_alert=True)
        return
    try:
        await _bot.ban_chat_member(chat_id=config.vip_group_id, user_id=tid)
    except TelegramBadRequest as e:
        await callback.answer(_t("vip.telegram_err", err=e), show_alert=True)
        return
    except Exception as e:
        await callback.answer(str(e)[:200], show_alert=True)
        return
    await _render_user_detail(callback, tid, back="adm:um")


# --- Questions ---


@router.callback_query(F.data == "adm:qm", F.from_user.id == config.admin_id)
async def cb_q_menu(callback: CallbackQuery) -> None:
    db = SessionLocal()
    try:
        kb = _kb_questions_menu(_questions_counts(db))
    finally:
        db.close()
    await _safe_edit(
        callback,
        _section_header(
            _t("qm.title"),
            _t("qm.desc"),
        ),
        kb,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm:qexp:"), F.from_user.id == config.admin_id)
async def cb_export_questions(callback: CallbackQuery) -> None:
    """Export the chosen question dataset (pending / all) to .xlsx and send it.

    Additive + read-only: queries questions and writes a temp file, then deletes
    it. No subscription / Stripe / entitlement state is touched.
    """
    key = callback.data.split(":")[2]  # "pending" | "all"
    if key not in ("pending", "all"):
        await callback.answer()
        return
    name = _t("qexport.name_pending" if key == "pending" else "qexport.name_all")
    file_prefix = "pending_questions" if key == "pending" else "all_questions"

    await callback.answer(_t("export.generating"))

    headers = [
        _t("qexport.col_id"),
        _t("qexport.col_user_id"),
        _t("qexport.col_username"),
        _t("qexport.col_full_name"),
        _t("qexport.col_status"),
        _t("qexport.col_type"),
        _t("qexport.col_text"),
        _t("qexport.col_reply"),
        _t("qexport.col_created"),
        _t("qexport.col_answered"),
    ]

    db = SessionLocal()
    path: Optional[str] = None
    count = 0
    try:
        questions = list_questions(db, status="PENDING" if key == "pending" else None)
        count = len(questions)
        if not questions:
            await callback.message.answer(_t("export.empty"))
            return
        # Resolve usernames/full names in one pass; build the file while the
        # session is open, then close before the network send.
        user_map = {u.telegram_id: u for u in get_all_users(db)}
        path = export_questions_xlsx(
            questions, headers, user_map=user_map, sheet_title=name, filename_prefix=file_prefix
        )
    except Exception as e:  # noqa: BLE001 - export must never crash the panel
        logger.exception("admin question export build failed key=%s err=%s", key, e)
        await callback.message.answer(_t("export.failed"))
        return
    finally:
        db.close()

    try:
        await callback.message.answer_document(
            FSInputFile(path, filename=f"{file_prefix}.xlsx"),
            caption=_t("export.caption", name=name, n=count),
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("admin question export send failed key=%s err=%s", key, e)
        await callback.message.answer(_t("export.failed"))
    finally:
        safe_remove(path)


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
        nav.append(InlineKeyboardButton(text=_t("pg.prev_arrow"), callback_data=f"{prefix}:{max(0, offset - PAGE)}"))
    if offset + PAGE < total:
        nav.append(InlineKeyboardButton(text=_t("pg.next_arrow"), callback_data=f"{prefix}:{offset + PAGE}"))
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
        if total == 0:
            await _safe_edit(
                callback,
                _empty_state(
                    _t("q.pending_empty_title"),
                    _t("q.pending_empty_body"),
                    _t("q.pending_empty_hint"),
                ),
                InlineKeyboardMarkup(inline_keyboard=_nav("adm:qm")),
            )
            await callback.answer()
            return
        text = _t("q.pending_header", n=total) + "\n"
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
        if total == 0:
            await _safe_edit(
                callback,
                _empty_state(
                    _t("q.hist_empty_title"),
                    _t("q.hist_empty_body"),
                    _t("q.hist_empty_hint"),
                ),
                InlineKeyboardMarkup(inline_keyboard=_nav("adm:qm")),
            )
            await callback.answer()
            return
        text = _t("q.hist_header", n=total) + "\n"
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
            await callback.answer(_t("q.not_found"), show_alert=True)
            return
        u = get_user(db, q.user_id)
        un = html.escape(u.username) if u and u.username else "—"
        text = _t(
            "q.detail",
            id=q.id,
            uid=q.user_id,
            un=un,
            status=html.escape(q.status),
            created=q.created_at,
            text=html.escape(q.question_text or ""),
        )
        if q.admin_reply_text:
            text += _t("q.admin_reply_block", reply=html.escape(q.admin_reply_text))
        rows: List[List[InlineKeyboardButton]] = []
        if q.status == "PENDING":
            rows.append(
                [
                    InlineKeyboardButton(text=_t("q.btn_compose"), callback_data=f"adm:qco:{q.id}"),
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
            [InlineKeyboardButton(text=_t("q.btn_cancel_compose"), callback_data="adm:qcc")],
            *_nav(f"adm:qd:{qid}"),
        ]
    )
    await _safe_edit(
        callback,
        _section_header(
            _t("q.compose_title"),
            _t("q.compose_desc"),
            _t("q.compose_prompt"),
        ),
        kb,
    )
    await callback.answer()


@router.callback_query(F.data == "adm:qcc", F.from_user.id == config.admin_id)
async def cb_q_compose_cancel(callback: CallbackQuery) -> None:
    clear_pending_answer(callback.from_user.id)
    await _safe_edit(
        callback,
        _empty_state(
            _t("q.compose_cancelled_title"),
            _t("q.compose_cancelled_body"),
            _t("q.compose_cancelled_hint"),
        ),
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
            await message.answer(_t("q.no_longer_pending"))
            return
        # Delivered to the USER — stays in the user-facing flow, not the admin UI.
        reply_to_user = (
            f"📨 Admin response\n\n"
            f"Your question:\n{q.question_text}\n\n"
            f"Response:\n{text}\n"
        )
        try:
            await _bot.send_message(chat_id=q.user_id, text=reply_to_user)
        except TelegramForbiddenError:
            if mark_question_failed_delivery(db, qid, text):
                await message.answer(_t("q.user_blocked"))
            return
        except Exception as e:
            await message.answer(_t("q.send_failed", err=e))
            return
        if not answer_question(db, qid, text):
            await message.answer(_t("q.db_update_failed"))
            return
        await message.answer(_t("q.answered", qid=qid))
    finally:
        db.close()


# --- Subscriptions ---


@router.callback_query(F.data == "adm:sm", F.from_user.id == config.admin_id)
async def cb_sub_menu(callback: CallbackQuery) -> None:
    await _safe_edit(
        callback,
        _section_header(
            _t("sm.title"),
            _t("sm.desc"),
        ),
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
        if total == 0:
            await _safe_edit(
                callback,
                _empty_state(
                    _t("sl.empty_title"),
                    _t("sl.empty_body"),
                    _t("sl.empty_hint"),
                ),
                InlineKeyboardMarkup(inline_keyboard=_nav("adm:sm")),
            )
            await callback.answer()
            return
        lines = [_t("sl.header", n=total) + "\n"] + [_fmt_sub(s) for s in rows]
        ik: List[List[InlineKeyboardButton]] = []
        nav: List[InlineKeyboardButton] = []
        if offset > 0:
            nav.append(InlineKeyboardButton(text=_t("pg.prev_arrow"), callback_data=f"adm:sl:{max(0, offset - PAGE)}"))
        if offset + PAGE < total:
            nav.append(InlineKeyboardButton(text=_t("pg.next_arrow"), callback_data=f"adm:sl:{offset + PAGE}"))
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
        if total == 0:
            await _safe_edit(
                callback,
                _empty_state(
                    _t("pay.empty_title"),
                    _t("pay.empty_body"),
                    _t("pay.empty_hint"),
                ),
                InlineKeyboardMarkup(inline_keyboard=_nav("adm:sm")),
            )
            await callback.answer()
            return
        lines = [_t("pay.header", n=total) + "\n"] + [_fmt_payment(p) for p in rows]
        ik: List[List[InlineKeyboardButton]] = []
        nav: List[InlineKeyboardButton] = []
        if offset > 0:
            nav.append(InlineKeyboardButton(text=_t("pg.prev_arrow"), callback_data=f"adm:pf:{max(0, offset - PAGE)}"))
        if offset + PAGE < total:
            nav.append(InlineKeyboardButton(text=_t("pg.next_arrow"), callback_data=f"adm:pf:{offset + PAGE}"))
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
        if total == 0:
            await _safe_edit(
                callback,
                _empty_state(
                    _t("wl.empty_title"),
                    _t("wl.empty_body"),
                    _t("wl.empty_hint"),
                ),
                InlineKeyboardMarkup(inline_keyboard=_nav("adm:sm")),
            )
            await callback.answer()
            return
        lines = [_t("wl.header", n=total) + "\n"]
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
            nav.append(InlineKeyboardButton(text=_t("pg.prev_arrow"), callback_data=f"adm:wl:{max(0, offset - PAGE)}"))
        if offset + PAGE < total:
            nav.append(InlineKeyboardButton(text=_t("pg.next_arrow"), callback_data=f"adm:wl:{offset + PAGE}"))
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
        if total == 0:
            await _safe_edit(
                callback,
                _empty_state(
                    _t("pp.empty_title"),
                    _t("pp.empty_body"),
                    _t("pp.empty_hint"),
                ),
                InlineKeyboardMarkup(inline_keyboard=_nav("adm:sm")),
            )
            await callback.answer()
            return
        lines = [_t("pp.header", n=total) + "\n"] + [_fmt_payment(p) for p in rows]
        ik: List[List[InlineKeyboardButton]] = []
        nav: List[InlineKeyboardButton] = []
        if offset > 0:
            nav.append(InlineKeyboardButton(text=_t("pg.prev_arrow"), callback_data=f"adm:pp:{max(0, offset - PAGE)}"))
        if offset + PAGE < total:
            nav.append(InlineKeyboardButton(text=_t("pg.next_arrow"), callback_data=f"adm:pp:{offset + PAGE}"))
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


# --- Admin language ---


@router.message(Command("help"), F.from_user.id == config.admin_id)
async def cmd_admin_help(message: Message) -> None:
    """Admin `/help` shows the admin home hub (admin-localized) — never the user
    onboarding/verification help. Registered before access.router, so the admin
    is served here while users still get the user `/help`."""
    await message.answer(
        _section_header(_t("home.title"), _t("home.desc"), _t("home.prompt")),
        reply_markup=_kb_main(),
        parse_mode="HTML",
    )


@router.message(Command("status"), F.from_user.id == config.admin_id)
async def cmd_admin_status(message: Message) -> None:
    """Admin `/status` shows an admin-localized status — never the user
    'verify your account' flow. Users still get the user `/status`."""
    await message.answer(
        f"<b>{_t('cmd.admin_status_title')}</b>\n\n{_t('cmd.admin_status_body')}",
        reply_markup=_kb_main(),
        parse_mode="HTML",
    )


@router.message(Command("language"), F.from_user.id == config.admin_id)
async def cmd_admin_language(message: Message) -> None:
    """Admin `/language` opens the ADMIN language picker — never the user flow.

    The admin language is managed only through Admin Settings, so the admin's
    `/language` is claimed here (admin_panel is registered before language.router)
    instead of falling into the user onboarding/language flow.
    """
    await message.answer(_language_text(), reply_markup=_kb_language_menu(), parse_mode="HTML")


@router.callback_query(F.data == "adm:lang", F.from_user.id == config.admin_id)
async def cb_language(callback: CallbackQuery) -> None:
    """Open the Admin Language picker (English / Español)."""
    await _safe_edit(callback, _language_text(), _kb_language_menu())
    await callback.answer()


@router.callback_query(F.data.startswith("adm:setlang:"), F.from_user.id == config.admin_id)
async def cb_set_language(callback: CallbackQuery) -> None:
    """Persist the chosen admin language and re-render the picker in it."""
    code = callback.data.split(":")[2]
    lang = set_admin_language(code)
    # Refresh the admin's "/" command palette in the new admin language so it
    # updates immediately (no Telegram app restart needed).
    bot = _bot or (callback.message.bot if callback.message else None)
    if bot is not None:
        from services.bot_commands import set_admin_commands_for_chat

        await set_admin_commands_for_chat(bot, callback.from_user.id, lang)
    # Re-render the picker message in the newly-selected language so the change
    # is immediately visible on this inline menu.
    await _safe_edit(callback, _language_text(), _kb_language_menu())

    # The persistent reply keyboard (bottom section buttons) can ONLY be changed
    # by sending a new message with a fresh reply_markup — editing won't touch it,
    # so without this it would stay in the old language until the admin runs
    # /start. Re-send it now in the new language (this is NOT the /start flow:
    # no state is reset, just the keyboard is refreshed).
    if callback.message is not None:
        await callback.message.answer(
            _t("lang.menu_refreshed"),
            reply_markup=_admin_reply_keyboard(),
            parse_mode="HTML",
        )
    await callback.answer(_t("lang.changed"))
