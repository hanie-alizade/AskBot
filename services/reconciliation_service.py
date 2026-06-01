"""
Entitlement reconciliation logging.
"""

import logging
from sqlalchemy.orm import Session

from database.models import User
from .entitlement_policy import EntitlementPolicy, log_entitlement_decision

logger = logging.getLogger(__name__)


class ReconciliationService:
    """Logs entitlement mismatches during phased rollout."""

    def __init__(self, db: Session):
        self.db = db
        self.policy = EntitlementPolicy()

    def log_user_entitlement_state(self, telegram_id: int) -> None:
        user = self.db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            return

        allowed = self.policy.can_access_vip(user)
        if user.status == "APPROVED" and not allowed:
            expl = self.policy.explain_question_entitlement(user)
            log_entitlement_decision(logger, expl, user.telegram_id)
            logger.warning(
                "Entitlement mismatch (approved user denied): user_id=%s reason=%s",
                user.telegram_id,
                expl.reason,
            )
