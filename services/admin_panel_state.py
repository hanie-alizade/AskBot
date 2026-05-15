"""In-memory state for admin panel (digit entry, one-shot answer compose)."""

from __future__ import annotations

from typing import Dict, Optional

_id_search_buffer: Dict[int, str] = {}
_pending_answer_qid: Dict[int, int] = {}


def get_id_search_buffer(admin_telegram_id: int) -> str:
    return _id_search_buffer.get(admin_telegram_id, "")


def set_id_search_buffer(admin_telegram_id: int, value: str) -> None:
    _id_search_buffer[admin_telegram_id] = value


def clear_id_search_buffer(admin_telegram_id: int) -> None:
    _id_search_buffer.pop(admin_telegram_id, None)


def append_id_digit(admin_telegram_id: int, digit: str) -> str:
    cur = _id_search_buffer.get(admin_telegram_id, "")
    if len(cur) >= 16:
        return cur
    cur += digit
    _id_search_buffer[admin_telegram_id] = cur
    return cur


def backspace_id_buffer(admin_telegram_id: int) -> str:
    cur = _id_search_buffer.get(admin_telegram_id, "")
    cur = cur[:-1]
    _id_search_buffer[admin_telegram_id] = cur
    return cur


def set_pending_answer(admin_telegram_id: int, question_id: int) -> None:
    _pending_answer_qid[admin_telegram_id] = question_id


def get_pending_answer(admin_telegram_id: int) -> Optional[int]:
    return _pending_answer_qid.get(admin_telegram_id)


def clear_pending_answer(admin_telegram_id: int) -> None:
    _pending_answer_qid.pop(admin_telegram_id, None)
