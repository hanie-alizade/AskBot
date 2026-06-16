"""Persisted webhook / payment-event processing log for admin visibility."""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, Column, DateTime, Integer, String, Text

from database.db import Base


class WebhookProcessingLog(Base):
    __tablename__ = "webhook_processing_logs"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    user_id = Column(BigInteger, nullable=True, index=True)  # stores telegram_id
    event_type = Column(String(120), nullable=True)
    success = Column(Boolean, nullable=False, default=False)
    detail = Column(Text, nullable=True)
    external_event_id = Column(String(255), nullable=True, index=True)
