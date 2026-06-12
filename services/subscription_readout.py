"""
Read-only subscription / entitlement text for bot UX.
Keeps handlers free of formatting rules.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from app.config import config
from services.entitlement_policy import EntitlementExplanation
from services.i18n import t


def payment_mode_label() -> str:
    if config.mock_payment_enabled:
        return "MOCK"
    if config.stripe_secret_key:
        return "REAL_READY"
    return "REAL_NOT_CONFIGURED"


def _fmt_dt(value: Optional[datetime], dash: str) -> str:
    if value is None:
        return dash
    return value.strftime("%Y-%m-%d %H:%M UTC")


@dataclass
class SubscriptionViewModel:
    snapshot: Dict[str, Any]
    explanation: EntitlementExplanation
    mode_label: str


def build_subscription_view(snapshot: Dict[str, Any], explanation: EntitlementExplanation) -> SubscriptionViewModel:
    return SubscriptionViewModel(
        snapshot=snapshot,
        explanation=explanation,
        mode_label=payment_mode_label(),
    )


def format_user_subscription_message(
    vm: SubscriptionViewModel,
    *,
    include_next_action: bool = True,
    lang: Optional[str] = None,
) -> str:
    """Format the subscription readout for a user. `lang=None` uses English (admin path)."""
    sub_status = vm.snapshot.get("subscription_status") or "NONE"
    user_st = vm.snapshot.get("user_status") or "UNKNOWN"
    dash = t(lang, "sub.readout_dash")
    plan = vm.snapshot.get("plan_name") or dash

    lines = [
        t(lang, "sub.readout_title"),
        "",
        t(lang, "sub.readout_account_status", status=user_st),
        t(lang, "sub.readout_sub_state", state=sub_status),
        t(lang, "sub.readout_billing_mode", mode=vm.mode_label),
        t(lang, "sub.readout_plan", plan=plan),
        t(lang, "sub.readout_period_end", date=_fmt_dt(vm.snapshot.get("end_date"), dash)),
        t(lang, "sub.readout_grace_until", date=_fmt_dt(vm.snapshot.get("grace_until"), dash)),
        "",
        t(
            lang,
            "sub.readout_can_ask",
            yes_no=t(lang, "sub.readout_yes" if vm.explanation.allows_questions else "sub.readout_no"),
        ),
        t(lang, "sub.readout_access_detail", reason=vm.explanation.reason),
    ]
    if include_next_action:
        lines.extend(["", _next_action_suggestion(vm, lang)])
    return "\n".join(lines)


def _next_action_suggestion(vm: SubscriptionViewModel, lang: Optional[str]) -> str:
    if vm.explanation.allows_questions:
        return t(lang, "sub.next_good_to_go")
    if vm.snapshot.get("user_status") != "APPROVED":
        return t(lang, "sub.next_complete_onboarding")
    if vm.mode_label == "MOCK":
        return t(lang, "sub.next_mock_subscribe")
    if vm.mode_label == "REAL_NOT_CONFIGURED":
        return t(lang, "sub.next_not_configured")
    return t(lang, "sub.next_use_renew")


def format_admin_subscription_status_message(
    user_id: int, vm: SubscriptionViewModel, lang: Optional[str] = None
) -> str:
    """Admin subscription view. `lang` selects the admin UI language (None = English).

    The body reuses the shared user readout (its labels already have Spanish
    translations); interpolated values (statuses, dates, mode) are data and are
    not translated. The header is localized via the admin catalog.
    """
    from services.i18n.admin import get_admin_text

    base = format_user_subscription_message(vm, include_next_action=False, lang=lang)
    header = get_admin_text("sub.admin_header", lang, user_id=user_id)
    return f"{header}\n\n{base}"


def subscribe_placeholder_message(lang: Optional[str] = None) -> str:
    return t(lang, "sub.placeholder_msg")
