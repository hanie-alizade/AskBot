"""VIP subscription markers and reconciliation (DB + mocked Telegram)."""

import unittest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import config
from database.db import Base
from database.models import User
from database.models_subscription import Subscription, SubscriptionPlan, SubscriptionStatus
from services.vip_membership import (
    apply_vip_subscription_markers,
    reconcile_vip_group_membership,
    sync_vip_markers_after_subscription_change,
)


def _memory_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


class VIPMarkerTests(unittest.TestCase):
    def setUp(self):
        self._p = patch.multiple(
            config,
            subscription_enforcement_enabled=True,
            vip_group_id=123,
            vip_subscription_lapse_removal_delay_seconds=60,
        )
        self._p.start()

    def tearDown(self):
        self._p.stop()

    def test_apply_sets_invalid_since_when_lapsed(self):
        db = _memory_session()
        try:
            u = User(telegram_id=42, username="t", first_name="n", status="APPROVED")
            u.vip_invite_sent_at = datetime.utcnow()
            db.add(u)
            db.commit()
            sub = Subscription(
                user_id=42,
                plan_name=SubscriptionPlan.VIP,
                status=SubscriptionStatus.EXPIRED,
            )
            db.add(sub)
            db.commit()
            db.refresh(u)

            self.assertTrue(apply_vip_subscription_markers(db, u))
            db.commit()
            db.refresh(u)
            self.assertIsNotNone(u.vip_sub_invalid_since)
            self.assertIsNone(u.vip_billing_removal_at)
        finally:
            db.close()

    def test_apply_clears_invalid_when_entitled(self):
        db = _memory_session()
        try:
            u = User(telegram_id=43, username="t", first_name="n", status="APPROVED")
            u.vip_invite_sent_at = datetime.utcnow()
            u.vip_sub_invalid_since = datetime.utcnow() - timedelta(hours=1)
            db.add(u)
            db.commit()
            end = datetime.utcnow() + timedelta(days=7)
            sub = Subscription(
                user_id=43,
                plan_name=SubscriptionPlan.VIP,
                status=SubscriptionStatus.ACTIVE,
                end_date=end,
            )
            db.add(sub)
            db.commit()
            db.refresh(u)

            self.assertTrue(apply_vip_subscription_markers(db, u))
            db.commit()
            db.refresh(u)
            self.assertIsNone(u.vip_sub_invalid_since)
        finally:
            db.close()

    def test_billing_removal_blocks_new_invalid_since(self):
        db = _memory_session()
        try:
            u = User(telegram_id=44, username="t", first_name="n", status="APPROVED")
            u.vip_invite_sent_at = datetime.utcnow()
            u.vip_billing_removal_at = datetime.utcnow()
            db.add(u)
            db.commit()
            sub = Subscription(
                user_id=44,
                plan_name=SubscriptionPlan.VIP,
                status=SubscriptionStatus.EXPIRED,
            )
            db.add(sub)
            db.commit()
            db.refresh(u)

            self.assertFalse(apply_vip_subscription_markers(db, u))
            self.assertIsNone(u.vip_sub_invalid_since)
        finally:
            db.close()

    def test_sync_by_user_id(self):
        db = _memory_session()
        try:
            u = User(telegram_id=45, username="t", first_name="n", status="APPROVED")
            u.vip_invite_sent_at = datetime.utcnow()
            db.add(u)
            db.commit()
            sub = Subscription(
                user_id=45,
                plan_name=SubscriptionPlan.VIP,
                status=SubscriptionStatus.CANCELLED,
            )
            db.add(sub)
            db.commit()

            sync_vip_markers_after_subscription_change(db, 45)
            db.refresh(u)
            self.assertIsNotNone(u.vip_sub_invalid_since)
        finally:
            db.close()


class VIPReconcileAsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_reconcile_bans_after_delay(self):
        with patch.multiple(
            config,
            subscription_enforcement_enabled=True,
            vip_group_id=999,
            vip_subscription_lapse_removal_delay_seconds=1,
        ):
            db = _memory_session()
            try:
                u = User(telegram_id=77, username="t", first_name="n", status="APPROVED")
                u.vip_invite_sent_at = datetime.utcnow()
                u.vip_sub_invalid_since = datetime.utcnow() - timedelta(seconds=10)
                db.add(u)
                db.commit()
                sub = Subscription(
                    user_id=77,
                    plan_name=SubscriptionPlan.VIP,
                    status=SubscriptionStatus.EXPIRED,
                )
                db.add(sub)
                db.commit()

                bot = AsyncMock()
                await reconcile_vip_group_membership(bot, db)
                bot.ban_chat_member.assert_awaited_once()
                db.refresh(u)
                self.assertIsNotNone(u.vip_billing_removal_at)
                self.assertIsNone(u.vip_sub_invalid_since)
            finally:
                db.close()

    async def test_reconcile_unban_when_re_subscribed(self):
        with patch.multiple(
            config,
            subscription_enforcement_enabled=True,
            vip_group_id=999,
            vip_subscription_lapse_removal_delay_seconds=3600,
        ):
            db = _memory_session()
            try:
                end = datetime.utcnow() + timedelta(days=5)
                u = User(telegram_id=78, username="t", first_name="n", status="APPROVED")
                u.vip_invite_sent_at = datetime.utcnow()
                u.vip_billing_removal_at = datetime.utcnow() - timedelta(days=1)
                db.add(u)
                db.commit()
                sub = Subscription(
                    user_id=78,
                    plan_name=SubscriptionPlan.VIP,
                    status=SubscriptionStatus.ACTIVE,
                    end_date=end,
                )
                db.add(sub)
                db.commit()

                bot = AsyncMock()
                bot.send_message = AsyncMock()
                await reconcile_vip_group_membership(bot, db)
                bot.unban_chat_member.assert_awaited()
                db.refresh(u)
                self.assertIsNone(u.vip_billing_removal_at)
            finally:
                db.close()


if __name__ == "__main__":
    unittest.main()
