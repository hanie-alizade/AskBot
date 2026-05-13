"""
Webhook processing service with idempotency protection.
"""

import json
import logging
from sqlalchemy.orm import Session

from services.subscription_service import SubscriptionService
from .gateway import PaymentGateway

logger = logging.getLogger(__name__)


class WebhookService:
    def __init__(self, db: Session, gateway: PaymentGateway):
        self.db = db
        self.gateway = gateway
        self.subscription_service = SubscriptionService(db)

    def process(self, payload_raw: bytes, signature: str) -> bool:
        if not self.gateway.verify_webhook(payload_raw, signature):
            logger.warning("Rejected webhook due to invalid signature")
            return False

        payload = json.loads(payload_raw.decode("utf-8"))
        event = self.gateway.normalize_event(payload)
        return self.subscription_service.process_payment_event(event)

    def process_mock_event(self, event_type: str, user_id: int, plan_code: str = "PREMIUM") -> bool:
        """
        Build and process a local fake webhook event without network dependencies.
        """
        payload_raw, signature = self.gateway.build_webhook_payload(
            event_type=event_type,
            user_id=user_id,
            plan_code=plan_code,
        )
        return self.process(payload_raw, signature)
