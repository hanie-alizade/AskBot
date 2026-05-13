"""
Entitlement policy for access and question limits.

Keeps rollout behavior centralized so handlers stay simple and consistent.
"""

from dataclasses import dataclass
from datetime import datetime
from math import inf
from typing import Optional

from database.models import User
from database.models_subscription import SubscriptionStatus, SubscriptionPlan
from app.config import config


@dataclass(frozen=True)
class EntitlementExplanation:
    """Structured entitlement result for logging and read-only UX."""

    decision: str  # ALLOW | DENY
    reason: str
    allows_questions: bool
    subscription_status: Optional[str]


class EntitlementPolicy:
    """Evaluate user access and usage limits during payment rollout."""

    def explain_question_entitlement(self, user: Optional[User]) -> EntitlementExplanation:
        """
        Single source of truth for VIP question access + debug reason.
        Safe when user.subscription is missing or user status mismatches subscription.
        """
        if not user:
            return EntitlementExplanation(
                decision="DENY",
                reason="no_user",
                allows_questions=False,
                subscription_status=None,
            )

        sub = getattr(user, "subscription", None)
        sub_status = str(sub.status) if sub is not None else None

        if user.status != "APPROVED":
            return EntitlementExplanation(
                decision="DENY",
                reason="user_not_approved",
                allows_questions=False,
                subscription_status=sub_status,
            )

        if config.mock_payment_enabled and config.mock_subscription_active_by_default:
            return EntitlementExplanation(
                decision="ALLOW",
                reason="mock_active_by_default",
                allows_questions=True,
                subscription_status=sub_status,
            )

        if not config.subscription_enforcement_enabled:
            return EntitlementExplanation(
                decision="ALLOW",
                reason="enforcement_disabled",
                allows_questions=True,
                subscription_status=sub_status,
            )

        if sub is None:
            return EntitlementExplanation(
                decision="DENY",
                reason="no_subscription_row",
                allows_questions=False,
                subscription_status=None,
            )

        if sub.user_id != user.telegram_id:
            return EntitlementExplanation(
                decision="DENY",
                reason="subscription_user_id_mismatch",
                allows_questions=False,
                subscription_status=sub_status,
            )

        now = datetime.utcnow()
        if sub.status == SubscriptionStatus.ACTIVE:
            if not sub.end_date:
                return EntitlementExplanation(
                    decision="DENY",
                    reason="active_missing_end_date",
                    allows_questions=False,
                    subscription_status=sub_status,
                )
            if sub.end_date <= now:
                return EntitlementExplanation(
                    decision="DENY",
                    reason="subscription_period_expired",
                    allows_questions=False,
                    subscription_status=sub_status,
                )
            return EntitlementExplanation(
                decision="ALLOW",
                reason="active_subscription",
                allows_questions=True,
                subscription_status=sub_status,
            )

        if sub.status == SubscriptionStatus.GRACE:
            if sub.grace_until and sub.grace_until > now:
                return EntitlementExplanation(
                    decision="ALLOW",
                    reason="grace_period",
                    allows_questions=True,
                    subscription_status=sub_status,
                )
            return EntitlementExplanation(
                decision="DENY",
                reason="grace_expired",
                allows_questions=False,
                subscription_status=sub_status,
            )

        if sub.status in (
            SubscriptionStatus.EXPIRED,
            SubscriptionStatus.CANCELLED,
            SubscriptionStatus.INACTIVE,
            SubscriptionStatus.PENDING_PAYMENT,
            SubscriptionStatus.SUSPENDED,
        ):
            return EntitlementExplanation(
                decision="DENY",
                reason=f"subscription_state_{sub.status}",
                allows_questions=False,
                subscription_status=sub_status,
            )

        return EntitlementExplanation(
            decision="DENY",
            reason="subscription_state_unknown",
            allows_questions=False,
            subscription_status=sub_status,
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

