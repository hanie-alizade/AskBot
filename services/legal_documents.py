"""
Required legal documents and acceptance helpers.

Text is the client-provided final wording for VIP Spain Community. When wording
changes, bump the version string so existing users are re-prompted by
`missing_documents` (acceptance is only valid for the current version).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple

from database.models import User


# --- Versions ---------------------------------------------------------------

DISCLAIMER_VERSION = "v2"
TERMS_VERSION = "v2"
PRIVACY_VERSION = "v2"
LIABILITY_VERSION = "v2"


# --- Client-provided final text ---------------------------------------------

DISCLAIMER_TEXT = (
    "📄 <b>Disclaimer</b> (version v2)\n\n"
    "VIP Spain Community provides general educational and informational content "
    "related to immigration and residency matters in Spain.\n\n"
    "Information shared within the community does not constitute individualized "
    "legal advice and does not create an attorney-client relationship. "
    "Immigration laws and administrative procedures may change, and information "
    "may become outdated over time.\n\n"
    "Members should seek professional legal advice before making important legal "
    "or immigration decisions based on information shared within the community.\n\n"
    "By tapping <b>I Accept</b> you confirm you have read and agree to the disclaimer."
)

TERMS_TEXT = (
    "📄 <b>Terms &amp; Conditions</b> (version v2)\n\n"
    "By joining VIP Spain Community, you agree to the following:\n\n"
    "• Membership is personal and may not be shared, transferred, or resold.\n"
    "• Members must communicate respectfully and comply with community rules.\n"
    "• Spam, harassment, unauthorized advertising, and misleading information are prohibited.\n"
    "• Community content may not be copied, redistributed, or commercially used without permission.\n"
    "• Access may be suspended or terminated for violations of these rules.\n"
    "• Subscription fees, renewals, cancellations, and refund eligibility are governed by the terms presented at checkout.\n"
    "• Continued use of the community constitutes acceptance of any future updates to these terms.\n\n"
    "By tapping <b>I Accept</b> you confirm you have read and agree to the Terms."
)

PRIVACY_TEXT = (
    "📄 <b>Privacy Policy</b> (version v2)\n\n"
    "We collect and process limited personal information necessary to manage your "
    "membership and provide community services.\n\n"
    "This may include your Telegram username, account identifiers, membership "
    "status, and payment-related information processed through secure third-party "
    "payment providers.\n\n"
    "Your information is used solely for community management, customer support, "
    "service delivery, legal compliance, and fraud prevention. We do not sell "
    "personal data to third parties.\n\n"
    "Members may request access, correction, or deletion of their personal "
    "information by contacting the community administrators, subject to applicable "
    "legal requirements.\n\n"
    "By tapping <b>I Accept</b> you give your consent under GDPR for the data processing described."
)

LIABILITY_TEXT = (
    "📄 <b>Liability Limitation</b> (version v2)\n\n"
    "VIP Spain Community and its administrators are not responsible for decisions, "
    "actions, or outcomes resulting from the use of information shared within the "
    "community.\n\n"
    "We do not guarantee the accuracy, completeness, or continued availability of "
    "any information, service, or third-party platform, including Telegram and "
    "payment providers.\n\n"
    "To the maximum extent permitted by applicable law, VIP Spain Community shall "
    "not be liable for any indirect, incidental, special, consequential, or "
    "punitive damages arising from the use of the community or its services.\n\n"
    "Any liability, where permitted by law, shall be limited to the amount paid by "
    "the member for the applicable subscription or service.\n\n"
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
