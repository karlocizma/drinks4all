# Drinks4All

Drinks tracking web app with user login, admin management, inventory, monthly billing, SMTP reports, and mobile-compatible UI.

## Highlights
- Admin dashboard with teams/fridges/users/drinks management
- Reporting panel with live statistics (revenue, active users, top drinks, low stock)
- Self-registration with admin approval workflow
- Manual PayPal button for direct payment link
- Monthly email reporting (buyer overview + per-user payment statement)
- Fully dockerized stack (`app + postgres + mailhog`)

## Full Docker Stack
This project is fully dockerized: **app + postgres + mailhog**.

### Start
```bash
cp .env.example .env
docker compose up --build -d
```

Open:
- App: http://localhost:8000
- MailHog UI: http://localhost:8025

Default bootstrap admin:
- Email: `admin@drinks.local`
- Password: `admin123`

### Stop
```bash
docker compose down
```

### Reset database + uploaded images
```bash
docker compose down -v
docker compose up --build -d
```

## SMTP configuration
Edit [`.env`](/mnt/c/Users/kcizmesija/Desktop/Programming/drinks4all/.env):
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_SENDER`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_USE_TLS`
- `BUYER_REPORT_EMAIL`

For local Docker testing, `SMTP_HOST=mailhog` and `SMTP_PORT=1025`.

## PayPal button (manual payment link)
Set in `.env`:
- `PAYPAL_ME_URL=https://www.paypal.com/paypalme/YOURNAME`

When set, users get a **Pay with PayPal** button on dashboard that opens PayPal with the current monthly EUR amount.

## Key API
- `POST /auth/login`
- `POST /auth/register` (self-registration, admin approval required)
- `POST /auth/logout`
- `GET /drinks`
- `POST /consumptions`
- `DELETE /consumptions/last`
- `POST /me/change-password`
- `GET /me/summary?month=YYYY-MM`
- `GET /admin/teams`, `POST /admin/teams`, `PUT /admin/teams/{team_id}`, `DELETE /admin/teams/{team_id}`
- `GET /admin/fridges`, `POST /admin/fridges`, `PUT /admin/fridges/{fridge_id}`, `DELETE /admin/fridges/{fridge_id}`
- `POST /admin/drinks/upload-image`
- `GET /admin/drinks`, `POST /admin/drinks`, `PUT /admin/drinks/{drink_id}`, `DELETE /admin/drinks/{drink_id}`
- `GET /admin/users`, `GET /admin/users/pending`, `POST /admin/users`, `PUT /admin/users/{user_id}`, `DELETE /admin/users/{user_id}`
- `POST /admin/users/{user_id}/approve`
- `POST /admin/users/{user_id}/reset-password`
- `GET /admin/reports?month=YYYY-MM` (JSON/CSV/PDF)
- `POST /admin/run-billing?month=YYYY-MM`

## Optional Local (non-docker app) run
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
docker compose up -d postgres mailhog
python -m scripts.bootstrap
uvicorn app.main:app --reload
```

## License
This project is licensed under the MIT License. See [LICENSE](/mnt/c/Users/kcizmesija/Desktop/Programming/drinks4all/LICENSE).
