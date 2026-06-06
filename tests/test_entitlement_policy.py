"""
Deterministic entitlement matrix (subscription enforcement ON).
"""

import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from app.config import config
from database.models import User
from database.models_subscription import Subscription, SubscriptionPlan, SubscriptionStatus
from services.entitlement_policy import EntitlementPolicy


def _user(status: str, subscription=None, *, legal_accepted: bool = True) -> User:
    """Build a test User.

    legal_accepted=True (the default) stamps every required legal document with
    the current version so the entitlement gate added by services/legal_documents
    does not deny these subscription-matrix tests.
    """
    u = User(
        id=1,
        telegram_id=100,
        username="u",
        first_name="n",
        status=status,
    )
    u.subscription = subscription
    if legal_accepted:
        from services.legal_documents import REQUIRED_DOCUMENTS, mark_accepted

        for doc in REQUIRED_DOCUMENTS:
            mark_accepted(u, doc)
    return u


def _subscription(
    *,
    status,
    end_date=None,
    grace_until=None,
    user_id=100,
) -> Subscription:
    return Subscription(
        user_id=user_id,
        plan_name=SubscriptionPlan.VIP,
        status=status,
        end_date=end_date,
        grace_until=grace_until,
    )


class EntitlementMatrixTests(unittest.TestCase):
    """Expected outcomes with SUBSCRIPTION_ENFORCEMENT_ENABLED=True."""

    def setUp(self):
        self.enforced = patch.multiple(
            config,
            subscription_enforcement_enabled=True,
            mock_payment_enabled=True,
            mock_subscription_active_by_default=True,
        )
        self.now = datetime.utcnow()

    def test_approved_none_deny(self):
        u = _user("APPROVED", None)
        with self.enforced:
            e = EntitlementPolicy().explain_question_entitlement(u)
        self.assertEqual(e.decision, "DENY")
        self.assertEqual(e.reason, "no_subscription")
        self.assertFalse(e.allows_questions)

    def test_approved_active_allow(self):
        sub = _subscription(
            status=SubscriptionStatus.ACTIVE,
            end_date=self.now + timedelta(days=5),
        )
        u = _user("APPROVED", sub)
        with self.enforced:
            e = EntitlementPolicy().explain_question_entitlement(u)
        self.assertEqual(e.decision, "ALLOW")
        self.assertEqual(e.reason, "active_subscription")
        self.assertTrue(e.allows_questions)

    def test_approved_grace_valid_allow(self):
        sub = _subscription(
            status=SubscriptionStatus.GRACE,
            grace_until=self.now + timedelta(days=1),
        )
        u = _user("APPROVED", sub)
        with self.enforced:
            e = EntitlementPolicy().explain_question_entitlement(u)
        self.assertEqual(e.decision, "ALLOW")
        self.assertEqual(e.reason, "grace_period")
        self.assertTrue(e.grace_valid)

    def test_approved_grace_expired_deny(self):
        sub = _subscription(
            status=SubscriptionStatus.GRACE,
            grace_until=self.now - timedelta(days=1),
        )
        u = _user("APPROVED", sub)
        with self.enforced:
            e = EntitlementPolicy().explain_question_entitlement(u)
        self.assertEqual(e.decision, "DENY")
        self.assertEqual(e.reason, "grace_expired")

    def test_approved_expired_deny(self):
        sub = _subscription(status=SubscriptionStatus.EXPIRED)
        u = _user("APPROVED", sub)
        with self.enforced:
            e = EntitlementPolicy().explain_question_entitlement(u)
        self.assertEqual(e.decision, "DENY")
        self.assertEqual(e.reason, "subscription_expired")

    def test_approved_cancelled_deny(self):
        sub = _subscription(status=SubscriptionStatus.CANCELLED)
        u = _user("APPROVED", sub)
        with self.enforced:
            e = EntitlementPolicy().explain_question_entitlement(u)
        self.assertEqual(e.decision, "DENY")
        self.assertEqual(e.reason, "subscription_cancelled")

    def test_approved_inactive_deny(self):
        sub = _subscription(status=SubscriptionStatus.INACTIVE)
        u = _user("APPROVED", sub)
        with self.enforced:
            e = EntitlementPolicy().explain_question_entitlement(u)
        self.assertEqual(e.decision, "DENY")
        self.assertEqual(e.reason, "subscription_inactive")

    def test_pending_approval_active_sub_deny(self):
        sub = _subscription(
            status=SubscriptionStatus.ACTIVE,
            end_date=self.now + timedelta(days=5),
        )
        u = _user("PENDING_APPROVAL", sub)
        with self.enforced:
            e = EntitlementPolicy().explain_question_entitlement(u)
        self.assertEqual(e.decision, "DENY")
        self.assertEqual(e.reason, "user_not_approved")

    def test_verified_active_sub_deny(self):
        sub = _subscription(
            status=SubscriptionStatus.ACTIVE,
            end_date=self.now + timedelta(days=5),
        )
        u = _user("VERIFIED", sub)
        with self.enforced:
            e = EntitlementPolicy().explain_question_entitlement(u)
        self.assertEqual(e.decision, "DENY")
        self.assertEqual(e.reason, "user_not_approved")

    def test_mock_flags_do_not_override_expired(self):
        """Regression: mock payment must not grant questions when subscription is EXPIRED."""
        sub = _subscription(status=SubscriptionStatus.EXPIRED)
        u = _user("APPROVED", sub)
        with self.enforced:
            e = EntitlementPolicy().explain_question_entitlement(u)
        self.assertFalse(e.allows_questions)
        self.assertNotEqual(e.reason, "mock_active_by_default")


class EnforcementOffRowTests(unittest.TestCase):
    """Dead subscription rows deny even when SUBSCRIPTION_ENFORCEMENT_ENABLED=False."""

    def setUp(self):
        self.unenforced = patch.multiple(
            config,
            subscription_enforcement_enabled=False,
            mock_payment_enabled=True,
            mock_subscription_active_by_default=True,
        )
        self.now = datetime.utcnow()

    def test_expired_row_denies_when_enforcement_off(self):
        sub = _subscription(status=SubscriptionStatus.EXPIRED)
        u = _user("APPROVED", sub)
        with self.unenforced:
            e = EntitlementPolicy().explain_question_entitlement(u)
        self.assertEqual(e.decision, "DENY")
        self.assertEqual(e.reason, "subscription_expired")
        self.assertFalse(e.allows_questions)

    def test_valid_active_allows_enforcement_disabled_when_off(self):
        sub = _subscription(
            status=SubscriptionStatus.ACTIVE,
            end_date=self.now + timedelta(days=5),
        )
        u = _user("APPROVED", sub)
        with self.unenforced:
            e = EntitlementPolicy().explain_question_entitlement(u)
        self.assertEqual(e.decision, "ALLOW")
        self.assertEqual(e.reason, "enforcement_disabled")
        self.assertTrue(e.allows_questions)

    def test_no_subscription_denies_when_enforcement_off(self):
        u = _user("APPROVED", None)
        with self.unenforced:
            e = EntitlementPolicy().explain_question_entitlement(u)
        self.assertEqual(e.decision, "DENY")
        self.assertEqual(e.reason, "no_subscription")
        self.assertFalse(e.allows_questions)


if __name__ == "__main__":
    unittest.main()
