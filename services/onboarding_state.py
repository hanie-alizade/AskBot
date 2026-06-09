"""In-memory onboarding state.

Currently tracks which users are mid-way through the "Other" category step and
whose next text message should be captured as their custom category.

In-memory by design (mirrors services/admin_panel_state.py): the flag is a
transient one-shot. If the process restarts while a user is typing, they simply
re-tap "Other" — no persistence needed.
"""

from __future__ import annotations

from typing import Set

_awaiting_custom_category: Set[int] = set()


def set_awaiting_custom_category(telegram_id: int) -> None:
    _awaiting_custom_category.add(telegram_id)


def is_awaiting_custom_category(telegram_id: int) -> bool:
    return telegram_id in _awaiting_custom_category


def clear_awaiting_custom_category(telegram_id: int) -> None:
    _awaiting_custom_category.discard(telegram_id)
