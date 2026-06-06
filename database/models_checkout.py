"""
Persisted record of Stripe Checkout Sessions we created.

The row is written at /subscribe time so we always know which Telegram user
started which Stripe Checkout. This unlocks:

  - webhook → checkout lookup (single source of truth for idempotency)
  - skip duplicate first-invoice activation
  - operator queries: created-but-never-paid, completed-but-not-activated

Lifecycle:
  CREATED   → /subscribe created the session on Stripe
  COMPLETED → checkout.session.completed webhook arrived
  ACTIVATED → SubscriptionService successfully wrote the subscription row
  CANCELLED → (reserved; not written today — no cancel-side wiring yet)
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import Column, DateTime, Integer, String

from database.db import Base


class CheckoutSessionStatus(str, Enum):
    CREATED = "CREATED"
    COMPLETED = "COMPLETED"
    ACTIVATED = "ACTIVATED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"  # rolled past the reuse window without completion


class CheckoutSession(Base):
    __tablename__ = "checkout_sessions"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, nullable=False, index=True)

    # The Stripe Checkout Session ID (cs_test_… / cs_live_…). Unique constraint
    # is the primary defence against double webhook processing.
    stripe_session_id = Column(String(255), nullable=False, unique=True, index=True)

    # Hosted Stripe Checkout URL, stored so /subscribe can hand the same link
    # back to a user who taps /subscribe twice within the reuse window.
    checkout_url = Column(String(2048), nullable=True)

    # Populated when checkout.session.completed arrives.
    stripe_subscription_id = Column(String(255), nullable=True, index=True)
    stripe_customer_id = Column(String(255), nullable=True)

    status = Column(
        String(20),
        nullable=False,
        default=CheckoutSessionStatus.CREATED.value,
    )

    amount_total_cents = Column(Integer, nullable=True)
    currency = Column(String(3), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    completed_at = Column(DateTime, nullable=True)
    activated_at = Column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<CheckoutSession(id={self.id}, telegram_id={self.telegram_id}, "
            f"stripe_session_id={self.stripe_session_id}, status={self.status})>"
        )
