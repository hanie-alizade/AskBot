"""
Mock payment provider for local development and testability.
"""

import hashlib
import hmac
import json
import time
import uuid
from typing import Dict, Any, Tuple

from .gateway import PaymentGateway
from .types import CheckoutSession, NormalizedPaymentEvent


class MockGateway(PaymentGateway):
    """
    Fake Stripe-like gateway that simulates payments without external services.
    """

    PROVIDER_NAME = "MOCK_STRIPE"

    def __init__(self, webhook_secret: str = "mock_secret", checkout_base_url: str = "https://mock.checkout"):
        self.webhook_secret = webhook_secret
        self.checkout_base_url = checkout_base_url.rstrip("/")

    def create_checkout_session(self, user_id: int, plan_code: str) -> CheckoutSession:
        fake_sub_id = f"sub_mock_{user_id}_{int(time.time())}"
        fake_customer_id = f"cus_mock_{user_id}"
        return CheckoutSession(
            checkout_url=f"{self.checkout_base_url}/session/{uuid.uuid4()}",
            external_subscription_id=fake_sub_id,
            external_customer_id=fake_customer_id,
            metadata={"telegram_user_id": user_id, "plan_code": plan_code},
        )

    def verify_webhook(self, payload: bytes, signature: str) -> bool:
        expected = hmac.new(
            self.webhook_secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature or "")

    def normalize_event(self, payload: Dict[str, Any]) -> NormalizedPaymentEvent:
        data = payload.get("data", {})
        event_type = str(payload.get("type", ""))
        user_id = int(data.get("telegram_user_id", 0))
        plan_code = str(data.get("plan_code", "PREMIUM"))

        status = "PENDING"
        if event_type in {"payment.succeeded", "subscription.renewed"}:
            status = "PAID"
        elif event_type in {"payment.failed"}:
            status = "FAILED"
        elif event_type in {"subscription.cancelled", "subscription.expired"}:
            status = "CANCELLED"

        return NormalizedPaymentEvent(
            event_id=str(payload.get("id", "")),
            event_type=event_type,
            user_id=user_id,
            status=status,
            provider=self.PROVIDER_NAME,
            amount=float(data.get("amount", 10.0)),
            currency=str(data.get("currency", "USD")),
            external_payment_id=str(data.get("payment_id", "")) or None,
            external_subscription_id=str(data.get("subscription_id", "")) or f"sub_mock_{user_id}",
            external_customer_id=str(data.get("customer_id", "")) or f"cus_mock_{user_id}",
            raw_payload={"plan_code": plan_code, **payload},
        )

    def build_webhook_payload(self, event_type: str, user_id: int, plan_code: str = "PREMIUM") -> Tuple[bytes, str]:
        payload = {
            "id": f"evt_mock_{uuid.uuid4().hex}",
            "type": event_type,
            "data": {
                "telegram_user_id": user_id,
                "plan_code": plan_code,
                "amount": 10.0,
                "currency": "USD",
                "payment_id": f"pay_mock_{uuid.uuid4().hex[:12]}",
                "subscription_id": f"sub_mock_{user_id}",
                "customer_id": f"cus_mock_{user_id}",
            },
        }
        payload_raw = json.dumps(payload).encode("utf-8")
        signature = hmac.new(
            self.webhook_secret.encode("utf-8"),
            payload_raw,
            hashlib.sha256,
        ).hexdigest()
        return payload_raw, signature
