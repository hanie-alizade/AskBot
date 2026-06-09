# AskBot — Fresh Machine Setup & Deployment Runbook

A complete, step-by-step guide to run this project from scratch on a new computer,
and to understand how it is deployed on Render. Written so a non-developer can follow it.

---

## 1. Technology stack

| Layer | What this project uses |
|---|---|
| Language | **Python 3.11.9** (pinned in `runtime.txt`, `.python-version`, `render.yaml`) |
| Telegram framework | **aiogram 3.4.1** (long-polling, **not** Telegram webhooks) |
| Web framework | **FastAPI 0.115** served by **uvicorn 0.30.6** (health pages + Stripe webhook) |
| Database | **SQLite by default** (file `ask_bot.db`); PostgreSQL optional via `DATABASE_URL` |
| ORM | **SQLAlchemy 2.0.23** |
| Migrations | Custom idempotent runner (`database/migration_runner.py`) + `create_all`. **Alembic is listed but NOT used.** |
| Payments | **Stripe 11.4.1** (Checkout + Customer Portal + webhooks) |
| Config | `python-dotenv` loading a `.env` file |

The single process (`python -m app.main`) runs **two things at once**: the Telegram bot
(polling) **and** the FastAPI/uvicorn HTTP server (for Stripe webhooks + health checks).

### External services it talks to
- **Telegram Bot API** (`api.telegram.org`) — outbound HTTPS. May be blocked on some
  networks/regions; a VPN may be required (see §10).
- **Stripe API** (`api.stripe.com`) — outbound HTTPS, only when not in mock mode.
- No Redis, no message broker, no Node.js, no Docker required.

---

## 2. Required software to install

| Software | Required? | Notes |
|---|---|---|
| **Python 3.11.x** | ✅ Required | Use 3.11.9 to match production. 3.12 may work but is untested here. |
| **Git** | ✅ Required | To clone the repository. |
| **pip + venv** | ✅ Required | Ships with Python. |
| PostgreSQL | ⛔ Optional | Only if you set a `postgresql://` `DATABASE_URL`. **Also requires adding a driver — see §10.** Default SQLite needs nothing. |
| **Stripe CLI** | ⚠️ Recommended for local Stripe testing | Needed to forward Stripe webhooks to your machine. Not needed if `MOCK_PAYMENT_ENABLED=true`. |
| Redis / Docker / Node.js | ⛔ Not used | The project does not require any of these. |

---

## 3. Environment variables (complete list)

All variables are read from a `.env` file in the project root (loaded by `python-dotenv`).
Sources: `app/config.py`, `config/stripe_config.py`, `database/db.py`, `app/main.py`.

### Core (startup will FAIL without these)
The startup validator (`app/main.py → validate_startup_config`) hard-requires these:

| Variable | Required? | Example | Description |
|---|---|---|---|
| `BOT_TOKEN` | ✅ **Required** | `8705043783:AAF...` | Telegram bot token from @BotFather. |
| `ADMIN_ID` | ✅ **Required** | `453888838` | Telegram numeric user ID of the single admin. Controls admin panel access. |
| `GROUP_INVITE_LINK` | ✅ **Required** | `https://t.me/+abc123` | Invite link to the community group. |
| `VIP_GROUP_ID` | ✅ **Required** | `-1003985764392` | Numeric ID of the VIP group. Startup fails if `0`/missing. |
| `STRIPE_WEBHOOK_SECRET` *(resolved)* | ✅ Required **unless** `MOCK_PAYMENT_ENABLED=true` | `whsec_...` | Webhook signing secret. Resolved per mode (see Stripe rows). Startup fails in real-payment mode if absent. |

### Payment mode flags

| Variable | Required? | Example | Description |
|---|---|---|---|
| `MOCK_PAYMENT_ENABLED` | Optional (default `false`) | `true` | `true` = fully simulated payments, no Stripe calls. Great for first local run. |
| `STRIPE_LIVE_MODE` | Optional (default `true` = LIVE) | `false` | Selects which Stripe keys are used. `false` = TEST keys, `true`/unset = LIVE keys. |
| `MOCK_SUBSCRIPTION_ACTIVE_BY_DEFAULT` | Optional (default `true`) | `true` | Legacy flag; only affects mock routing. |

### Stripe — TEST mode keys (used when `STRIPE_LIVE_MODE=false`)

| Variable | Required? | Example | Description |
|---|---|---|---|
| `STRIPE_TEST_SECRET_KEY` | Required for TEST real payments | `sk_test_...` | Stripe test secret key. |
| `STRIPE_TEST_PRICE_ID` | Required for TEST real payments | `price_...` | Stripe test subscription price ID. |
| `STRIPE_TEST_WEBHOOK_SECRET` | Required for TEST real payments | `whsec_...` | Signing secret of your TEST webhook endpoint. |

### Stripe — LIVE mode keys (used when `STRIPE_LIVE_MODE=true`/unset)

| Variable | Required? | Example | Description |
|---|---|---|---|
| `STRIPE_LIVE_SECRET_KEY` | Required for LIVE | `sk_live_...` | Stripe live secret key. |
| `STRIPE_LIVE_PRICE_ID` | Required for LIVE | `price_...` | Stripe live subscription price ID. |
| `STRIPE_LIVE_WEBHOOK_SECRET` | Required for LIVE | `whsec_...` | Signing secret of your LIVE webhook endpoint. |
| `STRIPE_SECRET_KEY` / `STRIPE_PRICE_ID` / `STRIPE_WEBHOOK_SECRET` | Optional (legacy) | `sk_live_...` | Backward-compatible fallback used in LIVE mode if the `STRIPE_LIVE_*` versions are absent. |

### Database / server / tuning

| Variable | Required? | Example | Description |
|---|---|---|---|
| `DATABASE_URL` | Optional (default `sqlite:///./ask_bot.db`) | `postgresql://user:pass@host:5432/db` | DB connection string. SQLite needs no install. Postgres needs a driver (§10). |
| `PORT` | Optional (default `10000`) | `10000` | HTTP server port. Render injects this automatically. |
| `SUBSCRIPTION_ENFORCEMENT_ENABLED` | Optional (default `false`) | `false` | Whether subscription gating is enforced. |
| `SUBSCRIPTION_GRANDFATHER_ENABLED` | Optional (default `true`) | `true` | Grandfather pre-existing users. |
| `STRIPE_PORTAL_RETURN_URL` | Optional (has default) | `https://.../payment-success` | Where Stripe Customer Portal returns users. |
| `CHECKOUT_BASE_URL` | Optional (default `https://example.com`) | `https://yourapp.onrender.com` | Base URL used by the payment factory. |
| `VIP_SUBSCRIPTION_LAPSE_REMOVAL_DELAY_SECONDS` | Optional (default `172800`) | `172800` | Delay before removing lapsed members from VIP group. |
| `SUBSCRIPTION_PAST_DUE_GRACE_DAYS` | Optional (default `3`) | `3` | Grace window after a failed renewal. |
| `VIP_MEMBERSHIP_SYNC_INTERVAL_SECONDS` | Optional (default `300`, min `5`) | `300` | How often VIP membership reconciliation runs. |

---

## 4. Local setup procedure (step by step)

### Step 1 — Clone the repository
```powershell
git clone <REPO_URL> AskBot
cd AskBot
```

### Step 2 — Create and activate a virtual environment
```powershell
# Windows (PowerShell)
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```
```bash
# macOS / Linux
python3.11 -m venv .venv
source .venv/bin/activate
```

### Step 3 — Install dependencies
```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4 — Configure `.env`
Create a `.env` file in the project root. **Easiest first run (no Stripe needed):**
```dotenv
BOT_TOKEN=123456:your-test-bot-token
ADMIN_ID=453888838
GROUP_INVITE_LINK=https://t.me/+yourInviteLink
VIP_GROUP_ID=-1001234567890

# Simulated payments — no Stripe required to boot
MOCK_PAYMENT_ENABLED=true

# Local DB (default; can omit this line)
DATABASE_URL=sqlite:///./ask_bot.db
```
For real Stripe testing instead, set `MOCK_PAYMENT_ENABLED=false`, `STRIPE_LIVE_MODE=false`,
and fill the three `STRIPE_TEST_*` variables (see §8).

### Step 5 — Initialize the database
**Nothing to do manually.** On startup the app calls `init_db()`, which runs
`Base.metadata.create_all()` (creates every table) and then the idempotent
`run_baseline_migrations()`. A fresh SQLite file is created automatically. (See §6.)

### Step 6 — Run the application
```powershell
python -m app.main
```
You should see: `Startup configuration validation passed`, `Database tables created
successfully`, `Start polling`, and `Uvicorn running on http://0.0.0.0:10000`.

Verify the HTTP side: open `http://localhost:10000/health` → `{"status":"healthy"}`.

---

## 5. Production startup procedure (Render)

`render.yaml` declares one **web service**, Python runtime, plan `free`, Python 3.11.
The app is a single process that runs the bot **and** the webhook server together.

- **Build command:** `pip install -r requirements.txt`
- **Start command:** `python -m app.main`
  (This is the one command. `render.yaml` is minimal, so confirm this start command is
  set in the Render dashboard.)
- **Port:** uvicorn binds `0.0.0.0:$PORT`; Render provides `PORT` automatically.
- **Background worker:** none required — the VIP-membership reconciliation loop runs as an
  in-process asyncio task started by `start_bot()`. No Celery/cron/Redis.
- **Telegram startup:** long-polling (`dp.start_polling`) — **no public Telegram webhook URL
  needed.** Only one instance may poll a given token at a time (see §10).
- **Stripe webhook server:** the same uvicorn server exposes `POST /stripe/webhook`. In
  Stripe, point the webhook endpoint at `https://<your-app>.onrender.com/stripe/webhook`.

---

## 6. Database analysis

- **Auto-creates tables?** ✅ Yes. `init_db()` → `Base.metadata.create_all()` builds the full
  schema on every boot (no-op if it already exists).
- **Migrations required?** ❌ Not manually. `run_baseline_migrations()` adds missing
  columns/indexes idempotently. ⚠️ The column-adding part is **SQLite-only** (`if dialect ==
  "sqlite"`); on a **fresh** Postgres DB that's fine because `create_all` already builds every
  column. The unique indexes at the end run on all dialects.
- **Alembic?** ❌ Present in `requirements.txt` but **unused** — there is no `alembic.ini` or
  migrations folder. Ignore it.
- **Seed data?** ❌ None. The DB starts empty; users are created as people interact with the bot.

---

## 7. Telegram requirements

- **Bot token** (`BOT_TOKEN`): create a bot with **@BotFather** → `/newbot` → copy the token.
  Use a **separate test bot** for local work (see §10).
- **Admin** (`ADMIN_ID`): a single numeric Telegram user ID. Get yours from **@userinfobot**.
  This ID unlocks the admin panel (`/start` as admin) and all `adm:*` actions.
- **VIP group** (`VIP_GROUP_ID`): add the bot to the group as an **admin**, then read the
  numeric group ID (e.g. via @userinfobot in the group, or bot logs). Must be set/non-zero.
- **Invite link** (`GROUP_INVITE_LINK`): a working invite link to the community group.
- The bot uses **polling**, so it does **not** need a public URL for Telegram itself.

---

## 8. Stripe requirements

The mode is chosen by two independent flags:
- `MOCK_PAYMENT_ENABLED=true` → no Stripe at all (simulated). Good for first boot.
- `MOCK_PAYMENT_ENABLED=false` + `STRIPE_LIVE_MODE=false` → **real Stripe TEST** (`sk_test_…`).
- `MOCK_PAYMENT_ENABLED=false` + `STRIPE_LIVE_MODE=true`/unset → **real Stripe LIVE** (`sk_live_…`).

**Test mode variables:** `STRIPE_TEST_SECRET_KEY`, `STRIPE_TEST_PRICE_ID`, `STRIPE_TEST_WEBHOOK_SECRET`.
**Live mode variables:** `STRIPE_LIVE_SECRET_KEY`, `STRIPE_LIVE_PRICE_ID`, `STRIPE_LIVE_WEBHOOK_SECRET`
(or the legacy `STRIPE_SECRET_KEY` / `STRIPE_PRICE_ID` / `STRIPE_WEBHOOK_SECRET`).

**Webhook requirements:** the endpoint is `POST /stripe/webhook`; it verifies the signature
with `stripe.Webhook.construct_event` using the mode-matched signing secret. Register it in
the Stripe Dashboard (Developers → Webhooks) for these events:
`checkout.session.completed`, `invoice.paid`, `invoice.payment_failed`,
`customer.subscription.updated`, `customer.subscription.deleted`.

**Testing Stripe webhooks locally** (Stripe can't reach `localhost`): use the Stripe CLI:
```bash
stripe login
stripe listen --forward-to localhost:10000/stripe/webhook
```
The CLI prints a `whsec_...` secret — put it in `STRIPE_TEST_WEBHOOK_SECRET`, set
`STRIPE_LIVE_MODE=false` and `MOCK_PAYMENT_ENABLED=false`, then `stripe trigger
checkout.session.completed`. ⚠️ The checkout success/cancel URLs are currently **hardcoded**
to the Render domain in `services/stripe_checkout.py`, so after a real local checkout the
browser redirects to the Render site, not localhost (the webhook still fires correctly).

---

## 9. Fresh Machine Setup Checklist

```
□ Install Python 3.11.9 and Git
□ (Optional) Install Stripe CLI if testing real payments locally
□ git clone <repo> && cd AskBot
□ Create venv: py -3.11 -m venv .venv  →  activate it
□ pip install -r requirements.txt
□ Create .env with BOT_TOKEN, ADMIN_ID, GROUP_INVITE_LINK, VIP_GROUP_ID
□ For first run set MOCK_PAYMENT_ENABLED=true (skip Stripe entirely)
□ Database: nothing to do — auto-created on first boot
□ Run: python -m app.main
□ Verify HTTP: open http://localhost:10000/health → {"status":"healthy"}
□ Verify Telegram bot: message your bot /start → you get the welcome + menu
□ Verify admin panel: /start from the ADMIN_ID account → admin menu appears
□ Verify Stripe (only if not mock): stripe listen + stripe trigger → admin "Webhook log" shows the event
```

---

## 10. Render vs. local — things that will break if not handled

1. **Same `BOT_TOKEN` running in two places** → Telegram allows only one poller per token.
   If Render is live and you run locally with the same token you'll get
   `TelegramConflictError`. **Use a separate test bot token locally**, or pause the Render
   service while testing.

2. **Telegram network access / region blocks** → a startup crash with
   `getaddrinfo failed` / `Cannot connect to host api.telegram.org` means DNS/network can't
   reach Telegram (common where Telegram is blocked). Connect a **VPN** before launching, or
   run `ipconfig /flushdns`.

3. **`DATABASE_URL` pointing at PostgreSQL** → `requirements.txt` has **no Postgres driver**
   (`psycopg2`). If you set a `postgresql://` URL, install a driver first:
   `pip install "psycopg2-binary"`. The zero-config default is SQLite, which needs nothing.

4. **SQLite on Render Free is ephemeral** → Render's free disk is wiped on every deploy/
   restart, so a SQLite DB there **loses all data** on redeploy. Fine locally; for persistent
   production use a managed PostgreSQL `DATABASE_URL` (plus the driver from point 3).

5. **`PORT`** → Render injects it; locally it defaults to `10000`. No action needed, just know
   the local server is on `:10000`.

6. **Stripe webhooks can't reach `localhost`** → on Render the public URL receives them; locally
   you must use the Stripe CLI `stripe listen` forwarder (§8).

7. **Hardcoded Render success/cancel URLs** in `services/stripe_checkout.py` → local checkouts
   redirect to the Render domain after payment. Harmless for webhook testing, but note it if
   you expect to land back on localhost.

8. **`STRIPE_WEBHOOK_SECRET` required in real mode** → if `MOCK_PAYMENT_ENABLED=false` and no
   resolved webhook secret is set, **startup aborts by design**. Either provide the secret or
   set `MOCK_PAYMENT_ENABLED=true` for a no-Stripe boot.
```
