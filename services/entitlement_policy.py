"""
Entitlement policy for access and question limits.

Keeps rollout behavior centralized so handlers stay simple and consistent.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from math import inf
from typing import Optional

from database.models import User
from database.models_subscription import Subscription, SubscriptionStatus, SubscriptionPlan
from app.config import config

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EntitlementExplanation:
    """Structured entitlement result for logging and read-only UX."""

    decision: str  # ALLOW | DENY
    reason: str
    allows_questions: bool
    subscription_status: Optional[str]
    user_status: Optional[str] = None
    grace_valid: bool = False


def log_entitlement_decision(
    log: logging.Logger,
    expl: EntitlementExplanation,
    telegram_user_id: int,
) -> None:
    """Single structured line for entitlement audits."""
    sub_display = expl.subscription_status if expl.subscription_status is not None else "NONE"
    log.info(
        "Entitlement decision: user_id=%s user_status=%s subscription_status=%s "
        "grace_valid=%s decision=%s reason=%s allows_questions=%s",
        telegram_user_id,
        expl.user_status,
        sub_display,
        expl.grace_valid,
        expl.decision,
        expl.reason,
        expl.allows_questions,
    )


class EntitlementPolicy:
    """Evaluate user access and usage limits during payment rollout."""

    def _subscription_row_entitlement(
        self, user: User, sub: Subscription, now: datetime
    ) -> EntitlementExplanation:
        """Interpret an existing subscription row (caller ensures sub is not None)."""
        sub_status = str(sub.status)
        if sub.user_id != user.telegram_id:
            return EntitlementExplanation(
                decision="DENY",
                reason="subscription_user_id_mismatch",
                allows_questions=False,
                subscription_status=sub_status,
                user_status=user.status,
                grace_valid=False,
            )

        if sub.status == SubscriptionStatus.ACTIVE:
            if not sub.end_date:
                return EntitlementExplanation(
                    decision="DENY",
                    reason="active_missing_end_date",
                    allows_questions=False,
                    subscription_status=sub_status,
                    user_status=user.status,
                    grace_valid=False,
                )
            if sub.end_date <= now:
                return EntitlementExplanation(
                    decision="DENY",
                    reason="subscription_period_expired",
                    allows_questions=False,
                    subscription_status=sub_status,
                    user_status=user.status,
                    grace_valid=False,
                )
            return EntitlementExplanation(
                decision="ALLOW",
                reason="active_subscription",
                allows_questions=True,
                subscription_status=sub_status,
                user_status=user.status,
                grace_valid=False,
            )

        if sub.status == SubscriptionStatus.GRACE:
            grace_ok = bool(sub.grace_until and sub.grace_until > now)
            if grace_ok:
                return EntitlementExplanation(
                    decision="ALLOW",
                    reason="grace_period",
                    allows_questions=True,
                    subscription_status=sub_status,
                    user_status=user.status,
                    grace_valid=True,
                )
            return EntitlementExplanation(
                decision="DENY",
                reason="grace_expired",
                allows_questions=False,
                subscription_status=sub_status,
                user_status=user.status,
                grace_valid=False,
            )

        if sub.status == SubscriptionStatus.PAST_DUE:
            # Failed renewal payment, but we extend access until grace_until.
            grace_ok = bool(sub.grace_until and sub.grace_until > now)
            if grace_ok:
                return EntitlementExplanation(
                    decision="ALLOW",
                    reason="payment_past_due_grace",
                    allows_questions=True,
                    subscription_status=sub_status,
                    user_status=user.status,
                    grace_valid=True,
                )
            return EntitlementExplanation(
                decision="DENY",
                reason="past_due_grace_expired",
                allows_questions=False,
                subscription_status=sub_status,
                user_status=user.status,
                grace_valid=False,
            )

        if sub.status == SubscriptionStatus.CANCELLED:
            # User cancelled renewal, but they paid for the current period.
            # Allow access until end_date, then deny.
            within_paid_period = bool(sub.end_date and sub.end_date > now)
            if within_paid_period:
                return EntitlementExplanation(
                    decision="ALLOW",
                    reason="cancelled_within_paid_period",
                    allows_questions=True,
                    subscription_status=sub_status,
                    user_status=user.status,
                    grace_valid=False,
                )
            return EntitlementExplanation(
                decision="DENY",
                reason="subscription_cancelled",
                allows_questions=False,
                subscription_status=sub_status,
                user_status=user.status,
                grace_valid=False,
            )

        terminal_deny_reasons = {
            SubscriptionStatus.EXPIRED: "subscription_expired",
            SubscriptionStatus.INACTIVE: "subscription_inactive",
            SubscriptionStatus.PENDING_PAYMENT: "subscription_pending_payment",
            SubscriptionStatus.SUSPENDED: "subscription_suspended",
        }
        if sub.status in terminal_deny_reasons:
            return EntitlementExplanation(
                decision="DENY",
                reason=terminal_deny_reasons[sub.status],
                allows_questions=False,
                subscription_status=sub_status,
                user_status=user.status,
                grace_valid=False,
            )

        return EntitlementExplanation(
            decision="DENY",
            reason="subscription_state_unknown",
            allows_questions=False,
            subscription_status=sub_status,
            user_status=user.status,
            grace_valid=False,
        )

    def explain_question_entitlement(self, user: Optional[User]) -> EntitlementExplanation:
        """
        Single source of truth for VIP question access + debug reason.
        Safe when user.subscription is missing or user status mismatches subscription.

        Mock payment mode does not change this outcome; it only affects checkout/webhooks.

        Dead subscription rows (EXPIRED, CANCELLED, lapsed ACTIVE/GRACE, etc.) always deny,
        even when SUBSCRIPTION_ENFORCEMENT_ENABLED is false.

        Approved users need a subscription row in a valid ACTIVE or GRACE window to ask
        questions. Missing subscription always denies. When enforcement is disabled but the
        row is valid, the reason remains enforcement_disabled (billing rollout UX only).
        """
        if not user:
            return EntitlementExplanation(
                decision="DENY",
                reason="no_user",
                allows_questions=False,
                subscription_status=None,
                user_status=None,
                grace_valid=False,
            )

        sub = getattr(user, "subscription", None)
        sub_status = str(sub.status) if sub is not None else None

        if user.status != "APPROVED":
            return EntitlementExplanation(
                decision="DENY",
                reason="user_not_approved",
                allows_questions=False,
                subscription_status=sub_status,
                user_status=user.status,
                grace_valid=False,
            )

        # Legal acceptance gate: even approved users with valid subs are denied
        # if they haven't accepted every required document at its current version.
        from services.legal_documents import has_accepted_all  # local to avoid cycle

        if not has_accepted_all(user):
            return EntitlementExplanation(
                decision="DENY",
                reason="legal_consent_missing",
                allows_questions=False,
                subscription_status=sub_status,
                user_status=user.status,
                grace_valid=False,
            )

        now = datetime.utcnow()

        if sub is not None:
            row_expl = self._subscription_row_entitlement(user, sub, now)
            if row_expl.decision == "DENY":
                return row_expl
            if not config.subscription_enforcement_enabled:
                return EntitlementExplanation(
                    decision="ALLOW",
                    reason="enforcement_disabled",
                    allows_questions=True,
                    subscription_status=sub_status,
                    user_status=user.status,
                    grace_valid=row_expl.grace_valid,
                )
            return row_expl

        return EntitlementExplanation(
            decision="DENY",
            reason="no_subscription",
            allows_questions=False,
            subscription_status=None,
            user_status=user.status,
            grace_valid=False,
        )

    def can_access_vip(self, user: Optional[User]) -> bool:
        return self.explain_question_entitlement(user).allows_questions

    def has_active_subscription(self, user: Optional[User]) -> bool:
        if not user or not user.subscription:
            return False

        subscription = user.subscription
        now = datetime.utcnow()
        if subscription.status == SubscriptionStatus.ACTIVE:
            return bool(subscription.end_date and subscription.end_date > now)
        if subscription.status == SubscriptionStatus.GRACE:
            return bool(subscription.grace_until and subscription.grace_until > now)
        if subscription.status == SubscriptionStatus.PAST_DUE:
            return bool(subscription.grace_until and subscription.grace_until > now)
        if subscription.status == SubscriptionStatus.CANCELLED:
            return bool(subscription.end_date and subscription.end_date > now)
        return False

    def get_effective_question_limit(self, user: Optional[User]) -> float:
        if not user:
            return 0
        if self.has_active_subscription(user):
            plan_name = (user.subscription.plan_name or "").upper()
            if plan_name == SubscriptionPlan.VIP:
                return inf
            if plan_name == SubscriptionPlan.PREMIUM:
                return 50
        return user.question_limit

    def remaining_questions(self, user: Optional[User]) -> float:
        if not user:
            return 0
        limit = self.get_effective_question_limit(user)
        if limit == inf:
            return inf
        return max(0, limit - user.questions_used)
