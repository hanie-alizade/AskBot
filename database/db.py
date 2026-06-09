"""
Database configuration and session management for AskBot.
Handles SQLAlchemy setup and database connections.
"""

import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create database engine
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ask_bot.db")

engine = create_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL logging in development
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    pool_pre_ping=True,  # Check connection health
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def init_db() -> None:
    """Initialize database tables."""
    from .models import User
    from .models_subscription import Subscription, Payment
    from .models_webhook import WebhookProcessingLog  # noqa: F401
    from .models_checkout import CheckoutSession  # noqa: F401
    from .models_question_draft import QuestionSubmissionDraft  # noqa: F401
    from .models_email_idempotency import EmailNotificationLog  # noqa: F401
    from .migration_runner import run_baseline_migrations
    
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        run_baseline_migrations(engine)
        logger = logging.getLogger(__name__)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error creating database tables: {e}")


def get_db() -> Session:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
