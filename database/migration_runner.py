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
        _ensure_sqlite_column(engine, "subscriptions", "provider_customer_id", "VARCHAR(255)")
        _ensure_sqlite_column(engine, "subscriptions", "plan_code", "VARCHAR(50)")
        _ensure_sqlite_column(engine, "subscriptions", "billing_cycle", "VARCHAR(20) DEFAULT 'MONTHLY'")
        _ensure_sqlite_column(engine, "subscriptions", "activated_at", "DATETIME")
        _ensure_sqlite_column(engine, "subscriptions", "cancelled_at", "DATETIME")
        _ensure_sqlite_column(engine, "subscriptions", "grace_until", "DATETIME")
        _ensure_sqlite_column(engine, "payments", "external_event_id", "VARCHAR(255)")

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
