"""
Read-only subscription / entitlement text for bot UX.
Keeps handlers free of formatting rules.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from app.config import config
from services.entitlement_policy import EntitlementExplanation


def payment_mode_label() -> str:
    if config.mock_payment_enabled:
        return "MOCK"
    if config.stripe_api_key:
        return "REAL_READY"
    return "REAL_NOT_CONFIGURED"


def _fmt_dt(value: Optional[datetime]) -> str:
    if value is None:
        return "—"
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


def format_user_subscription_message(vm: SubscriptionViewModel) -> str:
    sub_status = vm.snapshot.get("subscription_status") or "NONE"
    user_st = vm.snapshot.get("user_status") or "UNKNOWN"
    lines = [
        "📋 Subscription",
        "",
        f"• Account status: {user_st}",
        f"• Subscription state: {sub_status}",
        f"• Billing mode: {vm.mode_label}",
        f"• Plan: {vm.snapshot.get('plan_name') or '—'}",
        f"• Period end: {_fmt_dt(vm.snapshot.get('end_date'))}",
        f"• Grace until: {_fmt_dt(vm.snapshot.get('grace_until'))}",
        "",
        f"• Can ask questions: {'Yes' if vm.explanation.allows_questions else 'No'}",
        f"• Access detail: {vm.explanation.reason}",
        "",
        _next_action_suggestion(vm),
    ]
    return "\n".join(lines)


def _next_action_suggestion(vm: SubscriptionViewModel) -> str:
    if vm.explanation.allows_questions:
        return "✅ You are good to go. Use /status anytime."
    if vm.snapshot.get("user_status") != "APPROVED":
        return "➡️ Complete onboarding: /start"
    if vm.mode_label == "MOCK":
        return "➡️ Try /subscribe to activate (mock), or ask an admin if you need help."
    if vm.mode_label == "REAL_NOT_CONFIGURED":
        return "➡️ Billing is not live yet. Watch for updates from admins."
    return "➡️ Use /renew when checkout is available, or contact support."


def format_admin_subscription_status_message(user_id: int, vm: SubscriptionViewModel) -> str:
    base = format_user_subscription_message(vm)
    return f"🛠 Admin sub view — user {user_id}\n\n{base}"


def subscribe_placeholder_message() -> str:
    return (
        "💳 Subscribe\n\n"
        "Online checkout is not enabled yet. "
        "You will be able to renew here once billing goes live.\n\n"
        "If you need access urgently, contact an admin."
    )
