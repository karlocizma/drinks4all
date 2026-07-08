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
python -m scripts.bootstrap        # create tables, apply schema-compat ALTERs, seed admin + sample drinks
uvicorn app.main:app --reload

# Tests (no DB needed — in-memory SQLite)
pytest
pytest app/tests/test_auth_and_roles.py
pytest -k "test_run_billing"
```

There is no lint/format/type-check command configured in this repo — none of ruff/black/mypy are in `requirements.txt`.

Default seeded admin: `admin@drinks.local` / `admin123`.

## Architecture

**Layering:** `app/api/*.py` (FastAPI routers, one file per concern: `auth`, `user`, `admin`, `web`) → `app/services/*.py` (business logic: `billing_job`, `reporting`, `emailer`) → `app/models/*.py` (SQLAlchemy 2.0 declarative models). `app/schemas/*.py` holds Pydantic request/response models. Routers do light DB queries directly for simple CRUD; anything involving money math, month-bucketing, or cross-table aggregation lives in `app/services/reporting.py` and is reused by both the `/me/summary` endpoint and the monthly billing job.

**Auth:** JWT is issued in `app/core/security.py` and carried in an **httponly cookie** named `access_token` (not an Authorization header). `app/api/deps.py` provides `get_current_user` (reads the cookie, decodes JWT, loads the user) and `require_admin` (wraps it with a role check). All protected routes depend on one of these.

**No Alembic migrations despite being a dependency.** Schema evolution is done via idempotent `ALTER TABLE ... ADD/DROP COLUMN IF NOT EXISTS` statements in a function called `ensure_schema_compat()`, which is **duplicated** in both `app/main.py` (runs on app startup) and `scripts/bootstrap.py` (runs on manual bootstrap / Docker entrypoint). If you add or rename a model column, add a matching `ALTER TABLE` statement to **both** copies of `ensure_schema_compat()` — SQLite test/dev setups use `Base.metadata.create_all` so they don't need it, but the Postgres deployment path does since the tables already exist there.

**Settings** (`app/core/settings.py`) load from `.env` via `pydantic-settings`. Note the backward-compat shim at module load: if `admin_report_email` (an old, removed env var) is set and `buyer_report_email` is still at its default, it overwrites `buyer_report_email`.

**Money** is `Decimal` / SQLAlchemy `Numeric(10, 2)` throughout; currency is hardcoded to EUR in reporting/email output (no multi-currency support).

**Billing cycle:** `app/services/billing_job.run_monthly_billing()` computes per-user monthly totals via `reporting.monthly_user_report_rows`, emails each user a statement (plain text + inline-styled HTML) and emails `BUYER_REPORT_EMAIL` recipients a buyer overview + low-stock alert digest, then (if `close_month=True`) marks the month's `BillingPeriod` rows closed via `reporting.close_billing_month`. Once a month is closed, `POST /consumptions` for that month is rejected (`reporting.is_month_closed`). An APScheduler `BackgroundScheduler` (in `app/main.py`) fires this automatically on the 1st of each month at 08:00 in `TIMEZONE`; disabled when `ENABLE_SCHEDULER=false` or `settings.testing` is true. `POST /admin/run-billing` triggers it manually; `POST /admin/reset-month` reverses a month (deletes consumptions/billing periods/email logs, restores stock).

**Stock tracking:** `Drink.stock_quantity` is decremented on `POST /consumptions` and restored on undo/delete/reset. Crossing `low_stock_threshold` triggers an immediate low-stock email (`app/api/user.py:notify_low_stock`) independent of the monthly buyer digest.

**Email:** `app/services/emailer.py` sends directly via `smtplib` (no templating engine, no queue) — HTML bodies are hand-built f-strings inline in `billing_job.py` and `user.py`. MailHog is used as the local SMTP catcher in Docker Compose.

**Reports:** `GET /admin/reports?month=YYYY-MM&format=json|csv|pdf` — CSV built manually in `reporting.build_csv`; PDF via `fpdf2` in `reporting.build_pdf` (has a `new_x/new_y` vs `ln=1` fallback for older fpdf API compat).

**Frontend:** no JS framework. `app/templates/*.html` are thin Jinja2 shells served by `app/api/web.py`; behavior lives in `app/static/js/{login,dashboard,admin}.js`, which call the JSON API directly via `fetch`. `admin.js` is the largest (grid/list dashboard view toggle, drink CRUD incl. image upload, user approval/management, reports).

**Testing:** `app/tests/conftest.py` sets `DATABASE_URL`/`SECRET_KEY`/`ENABLE_SCHEDULER`/`TESTING` env vars **before** importing `app.main`, then overrides the `get_db` dependency with a separate in-memory SQLite engine (`StaticPool`, tables dropped/recreated per test via an autouse fixture). Use the `client` fixture for HTTP-level tests and the `db` fixture for direct model setup; `admin_user`/`normal_user` fixtures create pre-hashed users.

## Maintenance scripts (production ops, not dev)

`scripts/` contains bash scripts for a deployed instance: `backup.sh` (Postgres dump + uploads tarball + `.env` snapshot), `restore.sh latest|<timestamp>`, `update.sh [--with-pull --branch X --keep N]` (backs up, optionally `git pull`s, rebuilds Docker, health-checks, and prints the backup path on failure so you can restore), `check_env.sh` (diffs `.env` against `.env.example`).
