"""
Database models for AskBot.
Defines SQLAlchemy ORM models for user management.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .db import Base


class User(Base):
    """User model for storing Telegram user information."""
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True, nullable=False)
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

    # Additional fields for future features
    question_limit = Column(Integer, default=5)  # Daily question limit
    questions_used = Column(Integer, default=0)     # Questions used today
    last_question_date = Column(DateTime(timezone=True), nullable=True)  # Last question date
    
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


class Question(Base):
    """Question model for tracking user questions and admin replies."""
    
    __tablename__ = "questions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    admin_message_id = Column(Integer, nullable=True)  # Message ID sent to admin
    question_text = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="PENDING")  # PENDING, ANSWERED, etc.
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
