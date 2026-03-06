# Drinks4All

Drinks tracking web app with user login, admin management, monthly billing, and email reports.

## Features
- Email/password login with admin-created accounts
- User dashboard with available drinks (name, photo, price) and one-click `+1`
- Monthly personal summary (`units`, `amount`)
- Admin CRUD for drinks and users
- Monthly reports in JSON, CSV, and PDF
- Scheduled monthly billing email job (1st day of month)
- Audit logs for email delivery attempts

## Stack
- Backend/API: FastAPI
- Frontend: server-rendered HTML + vanilla JS/CSS
- Database: PostgreSQL (SQLAlchemy)
- Scheduler: APScheduler
- Email: SMTP (MailHog supported)

## Quick Start
1. Install dependencies:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Start infra:
```bash
docker compose up -d
```

3. Configure env:
```bash
cp .env.example .env
```

4. Bootstrap initial admin + sample drinks:
```bash
python -m scripts.bootstrap
```

5. Run app:
```bash
uvicorn app.main:app --reload
```

Open:
- App: http://localhost:8000
- MailHog UI: http://localhost:8025

Default bootstrap admin:
- Email: `admin@drinks.local`
- Password: `admin123`

## API Endpoints
- `POST /auth/login`
- `POST /auth/logout`
- `GET /drinks`
- `POST /consumptions`
- `GET /me/summary?month=YYYY-MM`
- `POST /admin/drinks`
- `PUT /admin/drinks/{drink_id}`
- `DELETE /admin/drinks/{drink_id}`
- `GET /admin/users`
- `POST /admin/users`
- `PUT /admin/users/{user_id}`
- `POST /admin/users/{user_id}/reset-password`
- `GET /admin/reports?month=YYYY-MM`
- `GET /admin/reports?month=YYYY-MM&format=csv`
- `GET /admin/reports?month=YYYY-MM&format=pdf`
- `POST /admin/run-billing?month=YYYY-MM`

## Tests
```bash
pytest -q
```
