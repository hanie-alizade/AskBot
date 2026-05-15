# AskBot — Product Flow

A plain-language description of how AskBot behaves for end users and admins,
covering every major journey from first contact to renewal and beyond.

This document is intended for stakeholders, project managers, support staff,
and new team members. It deliberately avoids technical implementation detail.

---

## 1. Who AskBot is for

AskBot is a Telegram-based bot that mediates membership of a paid VIP group.

Two audiences:

- **Users** — people who want access to the VIP group and the ability to ask
  questions privately.
- **Admin** — a single trusted operator who reviews access requests, manages
  subscriptions, answers questions, and moderates the VIP group.

The VIP group itself is announcement-only. Users do not chat inside it. All
back-and-forth between users and admin happens privately with the bot.

---

## 2. Supported Languages

The bot is fully multilingual. The user picks one of four languages on first
contact, and can switch at any time:

- English
- Español
- العربية (Arabic, displayed right-to-left)
- 中文 (Simplified Chinese)

Every user-facing message, button label, menu, status string, subscription
view, and admin-to-user notification is translated. If a translation is
missing for a key, the bot falls back to English so the user is never left
with a broken screen.

The admin's own commands and admin-only menus remain in English to keep
operations predictable.

---

## 3. User Journey

### 3.1 First Interaction

1. The user finds the bot and sends `/start`.
2. Because they are brand new, the bot opens a **language picker** with four
   buttons: English / Español / العربية / 中文.
3. The user taps one. From this point onward every bot message to them is in
   that language.
4. The bot replies with a welcome screen and a small follow-up message that
   installs a **persistent menu** of three buttons at the bottom of the chat:
   - Check approval status
   - Subscription
   - Change language

These three buttons stay visible from now on, regardless of which screen the
user is looking at.

### 3.2 Verification

Right after picking a language a new user sees a single big **Verify** button.

- Tapping it marks the user as *verified* — a lightweight confirmation that
  they read the welcome and intend to proceed.
- After verification, the bot replaces the screen with a **Request Access**
  button.

### 3.3 Requesting Access

- The user taps **Request Access**.
- Their status changes to *pending approval*.
- The bot notifies the admin privately with the user's name, ID, and two
  inline buttons: **Approve** and **Reject**.
- The user is told their request is under review and to expect a notification.

### 3.4 Approval or Rejection

The admin's decision is sent back to the user as a translated private message:

- **Approved** — "Your access request was approved. Activate a plan to receive
  the VIP invite link."
- **Rejected** — "Your access request was denied. Reason: …" plus instructions
  on how to contact support if they think it's an error.

A rejected user can request access again later (after the admin resets them or
they appeal).

### 3.5 Subscription & Payment

Approval alone does not grant VIP access. The user must also have an active
subscription.

The bot supports two payment modes, chosen by configuration:

- **Mock mode** — for staging and demos. The user types `/subscribe` (or taps
  Subscription in the menu) and the subscription is activated immediately
  without any real money flow.
- **Real mode (Stripe-ready)** — the user gets a checkout link. On successful
  payment, the bot is notified and the subscription activates.

Either way, once payment succeeds the bot:

1. Activates the subscription for 30 days plus a 3-day grace buffer.
2. Lifts any prior VIP-group ban (in case this is a renewal after expiry).
3. Generates a **fresh, single-use, 30-day invite link** unique to that user
   and sends it privately.
4. Marks the user's record so future questions and group access are unlocked.

### 3.6 Joining the VIP Group

The user receives a private message that includes their personal invite link
and a short welcome line. Their welcome screen also displays a **Join VIP
Group** button with the same fresh link.

Important properties of the link:

- **Single-use** — once anyone joins through it, the link becomes inert.
- **30-day expiry** — even if unused, it dies after a month.
- **Generated per user, per delivery** — every send produces a new URL, so a
  leaked link is exposed only for one extra user, and that misuse immediately
  locks out the intended recipient.

Once the user joins the group they are simply a member; the bot doesn't
re-announce them.

### 3.7 Asking Questions (Private Chat)

To ask a question the user simply sends a text message to the bot in private
chat. The bot then:

1. Checks the user is approved.
2. Checks their subscription is active (or within the grace period).
3. Validates the question isn't empty, too short, spammy, on cooldown, or a
   recent duplicate.
4. Enforces a daily question limit.
5. Confirms receipt to the user (with the remaining quota for the day).
6. Forwards the question privately to the admin.

If any check fails, the user gets a clear translated message explaining why
and what to do (e.g. "Your subscription is inactive — use /renew").

### 3.8 Receiving Admin Replies

When the admin answers a question, the bot delivers the reply privately to
the user. The wrapper ("Your question / Response / This is a reply, you can
reply to this message…") is rendered in **the recipient's** language. The
admin's actual answer text is preserved verbatim — the bot does not translate
human-typed content.

If the user has blocked the bot, the reply is marked as *failed delivery* and
saved. The admin can re-send it later if the user unblocks.

### 3.9 Group Behaviour Restrictions

The VIP group is treated as **announcement-only**. The bot watches every
message a non-admin posts there and:

1. Deletes the message.
2. Sends the user a private DM explaining what to do instead.

The exact DM depends on the user's situation:

- **Not approved** → "Use private chat with the bot to continue onboarding."
- **Approved but no active subscription** → "You need an active subscription
  to forward questions from the group. Check /subscription."
- **Approved + active subscription** → "Would you like to send this as a
  question to the admin instead?" with Yes/No buttons. If they tap Yes the
  text is forwarded through the normal questions pipeline.
- **Non-text content** (image, sticker, file…) → cannot be forwarded as a
  question; the user is told to send text in private chat instead.

This keeps the VIP group clean and pushes all conversations into the proper
private-chat workflow.

### 3.10 Subscription Expiration

When a subscription's billing period ends, it transitions into a **grace
period** for a small number of days (currently 3). During grace the user
keeps full access — VIP membership and the ability to ask questions — and is
encouraged to renew.

After grace ends, the subscription is marked expired and the user loses
question access immediately.

### 3.11 Removal from the VIP Group

The bot does **not** kick a user the instant their subscription expires.
Instead a configurable delay applies (default 48 hours) — a buffer for
last-minute renewals. Once that delay passes without renewal, the bot:

1. Bans the user from the VIP group (banning is the cleanest way to make
   Telegram invite links stop working for them).
2. Records the removal time.

The user keeps their private chat with the bot, so they can still see
`/status`, `/subscription`, and `/renew`.

### 3.12 Renewal Flow

When a removed (or grace-period) user pays again:

1. The bot reactivates their subscription (30 days fresh).
2. It automatically lifts the VIP-group ban so invite links work again.
3. It generates a brand-new single-use invite link and DMs it to them.
4. Their welcome screen on the next `/start` again shows a **Join VIP Group**
   button with a fresh URL.

The reconciliation also runs on a background schedule, so even if the user
never opens the bot, the unban and re-invite happen automatically the moment
payment lands.

### 3.13 Rejoin After Renewal

The user simply taps the new invite link or the **Join VIP Group** button.
They re-enter the group as a normal member. The bot does not need any further
action from them.

### 3.14 Changing Language

At any time the user can:

- Tap **Change language** in the persistent menu, or
- Send `/language`.

They see the four-language picker again. After tapping a new flag, the bot
confirms in the new language and re-installs the menu with translated labels.

---

## 4. Admin Journey

The admin has a separate experience and a dedicated 4-button persistent menu:

- **User Management**
- **Questions**
- **Subscriptions & Payment**
- **System Settings**

Every admin action is **button-driven**. The only time the admin types free
text is when composing an answer to a user's question — and that text is
explicitly invited by a "Compose reply" button so there's no ambiguity.

### 4.1 Reviewing Users

Through **User Management** the admin can:

- Find a user by Telegram ID via a numeric keypad.
- Browse all users page-by-page.
- View only pending-approval users.

For any user they see a detail card with name, username, approval status,
question usage versus limit, and current subscription state.

### 4.2 Approve / Reject / Reset

From a user's detail screen the admin can:

- **Approve** a pending user (the user is notified instantly in their
  language).
- **Reject** with a reason; the user is told privately why.
- **Reset user** — wipes the user's row, subscription, payments, and
  questions. Used for full data removal. The next time that person sends
  `/start` they are treated as brand new.

Approve and Reject also appear as inline buttons attached to the access
request notification the admin received when the user first asked for
access — so the admin can act in one tap without opening the panel.

### 4.3 Viewing Statuses

Each user detail card shows:

- Approval state (NEW, VERIFIED, PENDING_APPROVAL, APPROVED, REJECTED).
- Subscription state (NONE, ACTIVE, GRACE, EXPIRED, CANCELLED, INACTIVE…).
- Plan name, period end, grace end.
- Whether they currently have permission to ask questions, plus a one-line
  reason why or why not.

### 4.4 Managing Subscriptions

From the user detail card the admin has buttons for:

- **Expire subscription** — force the subscription to EXPIRED immediately,
  regardless of dates.
- **Grace** — move the subscription into a 3-day grace window.
- **Activate sub** — admin-grant activation without a payment (useful for
  comps, support, edge-case manual fixes).
- **Remove from VIP** — ban the user from the VIP group on demand.

Any subscription change triggers the standard downstream effects: VIP
markers update, invite links regenerate on the next entitlement, removal
timers start when appropriate.

### 4.5 Handling Pending Questions

In the **Questions** section the admin can:

- View all pending questions.
- View the full question history.
- Open a single question to see the user, the question text, the timestamp,
  and the reply if any.

To answer:

1. Open a pending question.
2. Tap **Compose reply**.
3. Send the answer as the very next text message in the admin's chat.
4. The bot delivers it to the user (wrapped in their language) and marks the
   question answered.

Alternatively the admin can reply directly to the forwarded question message
the bot pushed at the time the question was asked — Telegram threads the
reply, and the bot routes it to the right user.

### 4.6 Monitoring Payments, Webhooks, and Logs

The **Subscriptions & Payment** section gives the admin:

- A paginated list of subscriptions across all users.
- A paginated list of recent payments.
- A webhook / event log showing every payment event the bot processed and
  whether it succeeded or failed.
- A "latest payment per user" view, useful for audits.

### 4.7 System Settings

A read-only screen shows the current runtime configuration:

- VIP group ID
- Whether subscription enforcement is on
- Whether mock payment is enabled
- Lapse-removal delay (how long after expiry before kicking)
- VIP reconciliation interval
- Whether real Stripe keys are configured

This lets the admin sanity-check the environment without needing developer
access.

### 4.8 Managing VIP Access

Beyond per-user banning, the bot automatically:

- Removes users whose subscriptions lapse (after the configured delay).
- Unbans users on renewal and re-issues a fresh invite link.
- Cleans up messages posted by non-admins inside the VIP group.

The admin can override any of this through the user detail card.

---

## 5. Subscription Rules — Who Gets Access?

The rules combine two independent dimensions: **approval status** and
**subscription state**.

| Approval Status   | Subscription | Can ask questions? | Can be in VIP group?     |
| ----------------- | ------------ | ------------------ | ------------------------ |
| NEW               | any          | No                 | No                       |
| VERIFIED          | any          | No                 | No                       |
| PENDING_APPROVAL  | any          | No                 | No                       |
| REJECTED          | any          | No                 | No                       |
| APPROVED          | none         | No                 | No (no invite link sent) |
| APPROVED          | ACTIVE       | **Yes**            | **Yes**                  |
| APPROVED          | GRACE (valid)| **Yes**            | **Yes**                  |
| APPROVED          | GRACE (expired) | No              | No (removal scheduled)   |
| APPROVED          | EXPIRED      | No                 | No (removal scheduled)   |
| APPROVED          | CANCELLED    | No                 | No                       |
| APPROVED          | INACTIVE     | No                 | No                       |
| APPROVED          | PENDING_PAYMENT | No              | No                       |

**Plain rule:** *You need to be APPROVED **and** have a subscription that is
ACTIVE or within a valid GRACE window to use the bot's paid features.*

The user always sees a one-line explanation of why their access is granted or
denied (e.g. "active subscription", "grace period", "subscription expired").

---

## 6. Payment & Access Logic — Step by Step

### When payment succeeds

1. The subscription is set to ACTIVE.
2. The billing period end moves to +30 days from now.
3. The grace window is set to billing end +3 days.
4. The user's VIP markers update.
5. If the user was previously banned from the VIP group for non-payment, the
   ban is automatically lifted.
6. A fresh single-use invite link is generated and DM'd to the user in their
   language.

### When payment fails

1. The subscription is set to INACTIVE.
2. The user is no longer entitled to ask questions.
3. The user remains in the VIP group temporarily (until the removal delay
   passes, see below), giving them a chance to retry payment.

### When a billing period ends without renewal

1. The subscription enters GRACE for a few days. The user still has access.
2. When grace expires, the subscription is marked EXPIRED.
3. A **lapse-removal delay** (default 48 hours) starts counting from the
   point the subscription stopped being valid.
4. When that delay elapses, the bot bans the user from the VIP group.

### When the user renews

1. Subscription goes back to ACTIVE.
2. Any standing ban is lifted automatically.
3. A new single-use 30-day invite link is sent.
4. The user can join again with one tap.

### Why the delay matters

The delay is a kindness: people sometimes pay a day or two late, especially
across time zones and bank settlements. Kicking immediately would punish
honest late-payers. The delay can be tuned per environment.

---

## 7. Navigation & UX Principles

### Button-driven everywhere

- **Users** never need to remember commands. The persistent 3-button menu
  covers the common cases (status / subscription / language). Inline buttons
  on each welcome screen guide them through verification and access requests.
- **Admins** drive everything through a 4-section reply keyboard plus deep
  inline menus.

### Minimal typing

- Users type free text only when asking a question.
- Admins type free text only when composing a reply (gated by an explicit
  Compose Reply button).
- Even user-ID lookups for the admin are done via an on-screen numeric
  keypad, not raw input.

### Clear status visibility

Any user can:

- Tap **Check approval status** in the menu, or send `/status`.
- Tap **Subscription** in the menu, or send `/subscription`.

These show plain, human-readable answers including:

- Approval state
- Subscription state and plan
- Period end date
- Grace end date
- Whether they can currently ask questions
- A one-line "reason" for the access decision
- A "next action" hint (e.g. "Try /subscribe", "Contact support")

### Persistent admin menu

The admin always sees their four-section reply keyboard. Sub-menus are inline
and scoped to the action at hand. There's no hidden state — pressing Home
or Back is always one tap away.

### Clean separation between group and private chat

- **VIP group** = announcements only. Non-admin messages are removed.
- **Private chat with the bot** = where onboarding, billing, questions, and
  replies all happen.

This separation is intentional. It keeps the VIP group readable and pushes
support traffic into a one-on-one channel.

---

## 8. Edge Cases & Special Scenarios

### 8.1 Expired Subscription

The user keeps their private chat with the bot but cannot ask questions and
is eventually removed from the VIP group. Sending `/start` shows the
"approved but no subscription" welcome with a hint to renew.

### 8.2 Grace Period

For three days after the billing period ends the user retains full access.
This window is meant for honest late-payers and to absorb payment-processor
delays. During grace, `/subscription` shows the grace state and the date it
ends.

### 8.3 Shared Invite Links

Each invite link is **single-use** and tied to one person for thirty days.
If a user forwards the link to a friend:

- The first person to use it joins.
- The link immediately becomes inert.
- If the friend joined first, the legitimate recipient is locked out — which
  is an obvious signal of misuse and prompts support contact.

The user is never given the static, group-wide invite link; the bot mints a
fresh personal one every time it sends them an invite.

### 8.4 User Leaves the Group Voluntarily

Nothing is automatically revoked. The user can rejoin the next time their
welcome screen offers a Join VIP Group button (which generates a fresh link),
provided their subscription is still active or in grace.

### 8.5 User Tries to Ask a Question Without Access

They get a clear translated message describing exactly why:

- "You need to be approved" → run `/start` to begin verification.
- "Your subscription is inactive or expired" → run `/renew`.

The message tells them the next step in one sentence.

### 8.6 Approved But Unpaid

The user is welcomed and told they are approved. The "Join VIP Group" button
is replaced by a **Subscription** button until they activate a plan. Their
status shows: *Approved + no active subscription*. The bot never sends them
the invite link until payment lands.

### 8.7 User Blocked the Bot

If the admin tries to deliver a reply but the user has blocked the bot, the
reply is marked *failed delivery* and saved. The admin gets an alert and can
retry once the user unblocks.

### 8.8 Admin Removes a User Manually

The admin can ban a user from the VIP group through the user detail card.
The bot records the removal. On renewal — or via an explicit admin reset —
the user can be brought back through the normal flow.

### 8.9 Admin Resets a User

Resetting wipes the user's row entirely. They appear to the system as a
brand-new person on their next `/start` (including the language picker).
This is used for full data removal or fresh-start cases.

### 8.10 First-time Language Pick After Migration

Existing users who pre-dated multilingual support default to English. They
will not be forced through the picker on their next `/start`. They can
change language any time via the menu or `/language`. Only **truly new**
users see the picker before anything else.

---

## 9. Putting It All Together — A Typical Happy Path

1. New user sends `/start`.
2. Picks a language.
3. Taps Verify.
4. Taps Request Access.
5. Admin gets a notification with Approve/Reject buttons; taps Approve.
6. User receives an approval message in their language.
7. User taps Subscription → `/subscribe`.
8. Payment succeeds (mock or Stripe).
9. Bot DMs a fresh single-use invite link to the VIP group.
10. User taps the link, joins the group.
11. User asks a question in private chat. Bot validates + forwards to admin.
12. Admin opens Questions, taps a pending question, taps Compose Reply,
    types an answer.
13. User receives the answer in their language.
14. 30 days later the subscription approaches the end of its billing period.
    The user pays again; the bot auto-extends 30 more days and re-issues the
    invite link if needed.

If anything goes wrong along the way — payment fails, the user lapses, they
break group rules — the bot guides them back with clear in-language
prompts, and the admin sees the full picture through the panel.

---

## 10. Glossary

- **Verified** — confirmed they read the welcome; not yet entitled to anything.
- **Pending approval** — waiting on admin decision.
- **Approved** — admin has cleared them; still need a subscription to use VIP.
- **Active** — subscription is paid and within billing period.
- **Grace** — short window after billing end where access continues.
- **Expired** — grace ended without renewal; access removed.
- **Lapse-removal delay** — extra buffer after grace before the bot bans the
  user from the VIP group.
- **Personal invite link** — a single-use, 30-day Telegram invite link unique
  to one user, generated fresh on each send.
- **Mock mode** — local/staging payment mode that simulates a successful
  payment instantly. Useful for demos and tests; switched off in production.
- **Reconciliation** — the periodic background job that aligns VIP group
  membership with subscription state (kicks lapsed users, unbans renewed
  users, sends fresh invites).
