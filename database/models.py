"""
Database models for AskBot.
Defines SQLAlchemy ORM models for user management.
"""

from datetime import datetime
from sqlalchemy import BigInteger, Column, Integer, String, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .db import Base


class User(Base):
    """User model for storing Telegram user information."""
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    # BigInteger: modern Telegram user IDs exceed the 32-bit INTEGER ceiling
    # (2,147,483,647). On PostgreSQL a plain Integer overflows on insert; SQLite
    # is lenient, which is why this only surfaced in production. See also every
    # other telegram_id / user_id column in this package.
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default="NEW")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    approved_at = Column(DateTime(timezone=True), nullable=True)

    # VIP group: subscription-linked membership (see services/vip_membership.py)
    vip_invite_sent_at = Column(DateTime, nullable=True)
    vip_sub_invalid_since = Column(DateTime, nullable=True)
    vip_billing_removal_at = Column(DateTime, nullable=True)

    # Preferred UI language. NULL = user has not picked yet (first-time picker shown).
    language = Column(String(8), nullable=True)

    # User segmentation (see services/user_segment.py). NULL = not chosen yet
    # (existing users are grandfathered NULL; new users pick during onboarding).
    # Allowed: students | work_permits | residency | other.
    user_type = Column(String(32), nullable=True)
    # Free text, only meaningful when user_type == "other".
    user_type_custom = Column(String(255), nullable=True)

    # VIP Legal question quota — per-month cap (per client document).
    # last_question_date now tracks the month-of-last-quota-event, not the day.
    question_limit = Column(Integer, default=2)
    questions_used = Column(Integer, default=0)
    last_question_date = Column(DateTime(timezone=True), nullable=True)

    # Legal acceptance gates onboarding. NULL = not accepted.
    # The version string lets us re-prompt when documents change.
    disclaimer_accepted_at = Column(DateTime, nullable=True)
    disclaimer_version = Column(String(32), nullable=True)
    terms_accepted_at = Column(DateTime, nullable=True)
    terms_version = Column(String(32), nullable=True)
    privacy_accepted_at = Column(DateTime, nullable=True)
    privacy_version = Column(String(32), nullable=True)
    liability_accepted_at = Column(DateTime, nullable=True)
    liability_version = Column(String(32), nullable=True)
    
    # Relationships
    subscription = relationship("Subscription", back_populates="user", uselist=False)
    payments = relationship("Payment", back_populates="user")
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, status={self.status})>"
    
    def is_new(self) -> bool:
        """Check if user is new."""
        return self.status == "NEW"
    
    def is_verified(self) -> bool:
        """Check if user is verified."""
        return self.status in ["VERIFIED", "PENDING_APPROVAL", "APPROVED", "REJECTED"]
    
    def is_pending_approval(self) -> bool:
        """Check if user is pending approval."""
        return self.status == "PENDING_APPROVAL"
    
    def is_approved(self) -> bool:
        """Check if user is approved."""
        return self.status == "APPROVED"
    
    def is_rejected(self) -> bool:
        """Check if user is rejected."""
        return self.status == "REJECTED"
    
    def has_active_subscription(self) -> bool:
        """Check if user has an active subscription."""
        if not self.subscription:
            return False
        return (
            self.subscription.status == "ACTIVE" and
            self.subscription.end_date and
            self.subscription.end_date > datetime.utcnow()
        )
    
    def subscription_expired(self) -> bool:
        """Check if user's subscription has expired."""
        if not self.subscription:
            return False
        return (
            self.subscription.end_date and
            self.subscription.end_date <= datetime.utcnow()
        )
    
    def can_access_vip(self) -> bool:
        """Check if user can access VIP features."""
        # Backward compatibility: APPROVED users still have access
        # Future: will require APPROVED + ACTIVE subscription for VIP
        if self.is_approved():
            return True
        
        # Future VIP access logic
        return self.has_active_subscription() and self.subscription.plan_name in ["PREMIUM", "VIP"]
    
    def get_effective_question_limit(self) -> int:
        """Get effective question limit based on subscription."""
        if self.has_active_subscription():
            plan = self.subscription.plan_name.upper()
            if plan == "VIP":
                return float('inf')  # Unlimited
            elif plan == "PREMIUM":
                return 50
        return self.question_limit  # Default free limit


class QuestionType:
    """Allowed values for Question.question_type.

    Plain string constants (not Enum) so the column stores the value directly
    and reads back as a string — no SQLAlchemy enum coercion needed.
    """

    QUICK = "QUICK"
    VIP_LEGAL = "VIP_LEGAL"


class QuestionStatus:
    """Allowed values for Question.status (string column, no schema change)."""

    PENDING = "PENDING"
    ANSWERED = "ANSWERED"
    FAILED_DELIVERY = "FAILED_DELIVERY"
    # Set when admin reclassifies QUICK→VIP_LEGAL but the user has already used
    # their monthly quota. The type is updated to VIP_LEGAL, but no slot is
    # consumed and the admin is told not to answer the question.
    QUOTA_BLOCKED = "QUOTA_BLOCKED"


class Question(Base):
    """Question model for tracking user questions and admin replies."""

    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, index=True, nullable=False)  # stores telegram_id
    admin_message_id = Column(Integer, nullable=True)  # Message ID sent to admin
    question_text = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="PENDING")  # PENDING, ANSWERED, etc.
    # Question type chosen by the user before submission. Historic rows
    # without a type are backfilled to VIP_LEGAL by the migration runner.
    question_type = Column(String(16), nullable=False, default=QuestionType.VIP_LEGAL)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    answered_at = Column(DateTime(timezone=True), nullable=True)
    admin_reply_text = Column(Text, nullable=True)
    
    def __repr__(self) -> str:
        return f"<Question(id={self.id}, user_id={self.user_id}, status={self.status})>"
    
    def is_pending(self) -> bool:
        """Check if question is pending."""
        return self.status == "PENDING"
    
    def is_answered(self) -> bool:
        """Check if question has been answered."""
        return self.status == "ANSWERED"
    
    def is_failed_delivery(self) -> bool:
        """Check if question failed delivery."""
        return self.status == "FAILED_DELIVERY"
