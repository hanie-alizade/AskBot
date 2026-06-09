"""
User segmentation: structured category for each user.

Stored on User.user_type (one of the values below) plus User.user_type_custom
(free text, only meaningful when user_type == "other"). Kept structural — not a
UI-only label — so we can later filter/segment (e.g. all students) and attach
per-category message templates.

This module is the single source of truth for:
  - the allowed enum values (UserType / USER_TYPE_VALUES),
  - validation (is_valid_user_type),
  - normalized segment resolution with fallback (get_user_segment),
  - human-readable admin labels (user_type_admin_label).

User-facing button/prompt copy lives in the i18n locales (category.* keys), not
here, so it stays translatable.
"""

from __future__ import annotations

from typing import Any, Optional, Tuple


class UserType:
    """Allowed values for User.user_type (plain string constants, no Enum
    coercion — the column stores/reads the value directly)."""

    STUDENTS = "students"
    WORK_PERMITS = "work_permits"
    RESIDENCY = "residency"
    OTHER = "other"


# Canonical ordering used to render the selection screen.
USER_TYPE_VALUES: Tuple[str, ...] = (
    UserType.STUDENTS,
    UserType.WORK_PERMITS,
    UserType.RESIDENCY,
    UserType.OTHER,
)

# Sentinel returned by get_user_segment when a user has no category yet
# (existing/grandfathered users, or onboarding not finished).
SEGMENT_UNSET = "unset"

# English labels for admin-facing surfaces (admin text is English by design).
_ADMIN_LABELS = {
    UserType.STUDENTS: "Students",
    UserType.WORK_PERMITS: "Work Permits",
    UserType.RESIDENCY: "Residency",
    UserType.OTHER: "Other",
}


def is_valid_user_type(value: Optional[str]) -> bool:
    """True if `value` is one of the structured enum values (excludes custom text)."""
    return value in USER_TYPE_VALUES


def get_user_segment(user: Any) -> str:
    """Return the normalized segment key for a user, with fallback handling.

    Returns one of USER_TYPE_VALUES, or SEGMENT_UNSET when the user has no
    (valid) category set. Safe on None and on objects lacking the attribute,
    so callers never need to guard.
    """
    value = getattr(user, "user_type", None) if user is not None else None
    return value if is_valid_user_type(value) else SEGMENT_UNSET


def user_type_admin_label(user: Any) -> str:
    """Human-readable category for admin views.

    For "other", appends the user's custom text when present. Returns "—" when
    no category is set, so admin layouts always have something to show.
    """
    value = getattr(user, "user_type", None) if user is not None else None
    if value == UserType.OTHER:
        custom = (getattr(user, "user_type_custom", None) or "").strip()
        return f"Other ({custom})" if custom else "Other"
    return _ADMIN_LABELS.get(value, "—")
