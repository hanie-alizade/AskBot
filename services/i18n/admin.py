"""Admin-side localization layer (English + Spanish only).

Separate from the user-facing translator in `services.i18n.translator`:
  - It has its OWN message catalogs (`locales/admin/{en,es}.py`).
  - The selected language is a single global operator preference, persisted in
    the `app_settings` table (key = "admin_language") so it survives restarts.
  - English is always the default and the fallback for any missing key.

Public API:
    get_admin_text(key, language=None, **kwargs)  -> localized string
    get_admin_language()                          -> current admin language code
    set_admin_language(code)                       -> persist + return normalized code
    ADMIN_SUPPORTED_LANGUAGES, ADMIN_LANGUAGE_LABELS

When `language` is omitted, get_admin_text resolves the current persisted admin
language. The resolved value is cached in-process and refreshed on set, so the
common path does not hit the DB on every string.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from .locales.admin.en import ADMIN_MESSAGES as ADMIN_EN
from .locales.admin.es import ADMIN_MESSAGES as ADMIN_ES

logger = logging.getLogger(__name__)

ADMIN_DEFAULT_LANGUAGE = "en"
# Admin side intentionally supports ONLY English + Spanish.
ADMIN_SUPPORTED_LANGUAGES = ("en", "es")
ADMIN_LANGUAGE_LABELS = {
    "en": "🇺🇸 English",
    "es": "🇪🇸 Español",
}

_ADMIN_LOCALES: Dict[str, Dict[str, str]] = {
    "en": ADMIN_EN,
    "es": ADMIN_ES,
}

_SETTING_KEY = "admin_language"

# In-process cache of the resolved admin language. Populated lazily on first
# read and overwritten on set(); None means "not loaded yet".
_cached_language: Optional[str] = None


def admin_normalize_language(code: Optional[str]) -> str:
    """Return a supported admin language code, falling back to the default."""
    if code:
        code = code.lower()
        if code in _ADMIN_LOCALES:
            return code
    return ADMIN_DEFAULT_LANGUAGE


def get_admin_language() -> str:
    """Resolve the persisted admin language (cached). Defaults to English."""
    global _cached_language
    if _cached_language is not None:
        return _cached_language

    lang = ADMIN_DEFAULT_LANGUAGE
    try:
        from database.crud import get_app_setting
        from database.db import SessionLocal

        db = SessionLocal()
        try:
            stored = get_app_setting(db, _SETTING_KEY, None)
        finally:
            db.close()
        lang = admin_normalize_language(stored)
    except Exception as e:  # noqa: BLE001 - never let a settings read break the UI
        logger.warning("get_admin_language failed, using default: %s", e)
        lang = ADMIN_DEFAULT_LANGUAGE

    _cached_language = lang
    return lang


def set_admin_language(code: str) -> str:
    """Persist the admin language and update the cache. Returns the normalized code."""
    global _cached_language
    lang = admin_normalize_language(code)
    try:
        from database.crud import set_app_setting
        from database.db import SessionLocal

        db = SessionLocal()
        try:
            set_app_setting(db, _SETTING_KEY, lang)
        finally:
            db.close()
    except Exception as e:  # noqa: BLE001 - persistence failure shouldn't crash the UI
        logger.error("set_admin_language failed: %s", e)
    _cached_language = lang
    return lang


def get_admin_text(key: str, language: Optional[str] = None, **kwargs: Any) -> str:
    """Translate an admin key. Falls back to English for missing keys, and to the
    raw key if missing everywhere (so a typo never raises in a handler).

    `language=None` resolves the current persisted admin language.
    """
    lang = admin_normalize_language(language) if language else get_admin_language()
    bundle = _ADMIN_LOCALES[lang]
    raw = bundle.get(key)
    if raw is None:
        raw = _ADMIN_LOCALES[ADMIN_DEFAULT_LANGUAGE].get(key)
        if raw is None:
            logger.warning("Missing admin translation key: %s", key)
            return key
    if not kwargs:
        return raw
    try:
        return raw.format(**kwargs)
    except (KeyError, IndexError, ValueError) as e:
        logger.warning("Admin translation format failed key=%s lang=%s err=%s", key, lang, e)
        return raw
