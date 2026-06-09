"""Branded HTML email templates.

Pure rendering: every function takes plain data and returns ``(subject, html)``.
No Stripe, no DB, no network — so templates are trivially unit-testable and the
look is intentionally NOT Stripe-like (own header, palette, CTAs, footer).

CTAs supported on every email:
  - "Open Telegram Bot"     -> config-provided bot URL
  - "Manage Subscription"   -> Stripe Customer Portal URL (only when available)
"""

from __future__ import annotations

import html
from typing import List, Optional, Tuple

# Palette — deliberately our own brand, not Stripe's.
_INK = "#0f172a"
_MUTED = "#64748b"
_BORDER = "#e2e8f0"
_BG = "#f1f5f9"
_PRIMARY = "#4f46e5"  # indigo — primary CTA / brand accent


def _button(label: str, url: str, *, primary: bool) -> str:
    bg = _PRIMARY if primary else "#ffffff"
    color = "#ffffff" if primary else _INK
    border = _PRIMARY if primary else _BORDER
    return (
        f'<a href="{html.escape(url, quote=True)}" '
        f'style="display:inline-block;padding:12px 22px;margin:6px 6px 0 0;'
        f'background:{bg};color:{color};text-decoration:none;border-radius:8px;'
        f'border:1px solid {border};font-weight:600;font-size:15px;">'
        f"{html.escape(label)}</a>"
    )


def _layout(
    *,
    brand: str,
    accent: str,
    preheader: str,
    heading: str,
    intro_html: str,
    detail_rows: Optional[List[Tuple[str, str]]],
    ctas: List[Tuple[str, str, bool]],
    footer_note: str,
) -> str:
    rows_html = ""
    if detail_rows:
        cells = "".join(
            f'<tr><td style="padding:6px 0;color:{_MUTED};font-size:14px;">{html.escape(label)}</td>'
            f'<td style="padding:6px 0;color:{_INK};font-size:14px;font-weight:600;text-align:right;">'
            f"{html.escape(value)}</td></tr>"
            for label, value in detail_rows
        )
        rows_html = (
            f'<table role="presentation" width="100%" '
            f'style="border-collapse:collapse;margin:18px 0;border-top:1px solid {_BORDER};'
            f'border-bottom:1px solid {_BORDER};">{cells}</table>'
        )

    buttons_html = "".join(_button(label, url, primary=primary) for label, url, primary in ctas if url)

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:{_BG};">
<span style="display:none;max-height:0;overflow:hidden;opacity:0;">{html.escape(preheader)}</span>
<table role="presentation" width="100%" style="background:{_BG};padding:24px 0;border-collapse:collapse;">
<tr><td align="center">
  <table role="presentation" width="100%" style="max-width:560px;background:#ffffff;border:1px solid {_BORDER};
    border-radius:14px;overflow:hidden;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;">
    <tr><td style="height:6px;background:{accent};"></td></tr>
    <tr><td style="padding:28px 32px 0 32px;">
      <div style="font-size:13px;letter-spacing:.08em;text-transform:uppercase;color:{_MUTED};font-weight:700;">
        {html.escape(brand)}</div>
      <h1 style="margin:10px 0 0 0;font-size:22px;line-height:1.3;color:{_INK};">{html.escape(heading)}</h1>
    </td></tr>
    <tr><td style="padding:14px 32px 0 32px;color:{_INK};font-size:15px;line-height:1.6;">{intro_html}{rows_html}</td></tr>
    <tr><td style="padding:8px 32px 28px 32px;">{buttons_html}</td></tr>
    <tr><td style="padding:18px 32px 28px 32px;border-top:1px solid {_BORDER};color:{_MUTED};font-size:12px;line-height:1.6;">
      {html.escape(footer_note)}<br>
      This is an automated message from {html.escape(brand)}. You received it because you hold a subscription with us.
    </td></tr>
  </table>
</td></tr></table>
</body></html>"""


def _ctas(bot_url: str, portal_url: Optional[str]) -> List[Tuple[str, str, bool]]:
    ctas: List[Tuple[str, str, bool]] = [("Open Telegram Bot", bot_url, True)]
    if portal_url:
        ctas.append(("Manage Subscription", portal_url, False))
    return ctas


# --------------------------------------------------------------------------- #
# Per-event templates
# --------------------------------------------------------------------------- #


def render_payment_successful(
    *, brand: str, bot_url: str, portal_url: Optional[str],
    amount: Optional[str] = None, period_end: Optional[str] = None,
) -> Tuple[str, str]:
    subject = "Payment Successful – VIP Access Activated"
    rows = []
    if amount:
        rows.append(("Amount paid", amount))
    if period_end:
        rows.append(("Access valid until", period_end))
    html_body = _layout(
        brand=brand, accent="#16a34a",
        preheader="Your payment went through and your VIP access is active.",
        heading="Payment successful 🎉",
        intro_html="<p>Thank you — your payment was received and your <strong>VIP access is now active</strong>. "
                   "Head back to the Telegram bot to start using your benefits.</p>",
        detail_rows=rows or None,
        ctas=_ctas(bot_url, portal_url),
        footer_note="Keep this email for your records.",
    )
    return subject, html_body


def render_payment_failed(
    *, brand: str, bot_url: str, portal_url: Optional[str],
    reason: Optional[str] = None, next_attempt: Optional[str] = None,
) -> Tuple[str, str]:
    subject = "Payment Failed – Action Required"
    rows = []
    if reason:
        rows.append(("Reason", reason))
    if next_attempt:
        rows.append(("Next retry", next_attempt))
    html_body = _layout(
        brand=brand, accent="#dc2626",
        preheader="We couldn't process your latest payment — please update your details.",
        heading="Payment failed – action required",
        intro_html="<p>We were unable to process your latest subscription payment. "
                   "To avoid losing VIP access, please update your payment details using the "
                   "<strong>Manage Subscription</strong> button below.</p>",
        detail_rows=rows or None,
        ctas=_ctas(bot_url, portal_url),
        footer_note="If you have already updated your card, you can ignore this message.",
    )
    return subject, html_body


def render_subscription_cancelled(
    *, brand: str, bot_url: str, portal_url: Optional[str],
    access_until: Optional[str] = None,
) -> Tuple[str, str]:
    subject = "Subscription Cancelled – Access Ended"
    rows = []
    if access_until:
        rows.append(("Access ends", access_until))
    html_body = _layout(
        brand=brand, accent="#475569",
        preheader="Your subscription has been cancelled.",
        heading="Subscription cancelled",
        intro_html="<p>Your subscription has been cancelled and your VIP access has ended"
                   + (" (or will end on the date below)" if access_until else "")
                   + ". We're sorry to see you go — you can re-subscribe any time from the Telegram bot.</p>",
        detail_rows=rows or None,
        ctas=_ctas(bot_url, portal_url),
        footer_note="Changed your mind? Re-subscribe from the bot whenever you like.",
    )
    return subject, html_body


def render_subscription_expired(
    *, brand: str, bot_url: str, portal_url: Optional[str],
    expired_on: Optional[str] = None,
) -> Tuple[str, str]:
    subject = "Subscription Expired"
    rows = []
    if expired_on:
        rows.append(("Expired on", expired_on))
    html_body = _layout(
        brand=brand, accent="#6b7280",
        preheader="Your subscription has expired and VIP access has ended.",
        heading="Subscription expired",
        intro_html="<p>Your subscription has <strong>expired</strong> and your VIP access has ended. "
                   "You can reactivate any time from the Telegram bot to restore your benefits.</p>",
        detail_rows=rows or None,
        ctas=_ctas(bot_url, portal_url),
        footer_note="Reactivate from the bot whenever you're ready.",
    )
    return subject, html_body


# Human-friendly copy per Stripe subscription status.
_STATUS_COPY = {
    "active": "Your subscription is active and your VIP access is in good standing.",
    "past_due": "Your subscription is past due. Please update your payment details to keep your VIP access.",
    "unpaid": "Your subscription is unpaid and access is at risk. Please settle the outstanding amount.",
    "canceled": "Your subscription has been cancelled. Your VIP access will end at the end of the period.",
}


def render_subscription_status_changed(
    *, brand: str, bot_url: str, portal_url: Optional[str], status: str,
) -> Tuple[str, str]:
    subject = "Subscription Status Changed"
    label = status.replace("_", " ").title()
    message = _STATUS_COPY.get(status, "Your subscription status has changed.")
    html_body = _layout(
        brand=brand, accent="#d97706",
        preheader=f"Your subscription status is now: {label}.",
        heading="Subscription status changed",
        intro_html=f"<p>{html.escape(message)}</p>",
        detail_rows=[("Current status", label)],
        ctas=_ctas(bot_url, portal_url),
        footer_note="You can review or change your plan from the Telegram bot at any time.",
    )
    return subject, html_body
