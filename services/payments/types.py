"""
Payment provider common DTOs.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class CheckoutSession:
    checkout_url: str
    external_subscription_id: Optional[str] = None
    external_customer_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class NormalizedPaymentEvent:
    event_id: str
    event_type: str
    user_id: int
    status: str
    provider: str
    amount: Optional[float] = None
    currency: str = "USD"
    external_payment_id: Optional[str] = None
    external_subscription_id: Optional[str] = None
    external_customer_id: Optional[str] = None
    raw_payload: Optional[Dict[str, Any]] = None
    # Stripe-authoritative billing period boundaries. Used to set
    # subscription.start_date / end_date instead of a local now+30d guess.
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    # Failure forensics for invoice.payment_failed.
    failure_reason: Optional[str] = None
