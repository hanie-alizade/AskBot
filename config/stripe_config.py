"""
Centralized Stripe credential resolution — the single source of truth for which
Stripe environment (TEST vs LIVE) the whole application talks to.

Mode is chosen by the STRIPE_LIVE_MODE feature flag:

    STRIPE_LIVE_MODE=true   (or unset)  -> LIVE keys  (production default)
    STRIPE_LIVE_MODE=false              -> TEST keys  (Stripe sandbox)

Defaulting to LIVE when the flag is absent keeps existing Render deployments
working unchanged — they never silently downgrade to test mode.

This is deliberately INDEPENDENT of MOCK_PAYMENT_ENABLED. That flag controls the
fully-fake, no-network gateway used for offline development (see
services.payments.factory) and has nothing to do with which *real* Stripe
environment we authenticate against. The two can be combined freely:

    MOCK_PAYMENT_ENABLED=true                      -> fake gateway, no Stripe call
    MOCK_PAYMENT_ENABLED=false + STRIPE_LIVE_MODE=false -> real Stripe TEST
    MOCK_PAYMENT_ENABLED=false + STRIPE_LIVE_MODE=true  -> real Stripe LIVE

Backward compatibility: in LIVE mode each credential falls back to the legacy
unprefixed env names (STRIPE_SECRET_KEY / STRIPE_PRICE_ID / STRIPE_WEBHOOK_SECRET)
so deployments that only set those keep working. TEST mode never falls back to
the legacy names, because those hold live credentials and must not be used while
in test mode.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

# Idempotent: app.config also loads .env. Calling here means stripe_config is
# usable even if imported before app.config.
load_dotenv()


def _bool_env(key: str, default: bool) -> bool:
    value = os.getenv(key)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _first_nonempty(*values: str) -> str:
    """Return the first non-empty string, else ''."""
    for value in values:
        if value:
            return value
    return ""


@dataclass(frozen=True)
class StripeConfig:
    """Resolved Stripe credentials for the active mode.

    Instances are immutable snapshots taken at import time. Read the module-level
    `stripe_config` singleton everywhere instead of reading the raw env vars.
    """

    is_live_mode: bool
    stripe_secret_key: str
    stripe_price_id: str
    stripe_webhook_secret: str

    @property
    def is_test_mode(self) -> bool:
        return not self.is_live_mode

    @property
    def is_mock_mode(self) -> bool:
        """Fake, no-network gateway flag. Orthogonal to TEST/LIVE selection.

        Exposed here so callers have one place to read every payment-mode flag,
        but the canonical consumer of MOCK_PAYMENT_ENABLED remains the payment
        factory. Read fresh from env so it reflects the current process value.
        """
        return _bool_env("MOCK_PAYMENT_ENABLED", False)

    @property
    def mode_name(self) -> str:
        return "LIVE" if self.is_live_mode else "TEST"


def _load() -> StripeConfig:
    # Default True -> LIVE so a missing flag never silently downgrades production.
    is_live = _bool_env("STRIPE_LIVE_MODE", True)

    if is_live:
        secret_key = _first_nonempty(
            os.getenv("STRIPE_LIVE_SECRET_KEY", ""),
            os.getenv("STRIPE_SECRET_KEY", ""),  # legacy fallback
        )
        price_id = _first_nonempty(
            os.getenv("STRIPE_LIVE_PRICE_ID", ""),
            os.getenv("STRIPE_PRICE_ID", ""),  # legacy fallback
        )
        webhook_secret = _first_nonempty(
            os.getenv("STRIPE_LIVE_WEBHOOK_SECRET", ""),
            os.getenv("STRIPE_WEBHOOK_SECRET", ""),  # legacy fallback
        )
    else:
        # TEST mode: only the explicitly test-prefixed vars. No fallback to the
        # legacy unprefixed names — those hold live keys and must never be used
        # while in test mode.
        secret_key = os.getenv("STRIPE_TEST_SECRET_KEY", "")
        price_id = os.getenv("STRIPE_TEST_PRICE_ID", "")
        webhook_secret = os.getenv("STRIPE_TEST_WEBHOOK_SECRET", "")

    return StripeConfig(
        is_live_mode=is_live,
        stripe_secret_key=secret_key,
        stripe_price_id=price_id,
        stripe_webhook_secret=webhook_secret,
    )


# Module-level singleton — import this, do not re-read env vars elsewhere.
stripe_config = _load()
