"""
Question submission drafts.

A draft is the question text a user has typed but not yet classified as
QUICK or VIP_LEGAL. It is *not* a "pending question" in the admin-reply
sense — those live in the `questions` table with `status='PENDING'`.

Persisted (rather than in-memory) so the draft survives deploys, restarts,
and container recreation. One row per user; the unique constraint on
`telegram_id` enforces "one active draft per user" — a new draft from the
same user replaces the previous row in the upsert helper.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, Text

from database.db import Base


# 24h hard TTL: drafts older than this are discarded by both the read
# helpers (lazy expiry) and any future periodic sweep.
DRAFT_TTL_HOURS = 24


class QuestionSubmissionDraft(Base):
    __tablename__ = "question_submission_drafts"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, nullable=False, unique=True, index=True)
    question_text = Column(Text, nullable=False)
    created_at = Column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )

    def __repr__(self) -> str:
        return (
            f"<QuestionSubmissionDraft(telegram_id={self.telegram_id}, "
            f"created_at={self.created_at})>"
        )
