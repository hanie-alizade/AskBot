"""
State-aware deny messages used outside the question pipeline.

The question pipeline maps EntitlementExplanation reasons to messages and may
distinguish multiple subscription states. Other gates (commands like
/subscribe, /manage_subscription) only need the lifecycle subset:

  no user row | NEW | VERIFIED | PENDING_APPROVAL | REJECTED | APPROVED

`state_aware_command_denial` returns the appropriate (text, optional inline
keyboard) pair so callers don't have to handcraft "Please send /start"
boilerplate per command.
"""

from __future__ import annotations

from typing import Optional, Tuple

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from services.i18n import t_user
from services.legal_documents import REQUIRED_DOCUMENTS, has_accepted_all


def _legal_resume_kb(user) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t_user(user, "btn.resume_legal"), callback_data="legal_resume")],
    ])


def _request_access_kb(user) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=t_user(user, "btn.request_access_now"),
                callback_data="request_access",
            )
        ],
    ])


def state_aware_command_denial(user) -> Tuple[str, Optional[InlineKeyboardMarkup]]:
    """Return a context-aware deny reply for a non-APPROVED user.

    The caller has already decided the user shouldn't be allowed through (e.g.
    /subscribe requires APPROVED). This helper only picks the *right* message
    given the user's lifecycle and legal-acceptance state.
    """
    if user is None:
        return t_user(None, "q.deny_not_registered"), None

    # Legal acceptance wins because it's the lowest gate.
    if not has_accepted_all(user):
        any_accepted = any(
            getattr(user, d.accepted_at_attr, None) for d in REQUIRED_DOCUMENTS
        )
        key = "q.deny_legal_updated" if any_accepted else "q.deny_legal_pending"
        return t_user(user, key), _legal_resume_kb(user)

    status = user.status
    if status == "NEW":
        return t_user(user, "q.deny_new_user"), None
    if status == "VERIFIED":
        return t_user(user, "q.deny_must_request_access"), _request_access_kb(user)
    if status == "PENDING_APPROVAL":
        return t_user(user, "q.deny_pending_approval"), None
    if status == "REJECTED":
        return t_user(user, "q.deny_rejected"), None
    # APPROVED here means caller mis-routed; fall through with no-subscription text.
    return t_user(user, "q.deny_no_subscription"), None
