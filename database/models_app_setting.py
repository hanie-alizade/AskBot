"""Generic key-value application settings store.

A tiny, single-table persistence layer for operator-level preferences that are
NOT tied to a specific user row — currently just the admin UI language. Kept
deliberately separate from `User.language` (which is each end-user's own
preference) so admin-facing choices never collide with user-facing ones.

One row per setting; the `key` is the primary key, so reads/writes are simple
upserts. Survives restarts (it is a normal DB table).
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, String

from database.db import Base


class AppSetting(Base):
    __tablename__ = "app_settings"

    key = Column(String(64), primary_key=True, index=True)
    value = Column(String(255), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
