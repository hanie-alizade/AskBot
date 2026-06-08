"""In-memory state for admin panel: one-shot answer compose + user-id search.

Two independent flags per admin:
  • pending_answer_qid — admin is composing a reply to a specific question.
  • awaiting_id_search — admin tapped "Search by Telegram ID" and the next
    text message will be treated as the search input.

Mutually exclusive in practice (handlers gate on one at a time), but the
state is stored independently so transitions are explicit.
"""

from __future__ import annotations

from typing import Dict, Optional, Set

_pending_answer_qid: Dict[int, int] = {}
_awaiting_id_search: Set[int] = set()


# --- One-shot answer compose ----------------------------------------------- #


def set_pending_answer(admin_telegram_id: int, question_id: int) -> None:
    _pending_answer_qid[admin_telegram_id] = question_id


def get_pending_answer(admin_telegram_id: int) -> Optional[int]:
    return _pending_answer_qid.get(admin_telegram_id)


def clear_pending_answer(admin_telegram_id: int) -> None:
    _pending_answer_qid.pop(admin_telegram_id, None)


# --- "Search by Telegram ID" awaiting-input flag --------------------------- #


def set_awaiting_id_search(admin_telegram_id: int) -> None:
    _awaiting_id_search.add(admin_telegram_id)


def is_awaiting_id_search(admin_telegram_id: int) -> bool:
    return admin_telegram_id in _awaiting_id_search


def clear_awaiting_id_search(admin_telegram_id: int) -> None:
    _awaiting_id_search.discard(admin_telegram_id)
