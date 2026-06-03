"""
Payment gateway factory.
"""

from app.config import config
from .mock_gateway import MockGateway
from .stripe_gateway import StripeGateway


def build_stripe_gateway() -> StripeGateway:
    return StripeGateway(
        api_key=config.stripe_secret_key,
        webhook_secret=config.stripe_webhook_secret,
        checkout_base_url=config.checkout_base_url,
    )


def build_payment_gateway():
    """
    Build a gateway with mock-first behavior for local development.
    """
    if config.mock_payment_enabled or not config.stripe_secret_key:
        return MockGateway(
            webhook_secret=config.stripe_webhook_secret or "mock_secret",
            checkout_base_url=config.checkout_base_url,
        )
    return build_stripe_gateway()
