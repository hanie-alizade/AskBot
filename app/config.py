"""
Configuration module for the Telegram bot.
Handles loading environment variables and application settings.
"""

import os
from typing import Optional
from dotenv import load_dotenv

from config.stripe_config import stripe_config

# Load environment variables from .env file
load_dotenv()


class BotConfig:
    """Bot configuration class."""
    
    def __init__(self):
        self.bot_token: str = self._get_required_env("BOT_TOKEN")
        self.admin_id: int = int(self._get_required_env("ADMIN_ID"))
        self.group_invite_link: str = self._get_required_env("GROUP_INVITE_LINK")
        self.vip_group_id: int = int(self._get_optional_env("VIP_GROUP_ID", "0"))
        self.subscription_enforcement_enabled: bool = self._get_optional_bool_env(
            "SUBSCRIPTION_ENFORCEMENT_ENABLED", False
        )
        self.subscription_grandfather_enabled: bool = self._get_optional_bool_env(
            "SUBSCRIPTION_GRANDFATHER_ENABLED", True
        )
        # Default False so production deployments never silently fall back to
        # mock payments when the env var is missing. Tests / local dev that
        # want mock behavior must set MOCK_PAYMENT_ENABLED=true explicitly.
        self.mock_payment_enabled: bool = self._get_optional_bool_env("MOCK_PAYMENT_ENABLED", False)
        # Legacy env: kept for .env compatibility. Does not affect entitlement;
        # mock mode only routes checkout/webhooks via the payment factory.
        self.mock_subscription_active_by_default: bool = self._get_optional_bool_env(
            "MOCK_SUBSCRIPTION_ACTIVE_BY_DEFAULT", True
        )
        # Stripe credentials come from the centralized config.stripe_config layer,
        # which selects TEST vs LIVE keys based on STRIPE_LIVE_MODE (default LIVE).
        # Mirrored here so every existing `config.stripe_*` reader transparently
        # gets the mode-correct value. Do NOT read STRIPE_* env vars directly
        # elsewhere — this is the single source of truth.
        self.stripe_live_mode: bool = stripe_config.is_live_mode
        self.stripe_mode_name: str = stripe_config.mode_name  # "LIVE" | "TEST"
        self.stripe_secret_key: str = stripe_config.stripe_secret_key
        self.stripe_price_id: str = stripe_config.stripe_price_id
        self.stripe_webhook_secret: str = stripe_config.stripe_webhook_secret
        # Public base URL of this deployment (no trailing slash), used to build
        # Stripe redirect targets. Production MUST set BASE_URL to the live host
        # (e.g. https://your-service.onrender.com). The localhost default keeps
        # local dev working without extra config and never silently points at a
        # real deployment.
        self.base_url: str = self._get_optional_env(
            "BASE_URL", "http://localhost:10000"
        ).rstrip("/")
        # Stripe redirect targets. Each may be overridden individually; otherwise
        # they derive from BASE_URL so a single var configures the whole flow.
        self.payment_success_url: str = self._get_optional_env(
            "PAYMENT_SUCCESS_URL", f"{self.base_url}/payment-success"
        )
        self.payment_cancel_url: str = self._get_optional_env(
            "PAYMENT_CANCEL_URL", f"{self.base_url}/payment-cancel"
        )
        # Where Stripe redirects users after they close the Customer Portal.
        self.stripe_portal_return_url: str = self._get_optional_env(
            "STRIPE_PORTAL_RETURN_URL", f"{self.base_url}/payment-success"
        )
        self.checkout_base_url: str = self._get_optional_env("CHECKOUT_BASE_URL", "https://example.com")
        # VIP: remove from group this many seconds after subscription stops being ACTIVE/valid GRACE (default 2 days).
        self.vip_subscription_lapse_removal_delay_seconds: int = int(
            self._get_optional_env("VIP_SUBSCRIPTION_LAPSE_REMOVAL_DELAY_SECONDS", "172800")
        )
        # How many days of grace we extend after a failed renewal payment (PAST_DUE → access kept).
        self.subscription_past_due_grace_days: int = int(
            self._get_optional_env("SUBSCRIPTION_PAST_DUE_GRACE_DAYS", "3")
        )
        # How often the bot reconciles VIP bans / renewals (unban + re-invite).
        self.vip_membership_sync_interval_seconds: int = int(
            self._get_optional_env("VIP_MEMBERSHIP_SYNC_INTERVAL_SECONDS", "300")
        )

        # --- Branded email notifications (Resend) -------------------------------
        # Independent of Stripe's own receipts. If RESEND_API_KEY is empty (or the
        # `resend` package is not installed), the email layer logs and skips —
        # webhook processing is never affected.
        self.resend_api_key: str = self._get_optional_env("RESEND_API_KEY", "")
        # Verified sender. Resend's onboarding@resend.dev works without domain
        # verification for testing; use a verified domain in production.
        self.email_from: str = self._get_optional_env(
            "EMAIL_FROM", "VIP Spain Community <onboarding@resend.dev>"
        )
        self.email_notifications_enabled: bool = self._get_optional_bool_env(
            "EMAIL_NOTIFICATIONS_ENABLED", True
        )
        # Guards the /dev/email-test endpoint. Off by default so it is never
        # exposed in production unless explicitly enabled.
        self.email_test_endpoint_enabled: bool = self._get_optional_bool_env(
            "EMAIL_TEST_ENDPOINT_ENABLED", False
        )
        # Public brand + bot link used in email bodies / CTAs.
        self.brand_name: str = self._get_optional_env("BRAND_NAME", "VIP Spain Community")
        # Bot link comes from the env file (TELEGRAM_BOT_URL). Empty fallback so
        # we never ship a hardcoded URL; the email CTA omits the button if unset.
        self.telegram_bot_url: str = self._get_optional_env("TELEGRAM_BOT_URL", "")

    @staticmethod
    def _get_required_env(key: str) -> str:
        """Get required environment variable or raise ValueError."""
        value: Optional[str] = os.getenv(key)
        if value is None:
            raise ValueError(f"Required environment variable '{key}' is not set")
        return value
    
    @staticmethod
    def _get_optional_env(key: str, default: str = "") -> str:
        """Get optional environment variable with default value."""
        return os.getenv(key, default)

    @staticmethod
    def _get_optional_bool_env(key: str, default: bool = False) -> bool:
        """Get optional boolean environment variable with default value."""
        value = os.getenv(key)
        if value is None:
            return default
        return value.strip().lower() in {"1", "true", "yes", "on"}


# Global configuration instance
config = BotConfig()
