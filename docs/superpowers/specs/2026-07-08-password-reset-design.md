# Password Reset — Design Spec

**Date:** 2026-07-08
**Tracks:** GitHub issue #5, "Add password reset functionality to user login screen"

---

## Context

The login screen has no way to recover a forgotten password. Users must currently ask an admin to reset it via `POST /admin/users/{id}/reset-password`. This adds a self-service "Forgot password?" flow, following the same conventions already established for "Create Account" on the login page: same-page modal, no client-side routing, no new database table.

---

## Token design

No new `password_reset_tokens` table. Reset tokens are signed JWTs (reusing the existing `jose`/`secret_key` machinery in `app/core/security.py`), with two properties that a plain JWT wouldn't have on its own:

1. **Scoped to purpose.** The payload carries `"purpose": "password_reset"`, so a login-session JWT can never be replayed against the reset endpoint and vice versa.
2. **Single-use without server-side state.** The payload also carries a fingerprint of the user's *current* `password_hash` at issue time: `pwd_fp = sha256(password_hash)[:16]`. On reset, the token is only accepted if that fingerprint still matches the user's *current* `password_hash`. The moment a reset succeeds, `password_hash` changes, so the fingerprint stops matching — every outstanding token for that user (including the one just used, and any earlier ones from repeated forgot-password requests) is now dead. This gets single-use semantics "for free" from the property that resetting a password always changes the hash.

Tokens expire after `PASSWORD_RESET_EXPIRE_MINUTES` (default 30) regardless.

### New functions in `app/core/security.py`

```python
def password_fingerprint(password_hash: str) -> str:
    """First 16 hex chars of sha256(password_hash). Deterministic, not reversible."""

def create_password_reset_token(user_id: str, password_hash: str, expires_minutes: int | None = None) -> str:
    """Payload: {"sub": user_id, "purpose": "password_reset", "pwd_fp": ..., "exp": ...}"""

def decode_password_reset_token(token: str) -> tuple[int, str]:
    """Returns (user_id, pwd_fp_claim). Raises ValueError on bad signature, expiry,
    or purpose != "password_reset". Does NOT check the fingerprint against a user
    (caller must load the user and compare) since the token alone doesn't tell us
    which user's *current* hash to check against until decoded."""
```

---

## New settings (`app/core/settings.py`)

| Setting | Env var | Default | Purpose |
|---|---|---|---|
| `app_base_url` | `APP_BASE_URL` | `http://localhost:8000` | Base URL used to build the absolute reset link in the email. |
| `password_reset_expire_minutes` | `PASSWORD_RESET_EXPIRE_MINUTES` | `30` | Reset token lifetime. |

Both added to `.env.example`, `docker-compose.yml` (`environment:` block, same pattern as existing vars), and the README env var table.

---

## Endpoints (`app/api/auth.py`)

### `POST /auth/forgot-password`

Request: `{"email": "..."}` (new `ForgotPasswordRequest` schema in `app/schemas/auth.py`)

Response: **always** `200 {"ok": true, "message": "If that email exists, a reset link has been sent."}` — identical whether the email exists, doesn't exist, or belongs to an inactive/pending user. This is deliberate: it must not be possible to enumerate registered emails via this endpoint.

Behavior:
- Look up the user by email.
- Only if the user exists **and** `is_active` is true: create a reset token (`create_password_reset_token`), build `reset_link = f"{settings.app_base_url.rstrip('/')}/?reset_token={token}"`, render `emails/password_reset.html`, send via `send_email` (plain text + HTML, matching the existing pattern in `billing_job.py`).
- Send failures are caught and swallowed (logged server-side via `logging.warning`, not raised) — the response to the client is identical either way, so a transient SMTP failure doesn't leak anything either.
- No `EmailLog` row is written for this — `EmailLog.month` is billing-specific, and repurposing it for an unrelated auth flow would be a stretch. If we want observability here later, that's a separate, explicit decision.

### `POST /auth/reset-password`

Request: `{"token": "...", "new_password": "..."}` (new `ResetPasswordRequest` schema)

Response on success: `200 {"ok": true}`
Response on failure: `400` with a single generic detail — `"Invalid or expired reset link"` — for every rejection reason (bad signature, expired, wrong purpose, user not found, fingerprint mismatch). Reasons are deliberately not distinguished in the response, same rationale as forgot-password.

Separately, weak-password rejection uses its own message (`"New password must be at least 6 characters"`, matching the existing convention in `/auth/register` and `/me/change-password`) since it doesn't leak anything about account existence.

Behavior:
```python
try:
    user_id, pwd_fp = decode_password_reset_token(payload.token)
except ValueError:
    raise HTTPException(400, "Invalid or expired reset link")

user = db.scalar(select(User).where(User.id == user_id))
if user is None or password_fingerprint(user.password_hash) != pwd_fp:
    raise HTTPException(400, "Invalid or expired reset link")

if len(payload.new_password) < 6:
    raise HTTPException(400, "New password must be at least 6 characters")

user.password_hash = get_password_hash(payload.new_password)
db.commit()
return {"ok": True}
```

---

## Email template

New `app/templates/emails/password_reset.html`, extending the existing `emails/_layout.html` (same shared header/footer chrome as the other three email templates). Content: a short message, a button linking to `reset_link`, and a note that the link expires in `PASSWORD_RESET_EXPIRE_MINUTES` minutes. `max_width` 480, matching `low_stock_alert.html`'s narrower single-purpose layout.

`_user_statement_html`-style helper not needed — `app/api/auth.py` calls `render_email("emails/password_reset.html", reset_link=..., expires_minutes=...)` directly plus a plain-text body string, same as the low-stock alert in `user.py`.

---

## Frontend (`app/templates/login.html`, `app/static/js/login.js`)

Follows the existing "Create Account" modal pattern exactly (same `.modal-backdrop`/`.modal`/`.modal-head`/`.modal-actions` classes already in the file).

**Login page additions:**
- A "Forgot password?" text link under the login form.
- A new `#forgot-password-modal`: single email field + submit → `POST /auth/forgot-password` → show the generic response message in the modal, regardless of status code (there isn't a failure case worth surfacing differently).

**Reset-password mode:**
- On page load, `login.js` checks `new URLSearchParams(location.search).get('reset_token')`.
- If present: hide the normal login form, "Create Account" button, and "Forgot password?" link; show a "Set new password" form (one password field + submit) wired to `POST /auth/reset-password` with `{token, new_password}`.
- On success: redirect to `/` (drops the query param, shows the normal login form fresh).
- On failure: show the server's error message inline in that form's error slot; the token isn't consumed by a failed attempt, so the user can retry (e.g. after fixing a too-short password) without requesting a new email.

---

## Testing (`app/tests/test_password_reset.py`, new file — one file per concern, matching existing convention)

- `forgot-password` returns the identical response body/status for: an existing active user, a nonexistent email, and an inactive/pending user. (Monkeypatch `send_email` to a fake, matching the pattern in `test_low_stock_email_sent_once_when_threshold_is_crossed`, to assert an email *was* attempted only in the active-user case, without hitting real SMTP.)
- `reset-password` succeeds with a freshly issued valid token and actually changes the password (verified by logging in with the new password afterward).
- `reset-password` rejects: an expired token (construct via `expires_minutes=-1`), a token with the wrong `purpose` claim (e.g. a normal login token from `create_access_token`), a token whose fingerprint no longer matches (simulate by resetting once, then reusing the same token again), and a `new_password` under 6 characters.

---

## Files touched

**Modified:** `app/core/security.py`, `app/core/settings.py`, `app/schemas/auth.py`, `app/api/auth.py`, `app/templates/login.html`, `app/static/js/login.js`, `.env.example`, `docker-compose.yml`, `README.md`, `CLAUDE.md`

**New:** `app/templates/emails/password_reset.html`, `app/tests/test_password_reset.py`
