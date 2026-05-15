"""
Subscription service layer for AskBot.
Handles subscription business logic and lifecycle management.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from database.models import User
from database.models_subscription import Subscription, Payment, SubscriptionStatus, PaymentStatus, SubscriptionPlan, PaymentProvider
from services.payments.types import NormalizedPaymentEvent
import logging

logger = logging.getLogger(__name__)


def _vip_hook_after_subscription_change(db: Session, user_id: int) -> None:
    from services.vip_membership import after_subscription_mutation

    after_subscription_mutation(db, user_id)


class SubscriptionService:
    """Service for managing subscriptions and payments."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_active_subscription(self, user_id: int) -> Optional[Subscription]:
        """Get user's active subscription."""
        return self.db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.status == SubscriptionStatus.ACTIVE,
            Subscription.end_date > datetime.utcnow()
        ).first()
    
    def get_subscription_by_user(self, user_id: int) -> Optional[Subscription]:
        """Get user's current subscription (any status)."""
        return self.db.query(Subscription).filter(
            Subscription.user_id == user_id
        ).order_by(Subscription.created_at.desc()).first()
    
    def activate_subscription(
        self,
        user_id: int,
        plan_name: str,
        payment_provider: str,
        external_subscription_id: Optional[str] = None,
        duration_days: int = 30
    ) -> Optional[Subscription]:
        """Activate a new subscription for user."""
        try:
            # Deactivate existing subscription if any
            existing = self.get_subscription_by_user(user_id)
            if existing and existing.status == SubscriptionStatus.ACTIVE:
                existing.status = SubscriptionStatus.CANCELLED
                self.db.commit()
                _vip_hook_after_subscription_change(self.db, user_id)

            # Create new subscription
            subscription = Subscription(
                user_id=user_id,
                plan_name=plan_name,
                status=SubscriptionStatus.ACTIVE,
                start_date=datetime.utcnow(),
                end_date=datetime.utcnow() + timedelta(days=duration_days),
                auto_renew=False,
                payment_provider=payment_provider,
                external_subscription_id=external_subscription_id,
                activated_at=datetime.utcnow(),
                grace_until=datetime.utcnow() + timedelta(days=duration_days + 3),
            )
            
            self.db.add(subscription)
            self.db.commit()
            self.db.refresh(subscription)
            
            logger.info(f"Activated {plan_name} subscription for user {user_id}")
            _vip_hook_after_subscription_change(self.db, user_id)
            return subscription

        except Exception as e:
            logger.error(f"Failed to activate subscription for user {user_id}: {e}")
            self.db.rollback()
            return None

    def set_subscription_inactive(self, user_id: int) -> bool:
        """Move subscription to inactive state."""
        subscription = self.get_subscription_by_user(user_id)
        if not subscription:
            return False
        subscription.status = SubscriptionStatus.INACTIVE
        subscription.updated_at = datetime.utcnow()
        self.db.commit()
        _vip_hook_after_subscription_change(self.db, user_id)
        return True

    def move_to_grace(self, user_id: int, grace_days: int = 3) -> bool:
        """Move subscription to grace period."""
        subscription = self.get_subscription_by_user(user_id)
        if not subscription:
            return False
        now = datetime.utcnow()
        subscription.status = SubscriptionStatus.GRACE
        subscription.grace_until = now + timedelta(days=grace_days)
        subscription.updated_at = now
        self.db.commit()
        _vip_hook_after_subscription_change(self.db, user_id)
        return True

    def expire_subscription(self, user_id: int) -> bool:
        """Mark user's subscription as expired."""
        try:
            subscription = self.get_active_subscription(user_id)
            if not subscription:
                logger.warning(f"No active subscription found for user {user_id}")
                return False
            
            subscription.status = SubscriptionStatus.EXPIRED
            subscription.updated_at = datetime.utcnow()
            
            self.db.commit()
            logger.info(f"Expired subscription for user {user_id}")
            _vip_hook_after_subscription_change(self.db, user_id)
            return True

        except Exception as e:
            logger.error(f"Failed to expire subscription for user {user_id}: {e}")
            self.db.rollback()
            return False
    
    def cancel_subscription(self, user_id: int) -> bool:
        """Cancel user's subscription."""
        try:
            subscription = self.get_active_subscription(user_id)
            if not subscription:
                logger.warning(f"No active subscription found for user {user_id}")
                return False
            
            subscription.status = SubscriptionStatus.CANCELLED
            subscription.auto_renew = False
            subscription.updated_at = datetime.utcnow()
            subscription.cancelled_at = datetime.utcnow()
            
            self.db.commit()
            logger.info(f"Cancelled subscription for user {user_id}")
            _vip_hook_after_subscription_change(self.db, user_id)
            return True

        except Exception as e:
            logger.error(f"Failed to cancel subscription for user {user_id}: {e}")
            self.db.rollback()
            return False
    
    def create_payment_record(
        self,
        user_id: int,
        subscription_id: Optional[int],
        provider: str,
        amount: float,
        currency: str = "USD",
        external_payment_id: Optional[str] = None
    ) -> Optional[Payment]:
        """Create a new payment record."""
        try:
            payment = Payment(
                user_id=user_id,
                subscription_id=subscription_id,
                provider=provider,
                amount=amount,
                currency=currency,
                payment_status=PaymentStatus.PENDING,
                external_payment_id=external_payment_id,
            )
            
            self.db.add(payment)
            self.db.commit()
            self.db.refresh(payment)
            
            logger.info(f"Created payment record for user {user_id}: {amount} {currency}")
            return payment
            
        except Exception as e:
            logger.error(f"Failed to create payment record for user {user_id}: {e}")
            self.db.rollback()
            return None

    def get_payment_by_event_id(self, external_event_id: str) -> Optional[Payment]:
        """Return payment already linked to provider webhook event."""
        return self.db.query(Payment).filter(Payment.external_event_id == external_event_id).first()

    def process_payment_event(self, event: NormalizedPaymentEvent) -> bool:
        """
        Idempotent provider event handler.
        """
        if not event.event_id:
            logger.error("Webhook event is missing event_id")
            return False

        existing = self.get_payment_by_event_id(event.event_id)
        if existing:
            logger.info("Skipping duplicate payment event: %s", event.event_id)
            return True

        try:
            subscription = self.get_subscription_by_user(event.user_id)
            if not subscription and event.external_subscription_id:
                subscription = Subscription(
                    user_id=event.user_id,
                    plan_name=SubscriptionPlan.PREMIUM,
                    status=SubscriptionStatus.INACTIVE,
                    payment_provider=event.provider,
                    external_subscription_id=event.external_subscription_id,
                    provider_customer_id=event.external_customer_id,
                )
                self.db.add(subscription)
                self.db.flush()

            payment = Payment(
                user_id=event.user_id,
                subscription_id=subscription.id if subscription else None,
                provider=event.provider,
                amount=event.amount or 0.0,
                currency=event.currency,
                payment_status=PaymentStatus.PAID if event.status == PaymentStatus.PAID else (
                    PaymentStatus.FAILED if event.status == PaymentStatus.FAILED else PaymentStatus.PENDING
                ),
                external_payment_id=event.external_payment_id,
                external_event_id=event.event_id,
                paid_at=datetime.utcnow() if event.status == PaymentStatus.PAID else None,
            )
            self.db.add(payment)

            if subscription:
                subscription.provider_customer_id = event.external_customer_id or subscription.provider_customer_id
                subscription.external_subscription_id = (
                    event.external_subscription_id or subscription.external_subscription_id
                )

                if event.event_type in {"payment.succeeded", "checkout.session.completed", "invoice.paid"}:
                    now = datetime.utcnow()
                    subscription.status = SubscriptionStatus.ACTIVE
                    subscription.activated_at = now
                    subscription.start_date = subscription.start_date or now
                    subscription.end_date = now + timedelta(days=30)
                    subscription.grace_until = subscription.end_date + timedelta(days=3)
                elif event.event_type in {"payment.failed", "invoice.payment_failed"}:
                    subscription.status = SubscriptionStatus.INACTIVE
                elif event.event_type in {"subscription.renewed"}:
                    now = datetime.utcnow()
                    subscription.status = SubscriptionStatus.ACTIVE
                    subscription.end_date = now + timedelta(days=30)
                    subscription.grace_until = subscription.end_date + timedelta(days=3)
                elif event.event_type in {"subscription.cancelled"}:
                    subscription.status = SubscriptionStatus.CANCELLED
                    subscription.cancelled_at = datetime.utcnow()
                elif event.event_type in {"subscription.expired"}:
                    subscription.status = SubscriptionStatus.EXPIRED

            self.db.commit()
            logger.info("Processed payment event %s for user %s", event.event_id, event.user_id)
            _vip_hook_after_subscription_change(self.db, event.user_id)
            return True
        except Exception as e:
            logger.error(f"Failed to process payment event {event.event_id}: {e}")
            self.db.rollback()
            return False
    
    def update_payment_status(
        self,
        payment_id: int,
        status: str,
        paid_at: Optional[datetime] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """Update payment status."""
        try:
            payment = self.db.query(Payment).filter(Payment.id == payment_id).first()
            if not payment:
                logger.error(f"Payment {payment_id} not found")
                return False
            
            payment.payment_status = status
            payment.updated_at = datetime.utcnow()
            
            if paid_at:
                payment.paid_at = paid_at
            
            if error_message:
                payment.error_message = error_message
            
            self.db.commit()
            logger.info(f"Updated payment {payment_id} status to {status}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update payment {payment_id} status: {e}")
            self.db.rollback()
            return False
    
    def check_subscription_access(self, user_id: int) -> bool:
        """Check if user has subscription access."""
        subscription = self.get_subscription_by_user(user_id)
        if not subscription:
            return False
        if subscription.status == SubscriptionStatus.ACTIVE:
            return True
        if subscription.status == SubscriptionStatus.GRACE and subscription.grace_until:
            return subscription.grace_until > datetime.utcnow()
        return False
    
    def get_expired_subscriptions(self) -> List[Subscription]:
        """Get all subscriptions that should be expired."""
        return self.db.query(Subscription).filter(
            Subscription.status == SubscriptionStatus.ACTIVE,
            Subscription.end_date <= datetime.utcnow()
        ).all()
    
    def get_subscription_snapshot(self, user_id: int, user: Optional[User] = None) -> Dict[str, Any]:
        """Read-only snapshot for UX and admin tools."""
        if user is None:
            user = self.db.query(User).filter(User.telegram_id == user_id).first()
        sub = self.get_subscription_by_user(user_id)
        return {
            "user_exists": user is not None,
            "user_status": user.status if user else None,
            "subscription_status": str(sub.status) if sub else None,
            "plan_name": sub.plan_name if sub else None,
            "end_date": sub.end_date if sub else None,
            "grace_until": sub.grace_until if sub else None,
            "payment_provider": sub.payment_provider if sub else None,
            "subscription_db_id": sub.id if sub else None,
        }

    def admin_log_subscription_op(
        self,
        op: str,
        *,
        target_user_id: int,
        admin_user_id: int,
        ok: bool,
        detail: str = "",
    ) -> None:
        logger.info(
            "ADMIN_SUBSCRIPTION op=%s target_user_id=%s admin_user_id=%s ok=%s detail=%s",
            op,
            target_user_id,
            admin_user_id,
            ok,
            detail,
        )

    def admin_activate_subscription(
        self,
        user_id: int,
        *,
        admin_user_id: int,
        plan_name: str = SubscriptionPlan.PREMIUM.value,
        payment_provider: str = "ADMIN",
    ) -> bool:
        sub = self.activate_subscription(
            user_id,
            plan_name,
            payment_provider,
            external_subscription_id=f"admin_{user_id}_{int(datetime.utcnow().timestamp())}",
        )
        ok = sub is not None
        self.admin_log_subscription_op(
            "activate",
            target_user_id=user_id,
            admin_user_id=admin_user_id,
            ok=ok,
            detail=f"plan={plan_name}" if ok else "activate_failed",
        )
        return ok

    def force_expire_subscription(self, user_id: int, *, admin_user_id: int) -> bool:
        """Mark latest subscription EXPIRED regardless of time window (admin)."""
        try:
            sub = self.get_subscription_by_user(user_id)
            if not sub:
                self.admin_log_subscription_op(
                    "force_expire",
                    target_user_id=user_id,
                    admin_user_id=admin_user_id,
                    ok=False,
                    detail="no_subscription",
                )
                return False
            sub.status = SubscriptionStatus.EXPIRED
            sub.updated_at = datetime.utcnow()
            self.db.commit()
            _vip_hook_after_subscription_change(self.db, user_id)
            self.admin_log_subscription_op(
                "force_expire",
                target_user_id=user_id,
                admin_user_id=admin_user_id,
                ok=True,
                detail=f"sub_id={sub.id}",
            )
            return True
        except Exception as e:
            logger.error("force_expire_subscription failed user_id=%s: %s", user_id, e)
            self.db.rollback()
            self.admin_log_subscription_op(
                "force_expire",
                target_user_id=user_id,
                admin_user_id=admin_user_id,
                ok=False,
                detail=str(e),
            )
            return False

    def admin_move_to_grace(self, user_id: int, *, admin_user_id: int, grace_days: int = 3) -> bool:
        ok = self.move_to_grace(user_id, grace_days=grace_days)
        self.admin_log_subscription_op(
            "grace",
            target_user_id=user_id,
            admin_user_id=admin_user_id,
            ok=ok,
            detail=f"grace_days={grace_days}",
        )
        return ok
