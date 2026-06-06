"""
Configuration module for the Telegram bot.
Handles loading environment variables and application settings.
"""

import os
from typing import Optional
from dotenv import load_dotenv

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
        # Single source of truth for Stripe credentials. Env names match
        # Stripe's own dashboard wording.
        self.stripe_secret_key: str = self._get_optional_env("STRIPE_SECRET_KEY", "")
        self.stripe_price_id: str = self._get_optional_env("STRIPE_PRICE_ID", "")
        self.stripe_webhook_secret: str = self._get_optional_env("STRIPE_WEBHOOK_SECRET", "")
        # Where Stripe redirects users after they close the Customer Portal.
        self.stripe_portal_return_url: str = self._get_optional_env(
            "STRIPE_PORTAL_RETURN_URL",
            "https://askbot-uu5o.onrender.com/payment-success",
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
