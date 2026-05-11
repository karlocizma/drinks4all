# ALBdrinks Rework — Design Spec

**Date:** 2026-05-11  
**Approach:** Approach 1 — Full clean rework

---

## Context

ALBdrinks is a self-hosted internal tool for tracking office drink consumption. Two distinct usage surfaces:

- **Admin console** — used on desktop (computer) by one or more admins to manage users, drinks, reports, and billing.
- **User dashboard** — used on mobile phones by employees to log drink consumptions and view their monthly summary.

---

## Section 1 — Backend & Data Model

### Remove teams and fridges entirely

The following are deleted from the codebase:

**Models removed:**
- `app/models/team.py` — `Team` model
- `app/models/fridge.py` — `Fridge` model

**Columns dropped from existing tables:**
- `drinks.team_id`, `drinks.fridge_id`
- `users.team_id`
- `consumptions.team_id`, `consumptions.fridge_id`

**Schema cleanup in `ensure_schema_compat()`:**
New statements added (idempotent, run on every startup):
```sql
ALTER TABLE consumptions DROP COLUMN IF EXISTS team_id;
ALTER TABLE consumptions DROP COLUMN IF EXISTS fridge_id;
ALTER TABLE drinks DROP COLUMN IF EXISTS team_id;
ALTER TABLE drinks DROP COLUMN IF EXISTS fridge_id;
ALTER TABLE users DROP COLUMN IF EXISTS team_id;
DROP TABLE IF EXISTS fridges CASCADE;
DROP TABLE IF EXISTS teams CASCADE;
```

**Endpoints removed from `app/api/admin.py`:**
- `GET/POST/PUT/DELETE /admin/teams`
- `GET/POST/PUT/DELETE /admin/fridges`
- `ensure_team_exists()` and `ensure_fridge_exists()` helpers

**Filtering removed from `app/api/user.py`:**
- `GET /drinks` currently filters by `Drink.team_id == current_user.team_id`. This filter is removed. All active drinks are returned to all authenticated users.

**Schemas updated:**
- `DrinkCreate` — remove `team_id`, `fridge_id` fields
- `DrinkUpdate` — remove `team_id`, `fridge_id` fields; fix `stock_quantity` null-handling (see below)
- `UserCreate` / `UserUpdate` in `app/schemas/admin.py` — remove `team_id` field
- `app/models/__init__.py` — remove `Team`, `Fridge` exports

### Bug fixes bundled in

**`DrinkUpdate` null-handling for `stock_quantity`:**  
Current code uses `if payload.stock_quantity is not None` to decide whether to apply the update, making it impossible to set stock back to `null` (unlimited). Fix: check `"stock_quantity" in payload.model_fields_set` instead, so an explicitly sent `null` is applied while an absent field is skipped.

**`monthly_drink_report_rows` outer join bug:**  
Current WHERE clause `(Consumption.consumed_at >= start) | (Consumption.id.is_(None))` applied after a LEFT OUTER JOIN incorrectly filters out drinks with zero consumptions in some DB configurations. Fix: rewrite using a subquery that aggregates `consumptions` for the month independently, then LEFT JOINs it to `drinks`, so drinks with zero consumptions always appear with zero values.

---

## Section 2 — Design System Upgrade

### CSS

`app/static/css/app.css` is replaced with the full design system from the ZIP. Existing class names (`.card`, `.topbar`, `.drink-grid`, `.modal-backdrop`, etc.) are preserved — no JS changes required for this step alone.

**Additions over current file:**
- Inter font via Google Fonts `@import` (Segoe UI remains as fallback)
- Full token set: `--panel-subtle`, `--panel-stat`, `--panel-pill`, `--fg2`, `--fg3`, `--fg-muted`, `--border-strong`, `--border-input`, `--accent-deep`, `--accent-ink`, `--paypal`, `--paypal-ink`, `--grad-page`, `--grad-metric`, `--grad-modal-scrim`
- `.btn-icon` utility class for small bordered icon buttons used in the admin drink list

### Icons

Lucide loaded via CDN in all three templates:
```html
<script src="https://unpkg.com/lucide@0.469.0/dist/umd/lucide.min.js"></script>
```
`lucide.createIcons()` called at end of each page's JS. Admin section headings use `<i data-lucide="...">` at 22px in `--accent` colour. Admin buttons use 18px inline icons. User-facing surfaces (login, dashboard) remain icon-light per design system guidelines.

### Brand assets

Files copied from ZIP `assets/` to `app/static/`:
- `favicon.svg` → `app/static/favicon.svg`
- `logo-wordmark.svg` → `app/static/logo-wordmark.svg`

All three templates get `<link rel="icon" href="/static/favicon.svg">` in `<head>`.  
Admin topbar replaces `<h1>Admin Console</h1>` plain text with the wordmark SVG.

---

## Section 3 — Admin Console Rework

### Layout

Three-column layout replaced with two columns: **Users | Drinks**. Reporting panel remains full-width across the top (unchanged behaviour, styling updated to new tokens).

### Drinks column

**Create form (top of column):**
- Photo upload button (`POST /admin/drinks/upload-image`) + photo URL input
- Name, Price (EUR)
- Stock quantity (optional — leave blank for unlimited)
- Low-stock threshold (default 5)
- "Create Drink" submit button

**Drink list (below form):**
- Each row: 48×48px photo thumbnail (`object-fit: cover`, fallback placeholder icon if no URL), drink name, price, stock pill, Edit button
- Stock pill colours: green (`ok`) when above threshold, amber (`low`) when at or below threshold, grey (`inf`) when `stock_quantity` is null
- Inactive drinks rendered at 50% opacity — still show and are still editable, but visually distinct

**Edit modal:**
- Opens as a full-screen overlay (`modal-backdrop`)
- Layout: 80×80px thumbnail on left + Name input + "Change Photo" upload button on right; Photo URL field below; Price and Stock in a 2-col row; Low-stock threshold full-width; Active toggle (on/off)
- Live image preview: thumbnail updates immediately after successful upload response
- Footer: Save (primary) / Cancel (secondary) / Delete (danger)
- Delete calls `confirm()` before `DELETE /admin/drinks/{id}`
- Clicking the backdrop or Cancel closes without saving
- Setting Active to off sets `is_active: false` on save (drink disappears from user dashboard)

**Users column:**  
Existing behaviour preserved. Edit and Reset Password actions converted from `prompt()` to a proper modal (same overlay pattern as drink edit). No teams or team assignment UI anywhere.

---

## Section 4 — Dashboard (Mobile-Optimised)

### Topbar

Replaces the current five-button row (which wraps badly on phones) with:
- Left: ALBdrinks logo mark + logged-in user's name + current month
- Right: "Undo" button + `⋯` overflow button

The `⋯` button toggles a small positioned dropdown `<div>` (same dark panel style, `border-radius: 10px`, `box-shadow` for separation) containing: Change Password, Logout. Clicking outside the dropdown closes it. Month picker input moves inside this overflow menu (used rarely).

### Summary card

Unchanged in content. PayPal button gets `width: 100%` on mobile for easier tapping.

### Drink grid

- Grid changes from `minmax(210px, 1fr)` to `minmax(150px, 1fr)` → natural two-column layout on phones, three-plus on larger screens
- Card photo area: 140px tall, `object-fit: cover`
- Card body: drink name (bold), price in `--accent` cyan, full-width "+1 Drink" button (min height 44px for touch), stock line below button (amber + ⚠ when at or below threshold)
- Confirm modal: unchanged behaviour, button tap targets increased to min 48px

---

## File Change Summary

| File | Action |
|---|---|
| `app/models/team.py` | Delete |
| `app/models/fridge.py` | Delete |
| `app/models/__init__.py` | Remove Team, Fridge exports |
| `app/models/drink.py` | Remove team_id, fridge_id columns |
| `app/models/user.py` | Remove team_id column |
| `app/models/consumption.py` | Remove team_id, fridge_id columns |
| `app/schemas/drink.py` | Remove team_id, fridge_id; fix stock_quantity null |
| `app/schemas/admin.py` | Remove team_id from UserCreate/UserUpdate |
| `app/api/admin.py` | Remove teams/fridges endpoints; remove ensure_*_exists helpers |
| `app/api/user.py` | Remove team_id filter from GET /drinks |
| `app/services/reporting.py` | Fix monthly_drink_report_rows outer join |
| `app/main.py` | Update ensure_schema_compat() with DROP statements |
| `app/static/css/app.css` | Replace with full design system |
| `app/static/favicon.svg` | New (from ZIP assets) |
| `app/static/logo-wordmark.svg` | New (from ZIP assets) |
| `app/templates/admin.html` | Two-col layout, Lucide, logo, drink modal markup |
| `app/templates/dashboard.html` | Mobile topbar, updated drink grid markup |
| `app/templates/login.html` | Favicon link, minor token updates |
| `app/static/js/admin.js` | Full rewrite: thumbnail rows, modals, no teams/fridges |
| `app/static/js/dashboard.js` | Updated card template, overflow menu wiring |
| `app/tests/` | Update fixtures/tests that reference team_id or fridge_id |

---

## What Is Not Changing

- Authentication flow (JWT cookie, remember-me, registration + approval)
- Billing and reporting logic (`billing_job.py`, `reporting.py` beyond the bug fix)
- SMTP / email delivery
- Docker setup and deployment scripts
- PayPal integration
- Consumption undo logic
