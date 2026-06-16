"""Idempotency ledger for the email notification layer.

One row per email that was *claimed* for sending. The unique `idempotency_key`
guarantees a given (user, resulting-state, snapshot) is emailed at most once,
even across concurrent webhook deliveries / processes — the DB unique
constraint is the atomic guard (insert succeeds once, duplicates raise).

This table is owned entirely by the email side-effect layer; nothing in the
subscription/state machine reads or writes it.
"""

from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, Integer, String

from database.db import Base


class EmailNotificationLog(Base):
    __tablename__ = "email_notification_log"

    id = Column(Integer, primary_key=True, index=True)
    # The dedup key: "{user_id}:{new_state}:{snapshot_fingerprint}".
    idempotency_key = Column(String(255), unique=True, index=True, nullable=False)
    user_id = Column(BigInteger, index=True, nullable=True)  # stores telegram_id
    new_state = Column(String(32), nullable=True)
    email = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
