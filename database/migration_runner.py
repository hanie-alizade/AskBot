"""
Lightweight migration runner for baseline schema hardening.

This project already uses SQLAlchemy metadata creation for bootstrap.
To keep upgrades safe in existing SQLite deployments, this module
adds missing columns/indexes in an idempotent way.
"""

import logging
from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def _sqlite_table_columns(engine: Engine, table_name: str) -> set[str]:
    with engine.connect() as conn:
        rows = conn.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
    return {row[1] for row in rows}


def _ensure_sqlite_column(engine: Engine, table_name: str, column_name: str, ddl_fragment: str) -> None:
    columns = _sqlite_table_columns(engine, table_name)
    if column_name in columns:
        return

    statement = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl_fragment}"
    with engine.begin() as conn:
        conn.execute(text(statement))
    logger.info("Added missing column %s.%s", table_name, column_name)


def _ensure_sqlite_column_with_backfill(
    engine: Engine,
    table_name: str,
    column_name: str,
    ddl_fragment: str,
    backfill_sql: str,
) -> None:
    """
    Add a column and run a one-time backfill in the same transaction.

    The outer column-existence check guarantees the backfill runs exactly once,
    so brand-new rows created later are not retroactively modified.
    """
    columns = _sqlite_table_columns(engine, table_name)
    if column_name in columns:
        return

    add_stmt = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl_fragment}"
    with engine.begin() as conn:
        conn.execute(text(add_stmt))
        conn.execute(text(backfill_sql))
    logger.info("Added column %s.%s and applied one-time backfill", table_name, column_name)


def _ensure_index(engine: Engine, index_name: str, table_name: str, columns: str, unique: bool = False) -> None:
    prefix = "UNIQUE " if unique else ""
    statement = f"CREATE {prefix}INDEX IF NOT EXISTS {index_name} ON {table_name} ({columns})"
    try:
        with engine.begin() as conn:
            conn.execute(text(statement))
    except Exception as e:
        logger.warning("Could not create index %s: %s", index_name, e)


def run_baseline_migrations(engine: Engine) -> None:
    """
    Apply idempotent baseline migrations for subscription/payment schema.
    """
    dialect = engine.dialect.name
    if dialect == "sqlite":
        _ensure_sqlite_column(engine, "users", "vip_invite_sent_at", "DATETIME")
        _ensure_sqlite_column(engine, "users", "vip_sub_invalid_since", "DATETIME")
        _ensure_sqlite_column(engine, "users", "vip_billing_removal_at", "DATETIME")
        # Legal-acceptance gate columns (client document, June 2026).
        _ensure_sqlite_column(engine, "users", "disclaimer_accepted_at", "DATETIME")
        _ensure_sqlite_column(engine, "users", "disclaimer_version", "VARCHAR(32)")
        _ensure_sqlite_column(engine, "users", "terms_accepted_at", "DATETIME")
        _ensure_sqlite_column(engine, "users", "terms_version", "VARCHAR(32)")
        _ensure_sqlite_column(engine, "users", "privacy_accepted_at", "DATETIME")
        _ensure_sqlite_column(engine, "users", "privacy_version", "VARCHAR(32)")
        _ensure_sqlite_column(engine, "users", "liability_accepted_at", "DATETIME")
        _ensure_sqlite_column(engine, "users", "liability_version", "VARCHAR(32)")
        # VIP Legal question quota: shift legacy default 5/day to new 2/month.
        # Idempotent: only touches rows still at the previous default.
        try:
            with engine.begin() as conn:
                result = conn.execute(
                    text("UPDATE users SET question_limit = 2 WHERE question_limit = 5")
                )
                if result.rowcount:
                    logger.info(
                        "Backfilled %s users from question_limit=5 (daily) to question_limit=2 (monthly)",
                        result.rowcount,
                    )
        except Exception as e:
            logger.warning("question_limit backfill skipped: %s", e)
        # Existing users keep working in English by default; new rows stay NULL
        # so the first-time language picker is shown on next /start.
        _ensure_sqlite_column_with_backfill(
            engine,
            "users",
            "language",
            "VARCHAR(8)",
            "UPDATE users SET language = 'en' WHERE language IS NULL",
        )
        # User segmentation (services/user_segment.py). Nullable, no backfill:
        # existing users stay NULL (grandfathered) and are not forced to pick.
        _ensure_sqlite_column(engine, "users", "user_type", "VARCHAR(32)")
        _ensure_sqlite_column(engine, "users", "user_type_custom", "VARCHAR(255)")
        _ensure_sqlite_column(engine, "subscriptions", "provider_customer_id", "VARCHAR(255)")
        _ensure_sqlite_column(engine, "subscriptions", "plan_code", "VARCHAR(50)")
        _ensure_sqlite_column(engine, "subscriptions", "billing_cycle", "VARCHAR(20) DEFAULT 'MONTHLY'")
        _ensure_sqlite_column(engine, "subscriptions", "activated_at", "DATETIME")
        _ensure_sqlite_column(engine, "subscriptions", "cancelled_at", "DATETIME")
        _ensure_sqlite_column(engine, "subscriptions", "grace_until", "DATETIME")
        # Failed-payment forensics (invoice.payment_failed handler).
        _ensure_sqlite_column(engine, "subscriptions", "last_failed_payment_at", "DATETIME")
        _ensure_sqlite_column(engine, "subscriptions", "last_failure_reason", "VARCHAR(255)")
        _ensure_sqlite_column(engine, "subscriptions", "last_failure_event_id", "VARCHAR(255)")
        _ensure_sqlite_column(engine, "payments", "external_event_id", "VARCHAR(255)")
        # Checkout URL persistence (double-payment reuse window).
        _ensure_sqlite_column(engine, "checkout_sessions", "checkout_url", "VARCHAR(2048)")
        # Question type chosen by user (QUICK | VIP_LEGAL). Historic rows
        # backfill to VIP_LEGAL so they preserve their original quota behaviour.
        _ensure_sqlite_column_with_backfill(
            engine,
            "questions",
            "question_type",
            "VARCHAR(16) DEFAULT 'VIP_LEGAL'",
            "UPDATE questions SET question_type = 'VIP_LEGAL' WHERE question_type IS NULL",
        )

    _ensure_index(engine, "ix_subscriptions_provider_customer_id", "subscriptions", "provider_customer_id")
    _ensure_index(engine, "ix_subscriptions_plan_code", "subscriptions", "plan_code")
    _ensure_index(
        engine,
        "uq_subscriptions_provider_external_subscription",
        "subscriptions",
        "payment_provider, external_subscription_id",
        unique=True,
    )
    _ensure_index(
        engine,
        "uq_payments_provider_external_payment",
        "payments",
        "provider, external_payment_id",
        unique=True,
    )
    _ensure_index(engine, "uq_payments_external_event_id", "payments", "external_event_id", unique=True)
