"""
Lightweight i18n layer for user-facing bot messages.

Use:
    from services.i18n import t, t_user
    text = t_user(user, "verify.welcome_new")
    text = t("ar", "q.limit_reached", limit=5)

Admin-facing system text, log lines, and admin-typed replies are NOT
translated — they stay in English internally.
"""

from .translator import (
    DEFAULT_LANGUAGE,
    LANGUAGE_LABELS,
    SUPPORTED_LANGUAGES,
    is_supported,
    normalize_language,
    t,
    t_user,
)

__all__ = [
    "DEFAULT_LANGUAGE",
    "LANGUAGE_LABELS",
    "SUPPORTED_LANGUAGES",
    "is_supported",
    "normalize_language",
    "t",
    "t_user",
]
