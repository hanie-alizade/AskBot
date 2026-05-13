"""
Stripe gateway skeleton.

This is intentionally lightweight for incremental rollout.
"""

import hmac
import hashlib
import logging
import json
from typing import Dict, Any, Tuple

from .gateway import PaymentGateway
from .types import CheckoutSession, NormalizedPaymentEvent

logger = logging.getLogger(__name__)


class StripeGateway(PaymentGateway):
    def __init__(self, api_key: str, webhook_secret: str, checkout_base_url: str):
        self.api_key = api_key
        self.webhook_secret = webhook_secret
        self.checkout_base_url = checkout_base_url.rstrip("/")

    def create_checkout_session(self, user_id: int, plan_code: str) -> CheckoutSession:
        # Placeholder URL until Stripe SDK/API call is wired.
        checkout_url = f"{self.checkout_base_url}/checkout?provider=stripe&user_id={user_id}&plan={plan_code}"
        return CheckoutSession(checkout_url=checkout_url)

    def verify_webhook(self, payload: bytes, signature: str) -> bool:
        if not self.webhook_secret or not signature:
            return False
        expected = hmac.new(
            self.webhook_secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    def normalize_event(self, payload: Dict[str, Any]) -> NormalizedPaymentEvent:
        event_id = str(payload.get("id", ""))
        event_type = str(payload.get("type", "unknown"))
        data = payload.get("data", {}).get("object", {})
        metadata = data.get("metadata", {}) or {}
        user_id = int(metadata.get("telegram_user_id", 0))

        amount_cents = data.get("amount_total") or data.get("amount_paid")
        amount = (float(amount_cents) / 100.0) if amount_cents is not None else None
        currency = str((data.get("currency") or "usd")).upper()

        status = "PENDING"
        if event_type in {"checkout.session.completed", "invoice.paid"}:
            status = "PAID"
        elif event_type in {"invoice.payment_failed", "checkout.session.expired"}:
            status = "FAILED"

        return NormalizedPaymentEvent(
            event_id=event_id,
            event_type=event_type,
            user_id=user_id,
            status=status,
            provider="STRIPE",
            amount=amount,
            currency=currency,
            external_payment_id=data.get("payment_intent"),
            external_subscription_id=data.get("subscription"),
            external_customer_id=data.get("customer"),
            raw_payload=payload,
        )

    def build_webhook_payload(self, event_type: str, user_id: int, plan_code: str = "PREMIUM") -> Tuple[bytes, str]:
        payload = {
            "id": f"evt_stub_{user_id}_{event_type}",
            "type": event_type,
            "data": {
                "object": {
                    "currency": "usd",
                    "amount_paid": 1000,
                    "metadata": {
                        "telegram_user_id": str(user_id),
                        "plan_code": plan_code,
                    },
                }
            },
        }
        payload_raw = json.dumps(payload).encode("utf-8")
        signature = ""
        if self.webhook_secret:
            signature = hmac.new(
                self.webhook_secret.encode("utf-8"),
                payload_raw,
                hashlib.sha256,
            ).hexdigest()
        return payload_raw, signature
