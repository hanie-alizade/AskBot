"""Top-level configuration package.

Currently exposes the centralized Stripe credential resolver. Kept separate from
`app.config` (the broad bot config) so Stripe key/mode selection lives in exactly
one place and can be imported without pulling in the rest of the bot config.
"""

from .stripe_config import StripeConfig, stripe_config

__all__ = ["StripeConfig", "stripe_config"]
