# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

FastAPI backend for "ALBdrinks" (package/repo name `drinks4all`) — an internal office drinks tracker: user login, admin console, inventory/stock tracking, monthly billing, and SMTP email reports. Server-rendered Jinja2 shells + vanilla JS frontend (no build step, no npm, no bundler).

## Commands

Run everything from the repository root (static files and uploads are mounted via the relative path `app/static`).

```bash
# Dev server (Docker, recommended — bundles Postgres + MailHog)
cp .env.example .env
docker compose up --build -d      # app: :8000, MailHog UI: :8025

# Dev server (native)
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m scripts.bootstrap        # apply Alembic migrations, seed admin + sample drinks
uvicorn app.main:app --reload

# Tests (no DB needed — in-memory SQLite)
pytest
pytest app/tests/test_auth_and_roles.py
pytest -k "test_run_billing"

# Lint
ruff check .
ruff check . --fix
```

There is no type-check command configured in this repo (no mypy in `requirements.txt`); ruff is the only linter.

Default seeded admin: `admin@drinks.local` / `admin123`.

## Architecture

**Layering:** `app/api/*.py` (FastAPI routers, one file per concern: `auth`, `user`, `admin`, `web`) → `app/services/*.py` (business logic: `billing_job`, `reporting`, `emailer`) → `app/models/*.py` (SQLAlchemy 2.0 declarative models). `app/schemas/*.py` holds Pydantic request/response models. Routers do light DB queries directly for simple CRUD; anything involving money math, month-bucketing, or cross-table aggregation lives in `app/services/reporting.py` and is reused by both the `/me/summary` endpoint and the monthly billing job.

**Auth:** JWT is issued in `app/core/security.py` and carried in an **httponly cookie** named `access_token` (not an Authorization header). `app/api/deps.py` provides `get_current_user` (reads the cookie, decodes JWT, loads the user) and `require_admin` (wraps it with a role check). All protected routes depend on one of these. The cookie's `Secure` flag is controlled by `settings.cookie_secure` (`COOKIE_SECURE` env var, default `false`) — set it `true` once the app is behind HTTPS.

**Password reset** (`POST /auth/forgot-password`, `POST /auth/reset-password`) uses stateless JWTs, not a database table. `app/core/security.py:create_password_reset_token`/`decode_password_reset_token` scope the token with a `purpose: password_reset` claim (so a login-session JWT can't be replayed here) and fingerprint it to the user's *current* `password_hash` (`password_fingerprint`). Since a successful reset changes `password_hash`, the fingerprint on every previously issued token for that user — including the one just used — stops matching immediately. That's what makes the token single-use without a database table. Both endpoints return an identical response for every failure/non-existence case, by design, to avoid leaking which emails are registered.

**Image uploads** (`POST /admin/drinks/upload-image`) are validated by sniffing magic bytes (`app/core/images.sniff_image_extension`), not by trusting the client-supplied `Content-Type` header or filename extension — both are spoofable and the old behavior let arbitrary file extensions land in the publicly-served `app/static/uploads/` directory.

**Schema migrations use Alembic** (`alembic/`, config in `alembic.ini`). `alembic/env.py` pulls the DB URL from `app.core.settings.settings.database_url` and `target_metadata` from `Base.metadata` (via `app.models`) — there's no separate hardcoded URL to keep in sync. `scripts/bootstrap.py` runs `alembic upgrade head` before seeding; app startup (`app/main.py`) deliberately does **not** run migrations (to avoid multiple worker processes racing to apply DDL concurrently). After changing a model, run `alembic revision --autogenerate -m "..."`, review the generated file, and commit it. The initial migration (`alembic/versions/9ad0738c4ed1_initial_schema.py`) is a special case: it calls `Base.metadata.create_all(checkfirst=True)` directly instead of hand-written `op.create_table()` calls, specifically so it's a safe no-op against any database that already has this schema (i.e. every currently-deployed instance) — do not copy that pattern for future migrations, which should use the normal explicit `op.*` autogenerate output.

**Settings** (`app/core/settings.py`) load from `.env` via `pydantic-settings`. Note the backward-compat shim at module load: if `admin_report_email` (an old, removed env var) is set and `buyer_report_email` is still at its default, it overwrites `buyer_report_email`.

**Money** is `Decimal` / SQLAlchemy `Numeric(10, 2)` throughout; currency is hardcoded to EUR in reporting/email output (no multi-currency support).

**Billing cycle:** `app/services/billing_job.run_monthly_billing()` computes per-user monthly totals via `reporting.monthly_user_report_rows`, emails each user a statement (plain text + inline-styled HTML) and emails `BUYER_REPORT_EMAIL` recipients a buyer overview + low-stock alert digest, then (if `close_month=True`) marks the month's `BillingPeriod` rows closed via `reporting.close_billing_month`. Once a month is closed, `POST /consumptions` for that month is rejected (`reporting.is_month_closed`). An APScheduler `BackgroundScheduler` (in `app/main.py`) fires this automatically on the 1st of each month at 08:00 in `TIMEZONE`; disabled when `ENABLE_SCHEDULER=false` or `settings.testing` is true. `POST /admin/run-billing` triggers it manually; `POST /admin/reset-month` reverses a month (deletes consumptions/billing periods/email logs, restores stock).

**Stock tracking:** `Drink.stock_quantity` is decremented on `POST /consumptions` and restored on undo/delete/reset. Crossing `low_stock_threshold` triggers an immediate low-stock email (`app/api/user.py:notify_low_stock`) independent of the monthly buyer digest.

**Email:** `app/services/emailer.py` sends directly via `smtplib` (no queue) and exposes `render_email(template_name, **context)`, a small Jinja2 environment scoped to `app/templates/` (autoescaping on, since these values include user-entered names/drink names). HTML bodies live in `app/templates/emails/` (`user_statement.html`, `buyer_overview.html`, `low_stock_alert.html`), all extending `emails/_layout.html` for the shared header/footer chrome; `billing_job.py`/`user.py` pass pre-formatted `f"{amount:.2f}"` strings into the template context rather than formatting Decimals inside Jinja, to avoid float-rounding drift. MailHog is used as the local SMTP catcher in Docker Compose. The statement email includes `settings.payment_email` so recipients know where to send payment.

**Reports:** `GET /admin/reports?month=YYYY-MM&format=json|csv|pdf` — CSV built manually in `reporting.build_csv`; PDF via `fpdf2` in `reporting.build_pdf` (has a `new_x/new_y` vs `ln=1` fallback for older fpdf API compat).

**Frontend:** no JS framework. `app/templates/*.html` are thin Jinja2 shells served by `app/api/web.py`; behavior lives in `app/static/js/{login,dashboard,admin}.js`, which call the JSON API directly via `fetch`. `admin.js` is the largest (grid/list dashboard view toggle, drink CRUD incl. image upload, user approval/management, reports).

**Testing:** `app/tests/conftest.py` sets `DATABASE_URL`/`SECRET_KEY`/`ENABLE_SCHEDULER`/`TESTING` env vars **before** importing `app.main`, then overrides the `get_db` dependency with a separate in-memory SQLite engine (`StaticPool`, tables dropped/recreated per test via an autouse fixture). Use the `client` fixture for HTTP-level tests and the `db` fixture for direct model setup; `admin_user`/`normal_user` fixtures create pre-hashed users.

## Maintenance scripts (production ops, not dev)

`scripts/` contains bash scripts for a deployed instance: `backup.sh` (Postgres dump + uploads tarball + `.env` snapshot), `restore.sh latest|<timestamp>`, `update.sh [--with-pull --branch X --keep N]` (backs up, optionally `git pull`s, rebuilds Docker, health-checks, and prints the backup path on failure so you can restore), `check_env.sh` (diffs `.env` against `.env.example`).
