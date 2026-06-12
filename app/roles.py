"""Centralized role-based routing guards (ADMIN vs USER separation).

Single source of truth for who may reach which router. Instead of repeating
`F.from_user.id == admin_id` on every handler — which is easy to forget on a new
handler and was the root cause of an admin falling into the user `/language`
onboarding flow — we bind a whole router to a role at registration time.

The bound filter runs at the router boundary for EVERY current and future
handler in that router, so authorization never depends on UI visibility or on
each handler remembering to check. Mixed routers (which legitimately serve both
roles via per-handler filters, e.g. the admin reply handler living beside user
question submission) are intentionally NOT bound here and keep their own checks.
"""

from __future__ import annotations

from typing import Optional

from aiogram import F, Router

from app.config import config


def is_admin(user_id: Optional[int]) -> bool:
    """True only for the configured admin account. The one role predicate."""
    return user_id is not None and user_id == config.admin_id


def bind_user_only(router: Router) -> None:
    """Restrict every handler in `router` to NON-admin accounts.

    Applied to user onboarding / legal / verification / language / menu /
    subscription routers so an admin can never enter a user flow.
    """
    router.message.filter(F.from_user.id != config.admin_id)
    router.callback_query.filter(F.from_user.id != config.admin_id)


def bind_admin_only(router: Router) -> None:
    """Restrict every handler in `router` to the admin account.

    Defense-in-depth for the admin panel: even if a new admin handler forgets
    its own `F.from_user.id == admin_id` filter, non-admins are blocked at the
    router boundary.
    """
    router.message.filter(F.from_user.id == config.admin_id)
    router.callback_query.filter(F.from_user.id == config.admin_id)
