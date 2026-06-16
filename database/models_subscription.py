from datetime import datetime
from enum import Enum
from sqlalchemy import BigInteger, Column, Integer, String, DateTime, Boolean, ForeignKey, Float, Text
from sqlalchemy.orm import relationship
from database.db import Base


class SubscriptionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    GRACE = "GRACE"
    PAST_DUE = "PAST_DUE"  # payment failed, inside grace window — keep access
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"  # user cancelled; access continues until end_date
    PENDING_PAYMENT = "PENDING_PAYMENT"
    SUSPENDED = "SUSPENDED"


class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class PaymentProvider(str, Enum):
    STRIPE = "STRIPE"
    PAYPAL = "PAYPAL"
    CRYPTO = "CRYPTO"


class SubscriptionPlan(str, Enum):
    FREE = "FREE"
    PREMIUM = "PREMIUM"
    VIP = "VIP"


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    # BigInteger to match users.telegram_id (Postgres requires FK column types
    # to match the referenced column exactly).
    user_id = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=False, index=True)
    plan_name = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False, default=SubscriptionStatus.PENDING_PAYMENT)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    auto_renew = Column(Boolean, default=False)
    payment_provider = Column(String(20), nullable=True)
    provider_customer_id = Column(String(255), nullable=True, index=True)
    external_subscription_id = Column(String(255), nullable=True)
    plan_code = Column(String(50), nullable=True, index=True)
    billing_cycle = Column(String(20), nullable=True, default="MONTHLY")
    activated_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    grace_until = Column(DateTime, nullable=True)
    # Last failed-payment forensics (populated by invoice.payment_failed).
    last_failed_payment_at = Column(DateTime, nullable=True)
    last_failure_reason = Column(String(255), nullable=True)
    last_failure_event_id = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="subscription")
    payments = relationship("Payment", back_populates="subscription")

    def __repr__(self):
        return f"<Subscription(id={self.id}, user_id={self.user_id}, plan={self.plan_name}, status={self.status})>"


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    # BigInteger to match users.telegram_id (see Subscription.user_id).
    user_id = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=False, index=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True)
    provider = Column(String(20), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    payment_status = Column(String(20), nullable=False, default=PaymentStatus.PENDING)
    external_payment_id = Column(String(255), nullable=True)
    external_event_id = Column(String(255), nullable=True)
    paid_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Additional fields for error handling and retries
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)

    # Relationships
    user = relationship("User", back_populates="payments")
    subscription = relationship("Subscription", back_populates="payments")

    def __repr__(self):
        return f"<Payment(id={self.id}, user_id={self.user_id}, amount={self.amount}, status={self.payment_status})>"
