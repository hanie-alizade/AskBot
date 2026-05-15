"""
Translator core: resolve a (language, key) pair to a localized string with
English fallback when a key is missing in the requested locale.
"""

import logging
from typing import Any, Optional

from .locales.ar import MESSAGES as AR
from .locales.en import MESSAGES as EN
from .locales.es import MESSAGES as ES
from .locales.zh import MESSAGES as ZH

logger = logging.getLogger(__name__)

DEFAULT_LANGUAGE = "en"

# Order here defines the default presentation order in the language picker.
SUPPORTED_LANGUAGES = ("en", "es", "ar", "zh")

LANGUAGE_LABELS = {
    "en": "English",
    "es": "Español",
    "ar": "العربية",
    "zh": "中文",
}

_LOCALES = {
    "en": EN,
    "es": ES,
    "ar": AR,
    "zh": ZH,
}


def is_supported(code: Optional[str]) -> bool:
    return bool(code) and code in _LOCALES


def normalize_language(code: Optional[str]) -> str:
    """Return a supported language code, falling back to default."""
    if not code:
        return DEFAULT_LANGUAGE
    code = code.lower()
    if code in _LOCALES:
        return code
    return DEFAULT_LANGUAGE


def t(lang: Optional[str], key: str, **kwargs: Any) -> str:
    """
    Translate a key for the given language. Falls back to English if the key
    is missing in the target locale, and to the raw key if missing everywhere
    (prevents a runtime KeyError from breaking handlers).
    """
    code = normalize_language(lang)
    bundle = _LOCALES[code]
    raw = bundle.get(key)
    if raw is None:
        raw = _LOCALES[DEFAULT_LANGUAGE].get(key)
        if raw is None:
            logger.warning("Missing translation key: %s", key)
            return key
    if not kwargs:
        return raw
    try:
        return raw.format(**kwargs)
    except (KeyError, IndexError, ValueError) as e:
        logger.warning("Translation format failed key=%s lang=%s err=%s", key, code, e)
        return raw


def t_user(user: Any, key: str, **kwargs: Any) -> str:
    """Convenience helper when you have a `User` ORM instance handy."""
    lang = getattr(user, "language", None) if user is not None else None
    return t(lang, key, **kwargs)
