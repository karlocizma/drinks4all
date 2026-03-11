# ALBdrinks

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
`BUYER_REPORT_EMAIL` can contain one or more recipients separated by commas.

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

## Automated Updates And Backups
Local automation scripts are included in [`scripts/backup.sh`](/mnt/c/Users/kcizmesija/Desktop/Programming/drinks4all/scripts/backup.sh), [`scripts/update.sh`](/mnt/c/Users/kcizmesija/Desktop/Programming/drinks4all/scripts/update.sh), [`scripts/restore.sh`](/mnt/c/Users/kcizmesija/Desktop/Programming/drinks4all/scripts/restore.sh), [`scripts/prune_backups.sh`](/mnt/c/Users/kcizmesija/Desktop/Programming/drinks4all/scripts/prune_backups.sh), and [`scripts/check_env.sh`](/mnt/c/Users/kcizmesija/Desktop/Programming/drinks4all/scripts/check_env.sh).

Create a backup now:
```bash
bash scripts/backup.sh
```

Run a local update from your current checked-out code:
```bash
bash scripts/update.sh
```

Run an update that also pulls the latest git branch first:
```bash
bash scripts/update.sh --with-pull --branch main --keep 10
```

Restore the latest backup:
```bash
bash scripts/restore.sh latest
```

Check whether your current `.env` is missing new variables from `.env.example`:
```bash
bash scripts/check_env.sh
```

Backups are written to `backups/` and include:
- PostgreSQL dump: `albdrinks-db-YYYYMMDD-HHMMSS.sql.gz`
- Uploaded drink images: `albdrinks-uploads-YYYYMMDD-HHMMSS.tar.gz`
- Environment backup: `albdrinks-env-YYYYMMDD-HHMMSS.env`

The update script does this automatically:
- creates a fresh backup
- optionally pulls the selected git branch
- compares `.env` with `.env.example` and stops if variables are missing
- rebuilds and restarts Docker services
- checks that the app responds on `http://localhost:8000/`
- stops the app service if the rebuild or health check fails
- prunes old backups

## GitHub Actions Deploy
Two workflows are included:
- [`deploy.yml`](/mnt/c/Users/kcizmesija/Desktop/Programming/drinks4all/.github/workflows/deploy.yml): deploy on push to `main` or manual dispatch
- [`nightly-backup.yml`](/mnt/c/Users/kcizmesija/Desktop/Programming/drinks4all/.github/workflows/nightly-backup.yml): nightly remote backup over SSH

Required GitHub repository secrets:
- `DEPLOY_HOST`: server hostname or IP
- `DEPLOY_USER`: SSH user
- `DEPLOY_SSH_KEY`: private SSH key for that server
- `DEPLOY_PATH`: absolute path to the repo on the server
- `DEPLOY_PORT`: optional SSH port, usually `22`
- `BACKUP_KEEP_COUNT`: optional number of backups to keep, for example `10`

Server prerequisites:
- the repository is already cloned on the server at `DEPLOY_PATH`
- Docker and `docker compose` are installed
- the server can run the same `docker compose up --build -d` flow manually
- the `.env` file already exists on the server

Recommended first-time server setup:
```bash
git clone <your-repo-url> /path/to/albdrinks
cd /path/to/albdrinks
cp .env.example .env
docker compose up --build -d
```

After that, pushing to `main` will trigger:
- remote backup
- git pull on the target branch
- Docker rebuild and restart
- HTTP health check

If an update fails, the workflow exits with the latest backup path printed in the logs. You can then restore with:
```bash
bash scripts/restore.sh latest
```

## License
This project is licensed under the MIT License. See [LICENSE](/mnt/c/Users/kcizmesija/Desktop/Programming/drinks4all/LICENSE).
