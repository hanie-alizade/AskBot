"""
Payment gateway abstraction.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple
from .types import CheckoutSession, NormalizedPaymentEvent


class PaymentGateway(ABC):
    @abstractmethod
    def create_checkout_session(self, user_id: int, plan_code: str) -> CheckoutSession:
        """Create provider checkout and return a redirect URL."""

    @abstractmethod
    def verify_webhook(self, payload: bytes, signature: str) -> bool:
        """Validate provider webhook signature."""

    @abstractmethod
    def normalize_event(self, payload: Dict[str, Any]) -> NormalizedPaymentEvent:
        """Normalize provider payload into internal event format."""

    @abstractmethod
    def build_webhook_payload(self, event_type: str, user_id: int, plan_code: str = "PREMIUM") -> Tuple[bytes, str]:
        """Build provider-shaped webhook payload and matching signature."""
