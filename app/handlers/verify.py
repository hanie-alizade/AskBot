"""
Verification handlers for the user flow.
Handles the initial verification step for new users.
"""

import logging
from typing import Optional, Tuple

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from database.crud import create_user, get_user, update_user_status
from database.db import SessionLocal
from services.entitlement_policy import EntitlementPolicy
from services.i18n import t_user
from services.legal_documents import (
    REQUIRED_DOCUMENTS,
    get_document,
    has_accepted_all,
    is_accepted,
    mark_accepted,
)

from ..config import config

logger = logging.getLogger(__name__)

router = Router()
_entitlement = EntitlementPolicy()


# --------------------------------------------------------------------------- #
# Welcome-screen builders (also called from app/handlers/language.py after a
# language pick, so each one accepts the User and returns a fully-translated
# (text, keyboard) tuple — no inline strings).
# --------------------------------------------------------------------------- #


def _welcome_new(user) -> Tuple[str, InlineKeyboardMarkup]:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t_user(user, "btn.verify"), callback_data="verify_user")],
        [InlineKeyboardButton(text=t_user(user, "btn.check_status"), callback_data="check_status")],
        [InlineKeyboardButton(text=t_user(user, "btn.help"), callback_data="show_help")],
    ])
    return t_user(user, "verify.welcome_new"), keyboard


def _welcome_verified(user) -> Tuple[str, InlineKeyboardMarkup]:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t_user(user, "btn.request_access"), callback_data="request_access")],
        [InlineKeyboardButton(text=t_user(user, "btn.check_status"), callback_data="check_status")],
        [InlineKeyboardButton(text=t_user(user, "btn.help"), callback_data="show_help")],
    ])
    return t_user(user, "verify.welcome_verified"), keyboard


def _welcome_pending(user) -> Tuple[str, InlineKeyboardMarkup]:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t_user(user, "btn.check_status"), callback_data="check_status")],
        [InlineKeyboardButton(text=t_user(user, "btn.help"), callback_data="show_help")],
    ])
    return t_user(user, "verify.welcome_pending"), keyboard


def _welcome_approved(
    user, *, can_vip: bool, vip_link: Optional[str] = None
) -> Tuple[str, InlineKeyboardMarkup]:
    if can_vip:
        url = vip_link or config.group_invite_link
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t_user(user, "btn.join_vip"), url=url)],
            [InlineKeyboardButton(text=t_user(user, "btn.check_status"), callback_data="check_status")],
            [InlineKeyboardButton(text=t_user(user, "btn.help"), callback_data="show_help")],
        ])
        return t_user(user, "verify.welcome_approved_vip"), keyboard

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t_user(user, "btn.subscription"), callback_data="check_status")],
        [InlineKeyboardButton(text=t_user(user, "btn.help"), callback_data="show_help")],
    ])
    return t_user(user, "verify.welcome_approved_no_sub"), keyboard


async def send_welcome_for_status(message: Message, user) -> None:
    """
    Send the appropriate welcome screen for the user's current state, then
    install/refresh the persistent 3-button reply keyboard.

    Re-used by the language picker callback so the menu labels are always in
    the user's current language. Sent as a second message because a single
    Telegram message can carry only one reply_markup (inline OR reply keyboard).
    """
    # Legal-acceptance redirect: any user (NEW or existing) with missing
    # documents lands on the acceptance screen instead of their normal welcome.
    # NEW users would land here anyway after tapping Verify; this branch makes
    # sure existing approved users from before the legal flow existed have a
    # path to complete acceptance.
    if not has_accepted_all(user):
        text, kb = _legal_screen(user)
        await message.answer(text, reply_markup=kb, parse_mode="HTML")
        # Install the persistent reply menu even while the user still has legal
        # documents to accept. Without this, regular users who go through the
        # legal-acceptance flow never receive the reply keyboard (this function
        # returns before the install below), so their menu button "disappears".
        # Menu actions that require acceptance redirect back to the legal screen,
        # so surfacing the menu here is safe.
        from .language import build_reply_menu

        await message.answer(
            t_user(user, "menu.installed"),
            reply_markup=build_reply_menu(getattr(user, "language", None)),
        )
        return

    status = user.status
    if status == "NEW":
        text, kb = _welcome_new(user)
    elif status == "VERIFIED":
        text, kb = _welcome_verified(user)
    elif status == "PENDING_APPROVAL":
        text, kb = _welcome_pending(user)
    elif status == "APPROVED":
        # Need a fresh session to check entitlement without crossing the caller's session.
        db = SessionLocal()
        try:
            fresh = get_user(db, user.telegram_id) or user
            can_vip = _entitlement.explain_question_entitlement(fresh).allows_questions
        finally:
            db.close()
        vip_link: Optional[str] = None
        if can_vip:
            # Fresh single-use link per /start so leaked links die on first use.
            from services.vip_invite import get_personal_invite_link

            vip_link = await get_personal_invite_link(message.bot, user.telegram_id)
        text, kb = _welcome_approved(user, can_vip=can_vip, vip_link=vip_link)
    else:
        return

    await message.answer(text, reply_markup=kb)

    # Lazy import to avoid the language ↔ verify cycle.
    from .language import build_reply_menu

    lang = getattr(user, "language", None)
    await message.answer(
        t_user(user, "menu.installed"),
        reply_markup=build_reply_menu(lang),
    )


# --------------------------------------------------------------------------- #
# /start
# --------------------------------------------------------------------------- #


@router.message(Command("start"))
async def handle_start(message: Message) -> None:
    """Handle /start. First-time users see the language picker; all others see status-based welcome."""
    user_id = message.from_user.id

    logger.info(f"🚀 START command triggered by user {user_id}")

    db = SessionLocal()
    try:
        user = get_user(db, user_id)
        if not user:
            user = create_user(
                db,
                telegram_id=user_id,
                username=message.from_user.username,
                first_name=message.from_user.full_name,
            )

        # First-time language gate: a NULL `language` column means the user has
        # never picked. Existing users were backfilled to 'en' by the migration,
        # so they bypass this and continue normally.
        if not user.language:
            from .language import send_first_time_picker

            logger.info("First-time language picker shown to user %s", user_id)
            await send_first_time_picker(message)
            return

        logger.info(f"User {user_id} sent /start. State: {user.status} lang: {user.language}")
        await send_welcome_for_status(message, user)
    finally:
        db.close()


# --------------------------------------------------------------------------- #
# Inline-button callbacks
# --------------------------------------------------------------------------- #


def _legal_screen(user) -> Tuple[str, InlineKeyboardMarkup]:
    """Render the legal-acceptance screen reflecting current acceptance state."""
    rows = []
    for doc in REQUIRED_DOCUMENTS:
        accepted = is_accepted(user, doc)
        if accepted:
            rows.append(
                [InlineKeyboardButton(text=f"✅ {doc.label}", callback_data=f"legal_view:{doc.key}")]
            )
        else:
            rows.append(
                [
                    InlineKeyboardButton(text=f"📄 View {doc.label}", callback_data=f"legal_view:{doc.key}"),
                    InlineKeyboardButton(text=f"✅ Accept", callback_data=f"legal_accept:{doc.key}"),
                ]
            )

    if has_accepted_all(user):
        rows.append(
            [InlineKeyboardButton(text=t_user(user, "legal.finalize_btn"), callback_data="legal_finalize")]
        )

    text = t_user(user, "legal.intro")
    return text, InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data == "verify_user")
async def handle_verify_callback(callback: CallbackQuery) -> None:
    """Launch the legal-acceptance flow.

    Verification can only complete after every required document is accepted at
    its current version. The flip to VERIFIED happens in handle_legal_finalize.
    """
    user_id = callback.from_user.id

    db = SessionLocal()
    try:
        user = get_user(db, user_id)
        if not user or user.status != "NEW":
            await callback.answer(
                t_user(user, "verify.alert_already_verified"),
                show_alert=True,
            )
            return

        text, kb = _legal_screen(user)
        await callback.message.edit_text(text, reply_markup=kb)
        await callback.answer()
        logger.info("Legal acceptance flow started user_id=%s", user_id)
    finally:
        db.close()


@router.callback_query(F.data == "legal_resume")
async def handle_legal_resume(callback: CallbackQuery) -> None:
    """Re-enter the legal-acceptance flow regardless of user.status.

    Triggered by buttons attached to state-aware deny replies (questions.py,
    access.py, subscription_cmd.py) so users who have a document missing —
    either mid-onboarding or after a version bump — can resume without being
    told to type /start.
    """
    user_id = callback.from_user.id
    db = SessionLocal()
    try:
        user = get_user(db, user_id)
        if not user:
            await callback.answer()
            return
        text, kb = _legal_screen(user)
        await callback.message.answer(text, reply_markup=kb)
        await callback.answer()
        logger.info("Legal acceptance flow resumed user_id=%s status=%s", user_id, user.status)
    finally:
        db.close()


@router.callback_query(F.data.startswith("legal_view:"))
async def handle_legal_view(callback: CallbackQuery) -> None:
    """Show a single document's text with a Back button."""
    user_id = callback.from_user.id
    key = callback.data.split(":", 1)[1]
    doc = get_document(key)
    if doc is None:
        await callback.answer()
        return

    db = SessionLocal()
    try:
        user = get_user(db, user_id)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t_user(user, "legal.back_btn"), callback_data="legal_back")],
        ])
        await callback.message.edit_text(doc.text, reply_markup=kb, parse_mode="HTML")
        await callback.answer()
    finally:
        db.close()


@router.callback_query(F.data == "legal_back")
async def handle_legal_back(callback: CallbackQuery) -> None:
    """Return to the legal-acceptance overview from a single-document view."""
    user_id = callback.from_user.id
    db = SessionLocal()
    try:
        user = get_user(db, user_id)
        if not user:
            await callback.answer()
            return
        text, kb = _legal_screen(user)
        await callback.message.edit_text(text, reply_markup=kb)
        await callback.answer()
    finally:
        db.close()


@router.callback_query(F.data.startswith("legal_accept:"))
async def handle_legal_accept(callback: CallbackQuery) -> None:
    """Record acceptance of a single document, then redraw the overview."""
    user_id = callback.from_user.id
    key = callback.data.split(":", 1)[1]
    doc = get_document(key)
    if doc is None:
        await callback.answer()
        return

    db = SessionLocal()
    try:
        user = get_user(db, user_id)
        if not user:
            await callback.answer()
            return
        was_accepted = is_accepted(user, doc)
        if not was_accepted:
            mark_accepted(user, doc)
            db.commit()
            db.refresh(user)
            logger.info(
                "LEGAL ACCEPTED telegram_id=%s document=%s version=%s",
                user_id, doc.key, doc.version,
            )
        text, kb = _legal_screen(user)
        await callback.message.edit_text(text, reply_markup=kb)
        await callback.answer(t_user(user, "legal.alert_accepted"))
    finally:
        db.close()


@router.callback_query(F.data == "legal_finalize")
async def handle_legal_finalize(callback: CallbackQuery) -> None:
    """Flip NEW → VERIFIED once every required document is accepted."""
    user_id = callback.from_user.id
    db = SessionLocal()
    try:
        user = get_user(db, user_id)
        if not user:
            await callback.answer()
            return

        if not has_accepted_all(user):
            await callback.answer(
                t_user(user, "legal.alert_incomplete"),
                show_alert=True,
            )
            return

        if user.status == "NEW":
            update_user_status(db, user_id, "VERIFIED")
            user = get_user(db, user_id)
            logger.info("User %s completed verification (post legal acceptance)", user_id)

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t_user(user, "btn.request_access"), callback_data="request_access")],
        ])
        await callback.message.edit_text(
            t_user(user, "verify.complete"),
            reply_markup=keyboard,
        )
        await callback.answer(t_user(user, "verify.alert_success"))
    finally:
        db.close()


_STATUS_KEY = {
    "NEW": "status.new",
    "VERIFIED": "status.verified",
    "PENDING_APPROVAL": "status.pending",
    "APPROVED": "status.approved",
    "REJECTED": "status.rejected",
}


@router.callback_query(F.data == "check_status")
async def handle_status_callback(callback: CallbackQuery) -> None:
    """Handle status button click."""
    user_id = callback.from_user.id

    db = SessionLocal()
    try:
        user = get_user(db, user_id)
        if not user:
            await callback.message.answer(t_user(None, "status.not_registered_callback"))
            logger.info(f"User {user_id} checked status but not found in database")
        else:
            status_key = _STATUS_KEY.get(user.status, "status.unknown")
            status_text = t_user(user, status_key)
            await callback.message.answer(
                t_user(user, "status.label", status=status_text)
            )
            logger.info(f"User {user_id} checked their status via button: {user.status}")
    finally:
        db.close()

    await callback.answer()


_HELP_KEY = {
    "NEW": "help.new",
    "VERIFIED": "help.verified",
    "PENDING_APPROVAL": "help.pending",
    "APPROVED": "help.approved_with_vip",
}


@router.callback_query(F.data == "show_help")
async def handle_help_callback(callback: CallbackQuery) -> None:
    """Handle help button click."""
    user_id = callback.from_user.id

    db = SessionLocal()
    try:
        user = get_user(db, user_id)
        if not user:
            user = create_user(
                db,
                telegram_id=user_id,
                username=callback.from_user.username,
                first_name=callback.from_user.full_name,
            )

        body_key = _HELP_KEY.get(user.status, "help.new")
        help_text = t_user(user, "help.title") + t_user(user, body_key)
        await callback.message.answer(help_text)
        logger.info(f"User {user_id} requested help via button: {user.status}")
    finally:
        db.close()

    await callback.answer()
