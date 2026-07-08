# ALBdrinks

Drinks tracking web app with user login, admin management, inventory, monthly billing, SMTP reports, and mobile-optimised UI.

## Highlights

- Admin console (desktop) — manage users, drinks, photo uploads, inventory and billing
- Mobile dashboard — two-column drink grid, one-tap logging, undo, monthly summary
- Reporting panel — live statistics (revenue, active users, top drinks, low stock)
- Self-registration with admin approval workflow
- Manual PayPal button for direct payment link on the dashboard
- Monthly email reporting (buyer overview + per-user payment statement)

---

## Deployment Option 1 — Docker (recommended)

The full stack (app + PostgreSQL + MailHog) runs with a single command.

**Prerequisites:** Docker and Docker Compose installed.

```bash
cp .env.example .env
# Edit .env — at minimum set SECRET_KEY to a random string
docker compose up --build -d
```

Open:
- App: http://localhost:8000
- MailHog (local email UI): http://localhost:8025

Default admin account:
- Email: `admin@drinks.local`
- Password: `admin123`

### Stop

```bash
docker compose down
```

### Reset database and uploaded images

```bash
docker compose down -v
docker compose up --build -d
```

---

## Deployment Option 2 — Without Docker

Use this when you want to run the app directly on a server with a native PostgreSQL installation.

**Prerequisites:** Python 3.12+, PostgreSQL 17, a virtual environment tool.

### 1. Set up the database

Create a PostgreSQL database and user, then set `DATABASE_URL` in `.env` to match:

```
DATABASE_URL=postgresql+psycopg://youruser:yourpassword@localhost:5432/drinks4all
```

### 2. Install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env — set DATABASE_URL, SECRET_KEY, SMTP_*, BUYER_REPORT_EMAIL
```

### 4. Bootstrap the database

Creates all tables, applies schema migrations, and seeds the admin account and sample drinks:

```bash
python -m scripts.bootstrap
```

### 5. Run the app

For development:
```bash
uvicorn app.main:app --reload
```

For production (example with a single worker — increase as needed):
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
```

App is available at http://localhost:8000.

> **Note:** MailHog is not required when using a real SMTP server. Set `SMTP_HOST`, `SMTP_PORT`, and `SMTP_USE_TLS=true` in `.env` to point at your mail provider.

---

## Environment Variables

All settings are in `.env`. A template with every variable and its default is in `.env.example`.

| Variable | Description |
|---|---|
| `SECRET_KEY` | JWT signing secret — set to a long random string in production |
| `DATABASE_URL` | SQLAlchemy connection string |
| `TIMEZONE` | Scheduler timezone (e.g. `Europe/Berlin`) |
| `REMEMBER_ME_DAYS` | Session cookie lifetime when "Remember me" is checked |
| `SMTP_HOST` | SMTP server hostname |
| `SMTP_PORT` | SMTP port (1025 for MailHog, 465/587 for real providers) |
| `SMTP_SENDER` | From address for all outgoing emails |
| `SMTP_USERNAME` | SMTP auth username (leave blank for MailHog) |
| `SMTP_PASSWORD` | SMTP auth password (leave blank for MailHog) |
| `SMTP_USE_TLS` | `true` / `false` |
| `BUYER_REPORT_EMAIL` | One or more comma-separated addresses for the monthly buyer report |
| `PAYPAL_ME_URL` | Full PayPal.Me URL (e.g. `https://www.paypal.com/paypalme/YOURNAME`). Leave blank to hide the button. |
| `PAYMENT_EMAIL` | Contact address shown in monthly statement emails so users know where to send payment. |
| `UPLOAD_DIR` | Directory for uploaded drink images (default: `app/static/uploads`) |
| `MAX_UPLOAD_MB` | Max image upload size in megabytes |

---

## PayPal Button

When `PAYPAL_ME_URL` is set, users see a **Pay with PayPal** button on the dashboard that opens PayPal pre-filled with their current monthly total.

---

## Key API

| Method | Path | Description |
|---|---|---|
| `POST` | `/auth/login` | Log in |
| `POST` | `/auth/register` | Self-register (pending admin approval) |
| `POST` | `/auth/logout` | Log out |
| `GET` | `/me` | Current user info (id, name, email) |
| `POST` | `/me/change-password` | Change own password |
| `GET` | `/me/summary?month=YYYY-MM` | Monthly consumption summary |
| `GET` | `/drinks` | List active drinks |
| `POST` | `/consumptions` | Log a drink |
| `DELETE` | `/consumptions/last` | Undo last drink |
| `GET` | `/admin/drinks` | List all drinks (admin) |
| `POST` | `/admin/drinks` | Create drink |
| `PUT` | `/admin/drinks/{id}` | Update drink |
| `DELETE` | `/admin/drinks/{id}` | Delete drink |
| `POST` | `/admin/drinks/upload-image` | Upload drink photo |
| `GET` | `/admin/users` | List users |
| `GET` | `/admin/users/pending` | List pending-approval users |
| `POST` | `/admin/users` | Create user |
| `PUT` | `/admin/users/{id}` | Update user |
| `DELETE` | `/admin/users/{id}` | Delete user |
| `POST` | `/admin/users/{id}/approve` | Approve pending user |
| `POST` | `/admin/users/{id}/reset-password` | Reset user password |
| `GET` | `/admin/reports?month=YYYY-MM` | Monthly report (JSON / CSV / PDF) |
| `POST` | `/admin/run-billing?month=YYYY-MM` | Trigger billing run |

---

## Maintenance Scripts

All scripts are in `scripts/`. Run from the repository root.

### Backup

```bash
bash scripts/backup.sh
```

Creates a timestamped backup in `backups/` containing:
- PostgreSQL dump: `albdrinks-db-YYYYMMDD-HHMMSS.sql.gz`
- Uploaded drink images: `albdrinks-uploads-YYYYMMDD-HHMMSS.tar.gz`
- Environment file: `albdrinks-env-YYYYMMDD-HHMMSS.env`

### Restore

```bash
bash scripts/restore.sh latest     # restore newest backup
bash scripts/restore.sh 20260101-120000  # restore specific timestamp
```

### Update

Backs up, optionally pulls from git, rebuilds and restarts Docker, and checks the app responds:

```bash
bash scripts/update.sh                            # rebuild from current code
bash scripts/update.sh --with-pull --branch main --keep 10  # pull main first, keep 10 backups
```

If the rebuild or health check fails, the script exits and prints the backup path so you can restore.

### Check environment

Compares `.env` against `.env.example` and reports any missing variables:

```bash
bash scripts/check_env.sh
```

---

## Running Tests

No running database is required — tests use an in-memory SQLite database.

```bash
pytest                                           # all tests
pytest app/tests/test_auth_and_roles.py          # single file
pytest -k "test_run_billing"                     # single test by name
```

---

## License

MIT License. See `LICENSE`.
