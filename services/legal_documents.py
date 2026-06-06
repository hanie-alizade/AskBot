"""
Required legal documents and acceptance helpers.

All text is PLACEHOLDER. Final wording will be provided by the client and
swapped in via the constants below — when wording changes, bump the version
string so existing users are re-prompted by `missing_documents`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple

from database.models import User


# --- Versions ---------------------------------------------------------------

DISCLAIMER_VERSION = "v1"
TERMS_VERSION = "v1"
PRIVACY_VERSION = "v1"
LIABILITY_VERSION = "v1"


# --- Placeholder text (final text to be supplied by client) ----------------

DISCLAIMER_TEXT = (
    "📄 <b>Disclaimer</b> (version v1)\n\n"
    "[PLACEHOLDER — final disclaimer text will be supplied by the client.]\n\n"
    "By tapping <b>I Accept</b> you confirm you have read and agree to the disclaimer."
)

TERMS_TEXT = (
    "📄 <b>Terms &amp; Conditions</b> (version v1)\n\n"
    "[PLACEHOLDER — final Terms &amp; Conditions text will be supplied by the client.]\n\n"
    "By tapping <b>I Accept</b> you confirm you have read and agree to the Terms."
)

PRIVACY_TEXT = (
    "📄 <b>Privacy Policy</b> (version v1)\n\n"
    "[PLACEHOLDER — final Privacy Policy text will be supplied by the client.]\n\n"
    "By tapping <b>I Accept</b> you give your consent under GDPR for the data processing described."
)

LIABILITY_TEXT = (
    "📄 <b>Liability Limitation</b> (version v1)\n\n"
    "[PLACEHOLDER — final liability limitation text will be supplied by the client.]\n\n"
    "By tapping <b>I Accept</b> you agree to the liability limitations described."
)


# --- Document descriptors ---------------------------------------------------


@dataclass(frozen=True)
class LegalDocument:
    key: str           # short id used in callback data and code (disclaimer/terms/privacy/liability)
    label: str         # short human label for inline UI
    version: str
    text: str
    accepted_at_attr: str
    version_attr: str


REQUIRED_DOCUMENTS: Tuple[LegalDocument, ...] = (
    LegalDocument(
        key="disclaimer",
        label="Disclaimer",
        version=DISCLAIMER_VERSION,
        text=DISCLAIMER_TEXT,
        accepted_at_attr="disclaimer_accepted_at",
        version_attr="disclaimer_version",
    ),
    LegalDocument(
        key="terms",
        label="Terms & Conditions",
        version=TERMS_VERSION,
        text=TERMS_TEXT,
        accepted_at_attr="terms_accepted_at",
        version_attr="terms_version",
    ),
    LegalDocument(
        key="privacy",
        label="Privacy Policy",
        version=PRIVACY_VERSION,
        text=PRIVACY_TEXT,
        accepted_at_attr="privacy_accepted_at",
        version_attr="privacy_version",
    ),
    LegalDocument(
        key="liability",
        label="Liability Limitation",
        version=LIABILITY_VERSION,
        text=LIABILITY_TEXT,
        accepted_at_attr="liability_accepted_at",
        version_attr="liability_version",
    ),
)


def get_document(key: str) -> Optional[LegalDocument]:
    for d in REQUIRED_DOCUMENTS:
        if d.key == key:
            return d
    return None


def is_accepted(user: Optional[User], doc: LegalDocument) -> bool:
    if user is None:
        return False
    accepted_at = getattr(user, doc.accepted_at_attr, None)
    accepted_version = getattr(user, doc.version_attr, None)
    # Acceptance is only valid for the current published version. If the
    # document is bumped, every prior acceptance becomes stale.
    return bool(accepted_at) and accepted_version == doc.version


def missing_documents(user: Optional[User]) -> List[LegalDocument]:
    """Return every document the user has not yet accepted at its current version."""
    return [d for d in REQUIRED_DOCUMENTS if not is_accepted(user, d)]


def has_accepted_all(user: Optional[User]) -> bool:
    return not missing_documents(user)


def mark_accepted(user: User, doc: LegalDocument, *, now: Optional[datetime] = None) -> None:
    """Stamp the user as having accepted this document at its current version.

    Caller is responsible for committing. Idempotent in practice — running it
    twice just overwrites the timestamp.
    """
    setattr(user, doc.accepted_at_attr, now or datetime.utcnow())
    setattr(user, doc.version_attr, doc.version)
