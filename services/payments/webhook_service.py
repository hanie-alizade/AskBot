"""
Webhook processing service with idempotency protection.
"""

import json
import logging
from sqlalchemy.orm import Session

from database.crud import append_webhook_processing_log
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
            append_webhook_processing_log(
                self.db,
                user_id=None,
                event_type=None,
                success=False,
                detail="invalid_signature",
                external_event_id=None,
            )
            return False

        payload = json.loads(payload_raw.decode("utf-8"))
        event = self.gateway.normalize_event(payload)
        ok = self.subscription_service.process_payment_event(event)
        append_webhook_processing_log(
            self.db,
            user_id=event.user_id,
            event_type=event.event_type,
            success=ok,
            detail="ok" if ok else "rejected_or_failed",
            external_event_id=event.event_id,
        )
        return ok

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
