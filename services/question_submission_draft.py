"""
Question submission draft service.

A *draft* is the question text a user has typed but not yet classified as
QUICK or VIP_LEGAL. Drafts are short-lived (24h TTL) and stored in the
`question_submission_drafts` table so they survive deploys, restarts,
and container recreation.

This is intentionally distinct from "pending question" — that term in the
project means a question already submitted to the admin and awaiting a
reply (`Question.status='PENDING'` in `database.models`).

Public surface:
    save_draft(db, user_id, text)
    take_draft(db, user_id)      → consume + delete; None on miss/expired
    peek_draft(db, user_id)      → read-only; None on miss/expired
    discard_draft(db, user_id)
    sweep_expired_drafts(db)     → batch maintenance helper
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from database.crud import (
    clear_question_submission_draft,
    delete_stale_question_submission_drafts,
    peek_question_submission_draft,
    take_question_submission_draft,
    upsert_question_submission_draft,
)


def save_draft(db: Session, user_id: int, text: str) -> None:
    """Persist (or replace) the user's current draft. Resets the TTL clock."""
    upsert_question_submission_draft(
        db, telegram_id=user_id, question_text=text,
    )


def take_draft(db: Session, user_id: int) -> Optional[str]:
    """Read-and-delete the draft. Returns None on miss or TTL expiry."""
    return take_question_submission_draft(db, telegram_id=user_id)


def peek_draft(db: Session, user_id: int) -> Optional[str]:
    return peek_question_submission_draft(db, telegram_id=user_id)


def discard_draft(db: Session, user_id: int) -> bool:
    return clear_question_submission_draft(db, telegram_id=user_id)


def sweep_expired_drafts(db: Session) -> int:
    """Delete all rows older than the configured TTL. Returns the count."""
    return delete_stale_question_submission_drafts(db)
