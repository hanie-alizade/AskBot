"""
CRUD operations for AskBot database.
Handles Create, Read, Update, Delete operations for users.
"""

import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import Optional, List

from .models import User, Question
from .models_subscription import Payment, Subscription

logger = logging.getLogger(__name__)


def create_user(
    db: Session, 
    telegram_id: int, 
    username: Optional[str], 
    first_name: str,
    status: str = "NEW"
) -> User:
    """Create a new user in the database."""
    
    # Check if user already exists
    existing_user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if existing_user:
        logger.info(f"User {telegram_id} already exists, returning existing user")
        return existing_user
    
    # Create new user
    db_user = User(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        status=status
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    logger.info(f"Created new user: {telegram_id} with status: {status}")
    return db_user


def get_user(db: Session, telegram_id: int) -> Optional[User]:
    """Get user by Telegram ID."""
    return db.query(User).filter(User.telegram_id == telegram_id).first()


def update_user_status(db: Session, telegram_id: int, status: str, approved_at: Optional[datetime] = None) -> Optional[User]:
    """Update user status."""
    
    user = get_user(db, telegram_id)
    if not user:
        logger.warning(f"User {telegram_id} not found for status update")
        return None
    
    old_status = user.status
    user.status = status
    
    if status == "APPROVED" and approved_at:
        user.approved_at = approved_at
    
    db.commit()
    db.refresh(user)
    
    logger.info(f"Updated user {telegram_id} status: {old_status} -> {status}")
    return user


def get_all_users(db: Session) -> List[User]:
    """Get all users from database."""
    return db.query(User).order_by(User.created_at.desc()).all()


def get_pending_users(db: Session) -> List[User]:
    """Get all users pending approval."""
    return db.query(User).filter(User.status == "PENDING_APPROVAL").order_by(User.created_at.asc()).all()


def get_user_count_by_status(db: Session) -> dict:
    """Get count of users by status."""
    counts = {}
    statuses = ["NEW", "VERIFIED", "PENDING_APPROVAL", "APPROVED"]
    
    for status in statuses:
        count = db.query(User).filter(User.status == status).count()
        counts[status.lower()] = count
    
    return counts


def _is_new_month(last: Optional[datetime], now: datetime) -> bool:
    """True if last and now fall in different calendar months (or last is None)."""
    if last is None:
        return True
    return (last.year, last.month) != (now.year, now.month)


def increment_question_usage(db: Session, telegram_id: int) -> bool:
    """Increment user's VIP Legal question usage. Resets monthly."""

    user = get_user(db, telegram_id)
    if not user:
        return False

    now = datetime.now()

    if _is_new_month(user.last_question_date, now):
        user.questions_used = 1
        user.last_question_date = now
    else:
        if user.questions_used >= user.question_limit:
            logger.warning(
                "User %s has reached monthly VIP Legal question limit", telegram_id
            )
            return False
        user.questions_used += 1
        user.last_question_date = now

    db.commit()
    db.refresh(user)

    logger.info(
        "User %s monthly VIP Legal usage: %s/%s",
        telegram_id, user.questions_used, user.question_limit,
    )
    return True


def increment_question_usage_no_commit(db: Session, user) -> bool:
    """Increment user's VIP Legal question usage in-transaction. Resets monthly."""

    if not user:
        logger.error("User object not provided for question usage increment")
        return False

    now = datetime.now()

    if _is_new_month(user.last_question_date, now):
        user.questions_used = 1
        user.last_question_date = now
    else:
        if user.questions_used >= user.question_limit:
            logger.warning(
                "User %s has reached monthly VIP Legal question limit", user.telegram_id
            )
            return False
        user.questions_used += 1
        user.last_question_date = now

    logger.info(
        "User %s monthly VIP Legal usage incremented: %s/%s",
        user.telegram_id, user.questions_used, user.question_limit,
    )
    return True


def reset_question_limit(db: Session, telegram_id: int) -> bool:
    """Reset user's question usage (admin function)."""
    
    user = get_user(db, telegram_id)
    if not user:
        return False
    
    user.questions_used = 0
    user.last_question_date = None
    db.commit()
    db.refresh(user)
    
    logger.info(f"Reset question usage for user {telegram_id}")
    return True


# ==================== QUESTION CRUD OPERATIONS ====================

def create_question(
    db: Session,
    user_id: int,
    question_text: str,
    admin_message_id: Optional[int] = None,
    question_type: str = "VIP_LEGAL",
) -> Optional['Question']:
    """Create a new question in the database (no commit for atomic transactions).

    question_type defaults to VIP_LEGAL so any caller that doesn't yet pass
    the new field preserves the historical (quota-consuming) behaviour.
    """

    try:
        question = Question(
            user_id=user_id,
            question_text=question_text,
            admin_message_id=admin_message_id,
            status="PENDING",
            question_type=question_type,
        )

        db.add(question)
        # Don't commit here - let caller handle commit for atomic transaction
        db.flush()  # Get the ID without committing
        logger.info(
            "Created question %s for user %s type=%s",
            question.id, user_id, question_type,
        )
        return question

    except Exception as e:
        logger.error(f"Error creating question for user {user_id}: {e}")
        return None


def get_question(db: Session, question_id: int) -> Optional['Question']:
    """Get a question by ID."""
    try:
        return db.query(Question).filter(Question.id == question_id).first()
    except Exception as e:
        logger.error(f"Error getting question {question_id}: {e}")
        return None


def get_question_by_admin_message_id(db: Session, admin_message_id: int) -> Optional['Question']:
    """Get a question by admin message ID for reply mapping."""
    try:
        logger.info(f"🔍 DB QUERY: Searching for question with admin_message_id={admin_message_id}")
        question = db.query(Question).filter(Question.admin_message_id == admin_message_id).first()
        
        if question:
            logger.info(f"🔍 DB QUERY SUCCESS: Found question {question.id} for admin_message_id={admin_message_id}")
        else:
            logger.warning(f"🔍 DB QUERY FAILED: No question found for admin_message_id={admin_message_id}")
            # Log all questions in database for debugging
            all_questions = db.query(Question).all()
            logger.info(f"🔍 DEBUG: Total questions in database: {len(all_questions)}")
            for q in all_questions:
                logger.info(f"🔍 DEBUG: Question {q.id}: user_id={q.user_id}, admin_message_id={q.admin_message_id}, status={q.status}")
        
        return question
    except Exception as e:
        logger.error(f"🔍 DB ERROR: Error getting question by admin message ID {admin_message_id}: {e}")
        logger.exception("🔍 Full traceback:")
        return None


def get_pending_questions(db: Session) -> List['Question']:
    """Get all pending questions."""
    try:
        return db.query(Question).filter(Question.status == "PENDING").all()
    except Exception as e:
        logger.error(f"Error getting pending questions: {e}")
        return []


def answer_question(
    db: Session,
    question_id: int,
    admin_reply_text: str
) -> bool:
    """Answer a question with admin reply."""
    
    try:
        question = db.query(Question).filter(Question.id == question_id).first()
        if not question:
            logger.error(f"Question {question_id} not found")
            return False
        
        question.status = "ANSWERED"
        question.admin_reply_text = admin_reply_text
        question.answered_at = datetime.utcnow()
        
        db.commit()
        db.refresh(question)
        
        logger.info(f"Answered question {question_id} for user {question.user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error answering question {question_id}: {e}")
        db.rollback()
        return False


def get_user_questions(db: Session, user_id: int, limit: int = 10) -> List['Question']:
    """Get questions for a specific user."""
    try:
        return db.query(Question).filter(Question.user_id == user_id).order_by(Question.created_at.desc()).limit(limit).all()
    except Exception as e:
        logger.error(f"Error getting questions for user {user_id}: {e}")
        return []


def list_user_questions_paginated(
    db: Session,
    user_id: int,
    offset: int,
    limit: int = 5,
) -> tuple[list['Question'], int]:
    """Return (rows, total) for a user's own questions, newest first."""
    base = (
        db.query(Question)
        .filter(Question.user_id == user_id)
        .order_by(Question.created_at.desc())
    )
    total = int(base.count() or 0)
    rows = base.offset(offset).limit(limit).all()
    return rows, total


def get_user_question_by_id(
    db: Session, user_id: int, question_id: int
) -> Optional['Question']:
    """Fetch a single question — scoped to the owning user so callers can't
    look up someone else's question by guessing the id."""
    return (
        db.query(Question)
        .filter(Question.id == question_id, Question.user_id == user_id)
        .first()
    )


def check_duplicate_question(db: Session, user_id: int, question_text: str, time_window_minutes: int = 30) -> Optional['Question']:
    """Check if user sent the same question recently."""
    try:
        from datetime import datetime, timedelta
        
        # Normalize question text for comparison
        normalized_text = question_text.strip().lower()
        
        # Get recent questions from the same user
        time_threshold = datetime.utcnow() - timedelta(minutes=time_window_minutes)
        recent_questions = db.query(Question).filter(
            and_(
                Question.user_id == user_id,
                Question.created_at >= time_threshold
            )
        ).all()
        
        # Check for exact matches (normalized)
        for question in recent_questions:
            if question.question_text.strip().lower() == normalized_text:
                logger.info(f"Duplicate question detected for user {user_id}: '{question_text[:50]}...'")
                return question
        
        return None
        
    except Exception as e:
        logger.error(f"Error checking duplicate question: {e}")
        return None


def check_question_cooldown(db: Session, user_id: int, cooldown_seconds: int = 10) -> bool:
    """Check if user is on cooldown between questions."""
    try:
        from datetime import datetime, timedelta
        
        # Get the most recent question from the user
        latest_question = db.query(Question).filter(
            Question.user_id == user_id
        ).order_by(Question.created_at.desc()).first()
        
        if not latest_question:
            return True  # No previous question, no cooldown
        
        # Check if enough time has passed
        time_threshold = datetime.utcnow() - timedelta(seconds=cooldown_seconds)
        return latest_question.created_at <= time_threshold
        
    except Exception as e:
        logger.error(f"Error checking question cooldown: {e}")
        return True  # Allow question if check fails


def mark_question_failed_delivery(db: Session, question_id: int, admin_reply_text: str) -> bool:
    """Mark question as failed delivery but save the admin reply."""
    try:
        question = db.query(Question).filter(Question.id == question_id).first()
        if not question:
            logger.error(f"Question {question_id} not found for failed delivery marking")
            return False
        
        question.status = "FAILED_DELIVERY"
        question.admin_reply_text = admin_reply_text
        # Don't set answered_at since delivery failed
        
        db.commit()
        db.refresh(question)
        
        logger.info(f"Marked question {question_id} as FAILED_DELIVERY")
        return True
        
    except Exception as e:
        logger.error(f"Error marking question {question_id} as failed delivery: {e}")
        db.rollback()
        return False


def get_question_by_id(db: Session, question_id: int) -> Optional['Question']:
    """Get a question by ID."""
    try:
        return db.query(Question).filter(Question.id == question_id).first()
    except Exception as e:
        logger.error(f"Error getting question {question_id}: {e}")
        return None


def retry_failed_delivery(db: Session, question_id: int) -> Optional['Question']:
    """Get a failed delivery question for retry."""
    try:
        question = db.query(Question).filter(
            and_(
                Question.id == question_id,
                Question.status == "FAILED_DELIVERY"
            )
        ).first()
        
        if question and question.admin_reply_text:
            logger.info(f"Found failed delivery question {question_id} for retry")
            return question
        
        return None
        
    except Exception as e:
        logger.error(f"Error getting failed delivery question {question_id}: {e}")
        return None


def update_question_status(db: Session, question_id: int, status: str) -> bool:
    """Update question status."""
    try:
        question = db.query(Question).filter(Question.id == question_id).first()
        if not question:
            logger.error(f"Question {question_id} not found")
            return False
        
        question.status = status
        if status == "ANSWERED":
            question.answered_at = datetime.utcnow()
        
        db.commit()
        db.refresh(question)
        logger.info(f"Updated question {question_id} status to {status}")
        return True
        
    except Exception as e:
        logger.error(f"Error updating question {question_id} status: {e}")
        db.rollback()
        return False




def reset_user_completely(db: Session, telegram_id: int) -> bool:
    """
    Permanently remove this Telegram user and all related data (payments,
    subscriptions, questions). After success, get_user returns None until they
    use /start again and a fresh row is created.
    """
    try:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            logger.error(f"User {telegram_id} not found for reset")
            return False

        # FK order: payments reference subscriptions; both reference users.telegram_id
        pay_deleted = (
            db.query(Payment)
            .filter(Payment.user_id == telegram_id)
            .delete(synchronize_session=False)
        )
        sub_deleted = (
            db.query(Subscription)
            .filter(Subscription.user_id == telegram_id)
            .delete(synchronize_session=False)
        )
        # Question.user_id stores telegram_id (see create_question / handlers)
        q_deleted = (
            db.query(Question)
            .filter(Question.user_id == telegram_id)
            .delete(synchronize_session=False)
        )

        db.delete(user)
        db.commit()
        logger.info(
            "reset_user_completely telegram_id=%s deleted user row; "
            "payments=%s subscriptions=%s questions=%s",
            telegram_id,
            pay_deleted,
            sub_deleted,
            q_deleted,
        )
        return True

    except Exception as e:
        logger.error(f"Error resetting user {telegram_id}: {e}")
        db.rollback()
        return False


def reject_user(db: Session, telegram_id: int, reason: str = "Access denied") -> bool:
    """Reject a user's access request - production-safe implementation."""
    try:
        logger.info(f"Reject flow started for user {telegram_id}")
        
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            logger.error(f"User {telegram_id} not found for rejection")
            return False
        
        logger.info(f"Current user status for {telegram_id}: {user.status}")
        
        # Check if already rejected (idempotent)
        if user.status == "REJECTED":
            logger.info(f"User {telegram_id} is already rejected - idempotent operation")
            return True  # Already rejected, consider it success
        
        # Update status FIRST (atomic operation)
        user.status = "REJECTED"
        db.commit()
        db.refresh(user)
        
        logger.info(f"Successfully updated user {telegram_id} status to REJECTED")
        logger.info(f"Rejected user {telegram_id} with reason: {reason}")
        return True
        
    except Exception as e:
        logger.error(f"Error rejecting user {telegram_id}: {e}")
        db.rollback()
        return False


# --- Admin panel & reporting helpers ---


def append_webhook_processing_log(
    db: Session,
    *,
    user_id: Optional[int],
    event_type: Optional[str],
    success: bool,
    detail: str = "",
    external_event_id: Optional[str] = None,
) -> None:
    """Append a row for admin-visible webhook / payment-event history."""
    from database.models_webhook import WebhookProcessingLog

    try:
        row = WebhookProcessingLog(
            user_id=user_id,
            event_type=event_type,
            success=success,
            detail=(detail or "")[:4000],
            external_event_id=external_event_id,
        )
        db.add(row)
        db.commit()
    except Exception as e:
        logger.error("append_webhook_processing_log failed: %s", e)
        db.rollback()


def count_users_total(db: Session) -> int:
    return int(db.query(func.count(User.id)).scalar() or 0)


def list_users_paginated(db: Session, offset: int, limit: int = 6) -> List[User]:
    return (
        db.query(User)
        .order_by(User.telegram_id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def list_users_by_username_prefix(
    db: Session, prefix: str, offset: int, limit: int = 6
) -> tuple[List[User], int]:
    pattern = f"{prefix}%"
    base = db.query(User).filter(User.username.isnot(None), User.username.ilike(pattern))
    total = int(base.count() or 0)
    rows = base.order_by(User.username.asc()).offset(offset).limit(limit).all()
    return rows, total


def list_questions_paginated(
    db: Session, *, status: Optional[str], offset: int, limit: int = 6
) -> tuple[List[Question], int]:
    base = db.query(Question)
    if status:
        base = base.filter(Question.status == status)
    total = int(base.count() or 0)
    rows = base.order_by(Question.created_at.desc()).offset(offset).limit(limit).all()
    return rows, total


def list_subscriptions_paginated(
    db: Session, offset: int, limit: int = 6
) -> tuple[List[Subscription], int]:
    base = db.query(Subscription).order_by(Subscription.id.desc())
    total = int(base.count() or 0)
    rows = base.offset(offset).limit(limit).all()
    return rows, total


def list_payments_paginated(
    db: Session, offset: int, limit: int = 6
) -> tuple[List[Payment], int]:
    base = db.query(Payment).order_by(Payment.id.desc())
    total = int(base.count() or 0)
    rows = base.offset(offset).limit(limit).all()
    return rows, total


def count_distinct_payment_users(db: Session) -> int:
    return int(db.query(func.count(func.distinct(Payment.user_id))).scalar() or 0)


def list_latest_payment_per_user_page(
    db: Session, offset: int, limit: int = 6
) -> List[Payment]:
    subq = (
        db.query(Payment.user_id.label("uid"), func.max(Payment.id).label("mid"))
        .group_by(Payment.user_id)
        .subquery()
    )
    q = (
        db.query(Payment)
        .join(subq, (Payment.user_id == subq.c.uid) & (Payment.id == subq.c.mid))
        .order_by(Payment.id.desc())
    )
    return q.offset(offset).limit(limit).all()


def list_webhook_logs_paginated(
    db: Session, offset: int, limit: int = 6
) -> tuple[List, int]:
    from database.models_webhook import WebhookProcessingLog

    base = db.query(WebhookProcessingLog).order_by(WebhookProcessingLog.id.desc())
    total = int(base.count() or 0)
    rows = base.offset(offset).limit(limit).all()
    return rows, total


# --- Checkout session persistence ---


def create_checkout_session_record(
    db: Session,
    *,
    telegram_id: int,
    stripe_session_id: str,
    checkout_url: Optional[str] = None,
) -> "CheckoutSession":
    """Insert a CheckoutSession row in CREATED state.

    Uniqueness on stripe_session_id is enforced by a DB index; callers should
    handle IntegrityError if Stripe ever returns a duplicate id (it shouldn't).
    """
    from database.models_checkout import CheckoutSession, CheckoutSessionStatus

    row = CheckoutSession(
        telegram_id=telegram_id,
        stripe_session_id=stripe_session_id,
        status=CheckoutSessionStatus.CREATED.value,
        checkout_url=checkout_url,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_latest_checkout_for_user(
    db: Session, telegram_id: int
) -> Optional["CheckoutSession"]:
    """Most recent CheckoutSession row for this telegram_id, any status."""
    from database.models_checkout import CheckoutSession

    return (
        db.query(CheckoutSession)
        .filter(CheckoutSession.telegram_id == telegram_id)
        .order_by(CheckoutSession.id.desc())
        .first()
    )


def mark_checkout_expired(db: Session, *, stripe_session_id: str) -> bool:
    """Move a CheckoutSession to EXPIRED. Idempotent."""
    from database.models_checkout import CheckoutSession, CheckoutSessionStatus

    row = get_checkout_by_stripe_session_id(db, stripe_session_id)
    if not row:
        return False
    if row.status == CheckoutSessionStatus.CREATED.value:
        row.status = CheckoutSessionStatus.EXPIRED.value
        db.commit()
    return True


# --- Question submission drafts ---


def upsert_question_submission_draft(
    db: Session, *, telegram_id: int, question_text: str
) -> "QuestionSubmissionDraft":
    """Save (or replace) the current draft for this user.

    The unique constraint on telegram_id means a user can only have one
    active draft. Resubmitting a draft resets its 24h TTL.
    """
    from database.models_question_draft import QuestionSubmissionDraft

    row = (
        db.query(QuestionSubmissionDraft)
        .filter(QuestionSubmissionDraft.telegram_id == telegram_id)
        .first()
    )
    if row:
        row.question_text = question_text
        row.created_at = datetime.utcnow()
    else:
        row = QuestionSubmissionDraft(
            telegram_id=telegram_id,
            question_text=question_text,
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _draft_is_fresh(
    row: "QuestionSubmissionDraft", *, ttl_hours: int
) -> bool:
    return row.created_at >= datetime.utcnow() - timedelta(hours=ttl_hours)


def take_question_submission_draft(
    db: Session, *, telegram_id: int, ttl_hours: Optional[int] = None
) -> Optional[str]:
    """Atomically read-and-delete the user's draft. Returns the text or None.

    None is returned when no draft exists OR the row has aged past TTL —
    in both cases any stale row is deleted before returning.
    """
    from database.models_question_draft import QuestionSubmissionDraft, DRAFT_TTL_HOURS

    effective_ttl = ttl_hours if ttl_hours is not None else DRAFT_TTL_HOURS
    row = (
        db.query(QuestionSubmissionDraft)
        .filter(QuestionSubmissionDraft.telegram_id == telegram_id)
        .first()
    )
    if not row:
        return None
    text = row.question_text if _draft_is_fresh(row, ttl_hours=effective_ttl) else None
    db.delete(row)
    db.commit()
    return text


def peek_question_submission_draft(
    db: Session, *, telegram_id: int, ttl_hours: Optional[int] = None
) -> Optional[str]:
    """Read the draft text without consuming it. Stale rows are deleted."""
    from database.models_question_draft import QuestionSubmissionDraft, DRAFT_TTL_HOURS

    effective_ttl = ttl_hours if ttl_hours is not None else DRAFT_TTL_HOURS
    row = (
        db.query(QuestionSubmissionDraft)
        .filter(QuestionSubmissionDraft.telegram_id == telegram_id)
        .first()
    )
    if not row:
        return None
    if not _draft_is_fresh(row, ttl_hours=effective_ttl):
        db.delete(row)
        db.commit()
        return None
    return row.question_text


def clear_question_submission_draft(db: Session, *, telegram_id: int) -> bool:
    from database.models_question_draft import QuestionSubmissionDraft

    deleted = (
        db.query(QuestionSubmissionDraft)
        .filter(QuestionSubmissionDraft.telegram_id == telegram_id)
        .delete(synchronize_session=False)
    )
    db.commit()
    return bool(deleted)


def delete_stale_question_submission_drafts(
    db: Session, *, older_than: Optional[datetime] = None
) -> int:
    """Sweep helper for housekeeping. Default cutoff = TTL_HOURS ago."""
    from database.models_question_draft import QuestionSubmissionDraft, DRAFT_TTL_HOURS

    cutoff = older_than if older_than else (
        datetime.utcnow() - timedelta(hours=DRAFT_TTL_HOURS)
    )
    n = (
        db.query(QuestionSubmissionDraft)
        .filter(QuestionSubmissionDraft.created_at < cutoff)
        .delete(synchronize_session=False)
    )
    if n:
        db.commit()
    return int(n)


def expire_stale_checkout_sessions(
    db: Session, *, older_than: datetime, limit: int = 500
) -> int:
    """Bulk-mark CREATED checkouts older than the cutoff as EXPIRED.

    Returns the number of rows updated. Intended for periodic maintenance —
    not called from the request path. Operators can run this from an admin
    job to clean up abandoned checkouts.
    """
    from database.models_checkout import CheckoutSession, CheckoutSessionStatus

    rows = (
        db.query(CheckoutSession)
        .filter(
            CheckoutSession.status == CheckoutSessionStatus.CREATED.value,
            CheckoutSession.created_at < older_than,
        )
        .order_by(CheckoutSession.id.asc())
        .limit(limit)
        .all()
    )
    if not rows:
        return 0
    for row in rows:
        row.status = CheckoutSessionStatus.EXPIRED.value
    db.commit()
    return len(rows)


def get_checkout_by_stripe_session_id(
    db: Session, stripe_session_id: str
) -> Optional["CheckoutSession"]:
    from database.models_checkout import CheckoutSession

    return (
        db.query(CheckoutSession)
        .filter(CheckoutSession.stripe_session_id == stripe_session_id)
        .first()
    )


def get_checkout_by_stripe_subscription_id(
    db: Session, stripe_subscription_id: str
) -> Optional["CheckoutSession"]:
    """Look up the most recent checkout that was linked to this Stripe subscription."""
    from database.models_checkout import CheckoutSession

    return (
        db.query(CheckoutSession)
        .filter(CheckoutSession.stripe_subscription_id == stripe_subscription_id)
        .order_by(CheckoutSession.id.desc())
        .first()
    )


def mark_checkout_completed(
    db: Session,
    *,
    stripe_session_id: str,
    stripe_subscription_id: Optional[str],
    stripe_customer_id: Optional[str],
    amount_total_cents: Optional[int],
    currency: Optional[str],
) -> Optional["CheckoutSession"]:
    """Move CheckoutSession to COMPLETED and capture downstream Stripe IDs.

    Returns the updated row, or None if no matching row was found (recovery
    scenario — webhook arrived for a session we never recorded).
    """
    from database.models_checkout import CheckoutSession, CheckoutSessionStatus

    row = get_checkout_by_stripe_session_id(db, stripe_session_id)
    if not row:
        return None
    # Idempotent: only advance state forward.
    if row.status == CheckoutSessionStatus.CREATED.value:
        row.status = CheckoutSessionStatus.COMPLETED.value
        row.completed_at = datetime.utcnow()
    row.stripe_subscription_id = stripe_subscription_id or row.stripe_subscription_id
    row.stripe_customer_id = stripe_customer_id or row.stripe_customer_id
    if amount_total_cents is not None:
        row.amount_total_cents = amount_total_cents
    if currency:
        row.currency = currency.upper()
    db.commit()
    db.refresh(row)
    return row


def mark_checkout_activated(db: Session, *, stripe_session_id: str) -> bool:
    """Move CheckoutSession to ACTIVATED. Idempotent."""
    from database.models_checkout import CheckoutSession, CheckoutSessionStatus

    row = get_checkout_by_stripe_session_id(db, stripe_session_id)
    if not row:
        return False
    if row.status != CheckoutSessionStatus.ACTIVATED.value:
        row.status = CheckoutSessionStatus.ACTIVATED.value
        row.activated_at = datetime.utcnow()
        db.commit()
    return True


def list_stale_unpaid_checkouts(
    db: Session, *, older_than: datetime, limit: int = 100
) -> List["CheckoutSession"]:
    """Sessions still CREATED past the cutoff — abandoned by the user or lost upstream."""
    from database.models_checkout import CheckoutSession, CheckoutSessionStatus

    return (
        db.query(CheckoutSession)
        .filter(
            CheckoutSession.status == CheckoutSessionStatus.CREATED.value,
            CheckoutSession.created_at < older_than,
        )
        .order_by(CheckoutSession.created_at.asc())
        .limit(limit)
        .all()
    )


def list_completed_not_activated_checkouts(
    db: Session, *, limit: int = 100
) -> List["CheckoutSession"]:
    """Sessions Stripe says are paid but our subscription writer never closed."""
    from database.models_checkout import CheckoutSession, CheckoutSessionStatus

    return (
        db.query(CheckoutSession)
        .filter(CheckoutSession.status == CheckoutSessionStatus.COMPLETED.value)
        .order_by(CheckoutSession.completed_at.asc())
        .limit(limit)
        .all()
    )
