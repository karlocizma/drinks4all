# Password Reset Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users reset a forgotten password from the login screen, without a new database table.

**Architecture:** Two new endpoints on the existing `app/api/auth.py` router. Reset tokens are stateless JWTs (reusing the existing `jose`-based machinery in `app/core/security.py`), scoped with a `purpose` claim and fingerprinted to the user's current `password_hash` so a token stops working the instant a reset succeeds. The frontend follows the existing same-page-modal pattern already used for "Create Account" on `login.html`.

**Tech Stack:** FastAPI, `python-jose` (already a dependency), Jinja2 email templates (already established in `app/templates/emails/`), vanilla JS (no framework), pytest + `TestClient`.

## Global Constraints

- No new Alembic migration, no new database table — this is a stateless-JWT design, not a `password_reset_tokens` table.
- `POST /auth/forgot-password` must return an identical response body and status code regardless of whether the email exists, is inactive, or is pending approval — this is a hard requirement, not a nice-to-have, to prevent user enumeration.
- `POST /auth/reset-password` must return the same generic `400 "Invalid or expired reset link"` detail for every rejection reason (bad signature, expired, wrong purpose, unknown user, fingerprint mismatch) — do not return different messages per case.
- Reset tokens expire after `PASSWORD_RESET_EXPIRE_MINUTES` (default 30).
- Follow existing conventions exactly: one test file per concern (`app/tests/test_password_reset.py`), Jinja2 email templates extend `emails/_layout.html`, frontend modals reuse `.modal-backdrop`/`.modal`/`.modal-head`/`.modal-actions` CSS classes already in `app/static/css/app.css`.

Spec: `docs/superpowers/specs/2026-07-08-password-reset-design.md`

---

### Task 1: Settings + token functions (foundation)

**Files:**
- Modify: `app/core/settings.py` (add two settings after `cookie_secure: bool = False`, currently the last line of the auth-related group)
- Modify: `app/core/security.py` (append three new functions)
- Test: `app/tests/test_password_reset.py` (new file — this task adds only the token-function tests; later tasks append more tests to the same file)

**Interfaces:**
- Produces: `settings.app_base_url: str` (default `"http://localhost:8000"`), `settings.password_reset_expire_minutes: int` (default `30`), `password_fingerprint(password_hash: str) -> str`, `create_password_reset_token(user_id: str, password_hash: str, expires_minutes: int | None = None) -> str`, `decode_password_reset_token(token: str) -> tuple[int, str]` (returns `(user_id, pwd_fp_claim)`, raises `ValueError` on bad signature/expiry/wrong purpose/missing claims).

- [ ] **Step 1: Write the failing tests**

Create `app/tests/test_password_reset.py`:

```python
import pytest

from app.core.security import (
    create_password_reset_token,
    decode_password_reset_token,
    get_password_hash,
    password_fingerprint,
)


def test_password_fingerprint_is_deterministic_and_hash_specific():
    fp1 = password_fingerprint("hash-a")
    fp2 = password_fingerprint("hash-a")
    fp3 = password_fingerprint("hash-b")
    assert fp1 == fp2
    assert fp1 != fp3


def test_create_and_decode_password_reset_token_roundtrip():
    password_hash = get_password_hash("whatever123")
    token = create_password_reset_token("42", password_hash)

    user_id, pwd_fp = decode_password_reset_token(token)
    assert user_id == 42
    assert pwd_fp == password_fingerprint(password_hash)


def test_decode_password_reset_token_rejects_expired_token():
    password_hash = get_password_hash("whatever123")
    token = create_password_reset_token("42", password_hash, expires_minutes=-1)

    with pytest.raises(ValueError):
        decode_password_reset_token(token)


def test_decode_password_reset_token_rejects_wrong_purpose():
    from app.core.security import create_access_token

    token = create_access_token("42", "USER")

    with pytest.raises(ValueError):
        decode_password_reset_token(token)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest app/tests/test_password_reset.py -v`
Expected: FAIL (or ERROR) — `create_password_reset_token`, `decode_password_reset_token`, `password_fingerprint` don't exist yet (`ImportError`).

- [ ] **Step 3: Add the new settings**

In `app/core/settings.py`, the `Settings` class currently has this block:

```python
    access_token_expire_minutes: int = 60 * 8
    remember_me_days: int = 30
    cookie_secure: bool = False
```

Change it to:

```python
    access_token_expire_minutes: int = 60 * 8
    remember_me_days: int = 30
    cookie_secure: bool = False
    app_base_url: str = "http://localhost:8000"
    password_reset_expire_minutes: int = 30
```

- [ ] **Step 4: Add the token functions**

In `app/core/security.py`, the current full file is:

```python
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.settings import settings

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(subject: str, role: str, expires_minutes: int | None = None) -> str:
    minutes = expires_minutes if expires_minutes is not None else settings.access_token_expire_minutes
    expire = datetime.now(UTC) + timedelta(minutes=minutes)
    payload = {"sub": subject, "role": role, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError as exc:
        raise ValueError("Invalid token") from exc
```

Replace the top import line and append the three new functions at the end, so the full file becomes:

```python
import hashlib
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.settings import settings

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(subject: str, role: str, expires_minutes: int | None = None) -> str:
    minutes = expires_minutes if expires_minutes is not None else settings.access_token_expire_minutes
    expire = datetime.now(UTC) + timedelta(minutes=minutes)
    payload = {"sub": subject, "role": role, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError as exc:
        raise ValueError("Invalid token") from exc


def password_fingerprint(password_hash: str) -> str:
    """Deterministic, non-reversible fingerprint of a password hash.

    Used to bind a password-reset token to the user's *current* password_hash:
    once the hash changes (i.e. a reset succeeds), the fingerprint no longer
    matches, so every outstanding reset token for that user stops validating.
    """
    return hashlib.sha256(password_hash.encode()).hexdigest()[:16]


def create_password_reset_token(user_id: str, password_hash: str, expires_minutes: int | None = None) -> str:
    minutes = expires_minutes if expires_minutes is not None else settings.password_reset_expire_minutes
    expire = datetime.now(UTC) + timedelta(minutes=minutes)
    payload = {
        "sub": user_id,
        "purpose": "password_reset",
        "pwd_fp": password_fingerprint(password_hash),
        "exp": expire,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_password_reset_token(token: str) -> tuple[int, str]:
    """Returns (user_id, pwd_fp_claim). Raises ValueError on bad signature,
    expiry, or purpose != "password_reset". Does not check the fingerprint
    against a user -- the caller must load the user and compare, since the
    token alone doesn't say whose *current* hash to check against."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError as exc:
        raise ValueError("Invalid or expired reset link") from exc
    if payload.get("purpose") != "password_reset":
        raise ValueError("Invalid or expired reset link")
    user_id = payload.get("sub")
    pwd_fp = payload.get("pwd_fp")
    if not user_id or not pwd_fp:
        raise ValueError("Invalid or expired reset link")
    return int(user_id), pwd_fp
```

- [ ] **Step 5: Run ruff to fix import ordering**

Run: `ruff check app/core/security.py --fix`
Expected: clean or auto-fixed (the `import hashlib` / `from datetime import ...` ordering).

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest app/tests/test_password_reset.py -v`
Expected: 4 passed.

- [ ] **Step 7: Commit**

```bash
git add app/core/settings.py app/core/security.py app/tests/test_password_reset.py
git commit -m "feat: add password-reset token functions

Stateless JWT, scoped with a purpose claim and fingerprinted to the
user's current password_hash so a token stops validating the instant
a reset succeeds -- no new database table needed."
```

---

### Task 2: `POST /auth/forgot-password` + email template

**Files:**
- Create: `app/templates/emails/password_reset.html`
- Modify: `app/schemas/auth.py` (add `ForgotPasswordRequest`)
- Modify: `app/api/auth.py` (add the endpoint)
- Test: `app/tests/test_password_reset.py` (append)

**Interfaces:**
- Consumes: `create_password_reset_token(user_id, password_hash) -> str` and `settings.app_base_url`, `settings.password_reset_expire_minutes` from Task 1; `render_email(template_name, **context) -> str` and `send_email(recipient, subject, body, html=...)` from `app/services/emailer.py` (already exist).
- Produces: `POST /auth/forgot-password` — request `{"email": str}`, response always `200 {"ok": true, "message": "If that email exists, a reset link has been sent."}`.

- [ ] **Step 1: Write the failing tests**

Append to `app/tests/test_password_reset.py`:

```python
from app.core.security import get_password_hash
from app.models import User, UserRole


def test_forgot_password_sends_email_for_existing_active_user(client, normal_user, monkeypatch):
    sent = []
    monkeypatch.setattr("app.api.auth.send_email", lambda *a, **k: sent.append(a))

    res = client.post("/auth/forgot-password", json={"email": normal_user.email})

    assert res.status_code == 200
    assert res.json() == {"ok": True, "message": "If that email exists, a reset link has been sent."}
    assert len(sent) == 1


def test_forgot_password_generic_response_for_unknown_email(client, monkeypatch):
    sent = []
    monkeypatch.setattr("app.api.auth.send_email", lambda *a, **k: sent.append(a))

    res = client.post("/auth/forgot-password", json={"email": "nobody@example.com"})

    assert res.status_code == 200
    assert res.json() == {"ok": True, "message": "If that email exists, a reset link has been sent."}
    assert len(sent) == 0


def test_forgot_password_generic_response_for_pending_user(client, db, monkeypatch):
    pending = User(
        name="Pending",
        email="pending@test.local",
        password_hash=get_password_hash("whatever123"),
        role=UserRole.USER,
        is_active=False,
        is_pending_approval=True,
    )
    db.add(pending)
    db.commit()

    sent = []
    monkeypatch.setattr("app.api.auth.send_email", lambda *a, **k: sent.append(a))

    res = client.post("/auth/forgot-password", json={"email": "pending@test.local"})

    assert res.status_code == 200
    assert res.json() == {"ok": True, "message": "If that email exists, a reset link has been sent."}
    assert len(sent) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest app/tests/test_password_reset.py -v`
Expected: the three new tests FAIL with `404 Not Found` (endpoint doesn't exist yet).

- [ ] **Step 3: Create the email template**

Create `app/templates/emails/password_reset.html`:

```html
{% extends "emails/_layout.html" %}
{% set subtitle = "Password Reset" %}
{% set max_width = 480 %}
{% set header_padding = "22px 28px" %}
{% set body_padding = "24px 28px" %}
{% set footer_padding = "16px 28px" %}
{% set brand_size = 20 %}
{% block content %}
<p style="margin:0 0 4px;font-size:15px;font-weight:600;color:#0f172a;">Reset your password</p>
<p style="margin:0 0 20px;font-size:14px;color:#64748b;">We received a request to reset your ALBdrinks password. This link expires in {{ expires_minutes }} minutes.</p>
<p style="text-align:center;margin:24px 0 0;">
  <a href="{{ reset_link }}" style="display:inline-block;background:#009cde;color:#ffffff;font-size:15px;font-weight:700;text-decoration:none;padding:13px 32px;border-radius:8px;">Reset Password</a></p>
<p style="margin:20px 0 0;font-size:12px;color:#94a3b8;">If you didn't request this, you can safely ignore this email.</p>
{% endblock %}
```

- [ ] **Step 4: Add the schema**

In `app/schemas/auth.py`, the current file is:

```python
from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str
    password: str
    remember_me: bool = False


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    is_active: bool

    model_config = {"from_attributes": True}
```

Append at the end:

```python


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
```

(Both schemas are added now even though `ResetPasswordRequest` isn't used until Task 3, since they're one small, obviously-related addition to the same file.)

- [ ] **Step 5: Add the endpoint**

In `app/api/auth.py`, the current top of the file is:

```python
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, get_password_hash, verify_password
from app.core.settings import settings
from app.db.database import get_db
from app.models import User, UserRole
from app.schemas.auth import LoginRequest, RegisterRequest, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])
```

Replace it with:

```python
import logging

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    create_password_reset_token,
    decode_password_reset_token,
    get_password_hash,
    password_fingerprint,
    verify_password,
)
from app.core.settings import settings
from app.db.database import get_db
from app.models import User, UserRole
from app.schemas.auth import ForgotPasswordRequest, LoginRequest, RegisterRequest, ResetPasswordRequest, UserOut
from app.services.emailer import render_email, send_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])
```

Then append this endpoint at the end of the file (after the existing `register` endpoint):

```python


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)) -> dict:
    generic_response = {"ok": True, "message": "If that email exists, a reset link has been sent."}

    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or not user.is_active:
        return generic_response

    token = create_password_reset_token(str(user.id), user.password_hash)
    reset_link = f"{settings.app_base_url.rstrip('/')}/?reset_token={token}"
    body = (
        "We received a request to reset your ALBdrinks password.\n\n"
        f"Reset link (expires in {settings.password_reset_expire_minutes} minutes):\n{reset_link}\n\n"
        "If you didn't request this, you can safely ignore this email.\n"
    )
    html = render_email(
        "emails/password_reset.html",
        reset_link=reset_link,
        expires_minutes=settings.password_reset_expire_minutes,
    )

    try:
        send_email(user.email, "Reset your ALBdrinks password", body, html=html)
    except Exception:
        logger.warning("Failed to send password reset email to %s", user.email, exc_info=True)

    return generic_response
```

- [ ] **Step 6: Run ruff**

Run: `ruff check app/api/auth.py app/schemas/auth.py --fix`
Expected: clean. (`app/templates/emails/password_reset.html` is a Jinja template, not linted by ruff.)

- [ ] **Step 7: Run tests to verify they pass**

Run: `pytest app/tests/test_password_reset.py -v`
Expected: 7 passed (4 from Task 1, 3 new).

- [ ] **Step 8: Commit**

```bash
git add app/templates/emails/password_reset.html app/schemas/auth.py app/api/auth.py app/tests/test_password_reset.py
git commit -m "feat: add POST /auth/forgot-password

Always returns an identical response regardless of whether the email
exists, is inactive, or is pending approval, to avoid leaking which
addresses are registered."
```

---

### Task 3: `POST /auth/reset-password`

**Files:**
- Modify: `app/api/auth.py` (add the endpoint)
- Test: `app/tests/test_password_reset.py` (append)

**Interfaces:**
- Consumes: `decode_password_reset_token(token) -> tuple[int, str]`, `password_fingerprint(password_hash) -> str`, `create_password_reset_token(...)` from Task 1; `ResetPasswordRequest` schema from Task 2 (already added).
- Produces: `POST /auth/reset-password` — request `{"token": str, "new_password": str}`, response `200 {"ok": true}` on success, `400 {"detail": "..."}` on failure.

- [ ] **Step 1: Write the failing tests**

Append to `app/tests/test_password_reset.py`:

```python
from app.core.security import create_access_token, create_password_reset_token


def test_reset_password_succeeds_and_allows_login_with_new_password(client, normal_user):
    token = create_password_reset_token(str(normal_user.id), normal_user.password_hash)

    res = client.post("/auth/reset-password", json={"token": token, "new_password": "newpass123"})
    assert res.status_code == 200
    assert res.json() == {"ok": True}

    login = client.post("/auth/login", json={"email": normal_user.email, "password": "newpass123"})
    assert login.status_code == 200


def test_reset_password_rejects_expired_token(client, normal_user):
    token = create_password_reset_token(str(normal_user.id), normal_user.password_hash, expires_minutes=-1)

    res = client.post("/auth/reset-password", json={"token": token, "new_password": "newpass123"})
    assert res.status_code == 400


def test_reset_password_rejects_wrong_purpose_token(client, normal_user):
    token = create_access_token(str(normal_user.id), normal_user.role.value)

    res = client.post("/auth/reset-password", json={"token": token, "new_password": "newpass123"})
    assert res.status_code == 400


def test_reset_password_rejects_reused_token_after_password_changed(client, normal_user):
    token = create_password_reset_token(str(normal_user.id), normal_user.password_hash)

    first = client.post("/auth/reset-password", json={"token": token, "new_password": "firstpass123"})
    assert first.status_code == 200

    second = client.post("/auth/reset-password", json={"token": token, "new_password": "secondpass123"})
    assert second.status_code == 400


def test_reset_password_rejects_short_new_password(client, normal_user):
    token = create_password_reset_token(str(normal_user.id), normal_user.password_hash)

    res = client.post("/auth/reset-password", json={"token": token, "new_password": "abc"})
    assert res.status_code == 400
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest app/tests/test_password_reset.py -v`
Expected: the five new tests FAIL with `404 Not Found`.

- [ ] **Step 3: Add the endpoint**

Append to `app/api/auth.py`, after the `forgot_password` endpoint added in Task 2:

```python


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)) -> dict:
    try:
        user_id, pwd_fp = decode_password_reset_token(payload.token)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link") from exc

    user = db.scalar(select(User).where(User.id == user_id))
    if user is None or password_fingerprint(user.password_hash) != pwd_fp:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link")

    if len(payload.new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters")

    user.password_hash = get_password_hash(payload.new_password)
    db.commit()
    return {"ok": True}
```

- [ ] **Step 4: Run ruff**

Run: `ruff check app/api/auth.py --fix`
Expected: clean.

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest app/tests/test_password_reset.py -v`
Expected: 12 passed.

- [ ] **Step 6: Run the full suite to check for regressions**

Run: `pytest -q`
Expected: all tests pass (was 14 before this plan; should be 26 now — 14 existing + 12 in `test_password_reset.py`).

- [ ] **Step 7: Commit**

```bash
git add app/api/auth.py app/tests/test_password_reset.py
git commit -m "feat: add POST /auth/reset-password

Rejects with an identical generic message for every failure reason
(expired, wrong purpose, unknown user, already-used token) so no
information leaks through error responses."
```

---

### Task 4: Frontend — "Forgot password?" + reset form on the login page

**Files:**
- Modify: `app/templates/login.html`
- Modify: `app/static/js/login.js`
- Modify: `app/static/css/app.css` (add one small class)

**Interfaces:**
- Consumes: `POST /auth/forgot-password` and `POST /auth/reset-password` from Tasks 2–3 (called via `fetch`, same pattern as the existing login/register forms in `login.js`).
- Produces: no new interfaces for other tasks to consume — this is the last functional piece.

- [ ] **Step 1: Add the `.link-button` CSS class**

In `app/static/css/app.css`, find this block:

```css
.login-actions {
  display: grid;
  gap: 0.55rem;
  margin-top: 0.65rem;
}
```

Add immediately after it:

```css

.link-button {
  background: none;
  border: none;
  color: var(--accent);
  text-decoration: underline;
  font-size: 0.85rem;
  width: auto;
  padding: 0;
  cursor: pointer;
}
```

- [ ] **Step 2: Update `login.html`**

Replace the entire file with:

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>ALBdrinks - Login</title>
  <link rel="icon" href="/static/favicon.svg" />
  <link rel="stylesheet" href="/static/css/app.css" />
</head>
<body>
  <main class="container auth-shell">
    <section class="card" id="login-card">
      <img src="/static/logo-wordmark.svg" alt="ALBdrinks" style="height:52px;display:block;margin:0 auto 0.5rem;" />
      <p>Sign in with your assigned account.</p>
      <form id="login-form" class="grid">
        <label>Email <input type="email" id="email" autocomplete="username" required /></label>
        <label>Password <input type="password" id="password" autocomplete="current-password" required /></label>
        <label><input type="checkbox" id="remember-me" /> Stay logged in (remember me)</label>
      </form>
      <div class="login-actions">
        <button type="submit" form="login-form">Login</button>
        <button type="button" id="open-register-modal">Create Account</button>
      </div>
      <p><button type="button" id="open-forgot-password-modal" class="link-button">Forgot password?</button></p>
      <p id="error" class="error"></p>
    </section>

    <section class="card hidden" id="reset-password-card" hidden>
      <img src="/static/logo-wordmark.svg" alt="ALBdrinks" style="height:52px;display:block;margin:0 auto 0.5rem;" />
      <p>Choose a new password.</p>
      <form id="reset-password-form" class="grid">
        <label>New password <input type="password" id="reset-new-password" autocomplete="new-password" required /></label>
      </form>
      <div class="login-actions">
        <button type="submit" form="reset-password-form">Set new password</button>
      </div>
      <p id="reset-error" class="error"></p>
    </section>
  </main>

  <div id="register-modal" class="modal-backdrop hidden" hidden>
    <section class="card modal">
      <div class="modal-head">
        <h3>Create ALBdrinks Account</h3>
      </div>
      <p>Registration requires admin approval.</p>
      <form id="register-form" class="grid compact-form">
        <label>Name <input type="text" id="reg-name" required /></label>
        <label>Email <input type="email" id="reg-email" required /></label>
        <label>Password <input type="password" id="reg-password" required /></label>
        <div class="modal-actions">
          <button type="submit">Submit Registration</button>
          <button type="button" id="close-register-modal" class="btn-secondary">Close</button>
        </div>
      </form>
    </section>
  </div>

  <div id="forgot-password-modal" class="modal-backdrop hidden" hidden>
    <section class="card modal">
      <div class="modal-head">
        <h3>Reset your password</h3>
      </div>
      <p>Enter your account email and we'll send you a reset link.</p>
      <form id="forgot-password-form" class="grid compact-form">
        <label>Email <input type="email" id="forgot-email" required /></label>
        <div class="modal-actions">
          <button type="submit">Send reset link</button>
          <button type="button" id="close-forgot-password-modal" class="btn-secondary">Close</button>
        </div>
      </form>
      <p id="forgot-password-message"></p>
    </section>
  </div>

  <script src="/static/js/login.js"></script>
</body>
</html>
```

- [ ] **Step 3: Update `login.js`**

Replace the entire file with:

```js
const form = document.getElementById('login-form');
const registerForm = document.getElementById('register-form');
const registerModal = document.getElementById('register-modal');
const openRegisterModalBtn = document.getElementById('open-register-modal');
const closeRegisterModalBtn = document.getElementById('close-register-modal');
const errorEl = document.getElementById('error');

const loginCard = document.getElementById('login-card');
const resetPasswordCard = document.getElementById('reset-password-card');
const resetPasswordForm = document.getElementById('reset-password-form');
const resetErrorEl = document.getElementById('reset-error');

const forgotPasswordModal = document.getElementById('forgot-password-modal');
const openForgotPasswordModalBtn = document.getElementById('open-forgot-password-modal');
const closeForgotPasswordModalBtn = document.getElementById('close-forgot-password-modal');
const forgotPasswordForm = document.getElementById('forgot-password-form');
const forgotPasswordMessageEl = document.getElementById('forgot-password-message');

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  errorEl.textContent = '';

  const email = document.getElementById('email').value;
  const password = document.getElementById('password').value;
  const remember_me = document.getElementById('remember-me').checked;

  const response = await fetch('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, remember_me }),
  });

  if (!response.ok) {
    const msg = await response.text();
    errorEl.textContent = msg || 'Login failed. Check credentials.';
    return;
  }

  const user = await response.json();
  window.location.href = user.role === 'ADMIN' ? '/admin' : '/dashboard';
});

registerForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  errorEl.textContent = '';

  const name = document.getElementById('reg-name').value;
  const email = document.getElementById('reg-email').value;
  const password = document.getElementById('reg-password').value;

  const response = await fetch('/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, email, password }),
  });

  if (!response.ok) {
    const msg = await response.text();
    errorEl.textContent = msg || 'Registration failed.';
    return;
  }

  errorEl.textContent = 'Registration submitted. Wait for admin approval.';
  registerForm.reset();
  closeRegisterModal();
});

function openRegisterModal() {
  registerModal.classList.remove('hidden');
  registerModal.removeAttribute('hidden');
}

function closeRegisterModal() {
  registerModal.classList.add('hidden');
  registerModal.setAttribute('hidden', '');
}

openRegisterModalBtn?.addEventListener('click', openRegisterModal);
closeRegisterModalBtn?.addEventListener('click', closeRegisterModal);

registerModal?.addEventListener('click', (e) => {
  if (e.target === registerModal) {
    closeRegisterModal();
  }
});

function openForgotPasswordModal() {
  forgotPasswordMessageEl.textContent = '';
  forgotPasswordModal.classList.remove('hidden');
  forgotPasswordModal.removeAttribute('hidden');
}

function closeForgotPasswordModal() {
  forgotPasswordModal.classList.add('hidden');
  forgotPasswordModal.setAttribute('hidden', '');
}

openForgotPasswordModalBtn?.addEventListener('click', openForgotPasswordModal);
closeForgotPasswordModalBtn?.addEventListener('click', closeForgotPasswordModal);

forgotPasswordModal?.addEventListener('click', (e) => {
  if (e.target === forgotPasswordModal) {
    closeForgotPasswordModal();
  }
});

forgotPasswordForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const email = document.getElementById('forgot-email').value;

  const response = await fetch('/auth/forgot-password', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  });

  const data = await response.json();
  forgotPasswordMessageEl.textContent = data.message || 'If that email exists, a reset link has been sent.';
});

const resetToken = new URLSearchParams(window.location.search).get('reset_token');
if (resetToken) {
  loginCard.classList.add('hidden');
  loginCard.setAttribute('hidden', '');
  resetPasswordCard.classList.remove('hidden');
  resetPasswordCard.removeAttribute('hidden');
}

resetPasswordForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  resetErrorEl.textContent = '';

  const new_password = document.getElementById('reset-new-password').value;

  const response = await fetch('/auth/reset-password', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token: resetToken, new_password }),
  });

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    resetErrorEl.textContent = data.detail || 'Could not reset password.';
    return;
  }

  window.location.href = '/';
});
```

- [ ] **Step 4: Manually verify the full flow against the running app**

There's no JS test framework in this repo — verify by driving the real app.

```bash
cp .env.example .env
docker compose up --build -d
```

Using the Playwright MCP tools (`browser_navigate`, `browser_click`, `browser_fill_form`, `browser_snapshot`):

1. Navigate to `http://localhost:8000/`. Confirm "Forgot password?" is visible under the login button.
2. Click it, fill the email field with `admin@drinks.local`, submit. Confirm the modal shows "If that email exists, a reset link has been sent."
3. Fetch `http://localhost:8025/api/v2/messages` (MailHog API) and confirm a new message to `admin@drinks.local` with subject "Reset your ALBdrinks password" exists; extract the `reset_link` URL from its body (it contains `?reset_token=...`).
4. Navigate to that extracted URL. Confirm the login form is hidden and a "Set new password" form is shown instead.
5. Fill in a new password (e.g. `newadminpass123`), submit. Confirm the page redirects to `/` and the plain login form is shown again (no `reset_token` in the URL).
6. Log in with `admin@drinks.local` / `newadminpass123`. Confirm login succeeds.
7. `docker compose down -v` to tear down and discard the test data.

- [ ] **Step 5: Run ruff and the full test suite one more time**

Run: `ruff check .`
Expected: clean.

Run: `pytest -q`
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add app/templates/login.html app/static/js/login.js app/static/css/app.css
git commit -m "feat: add forgot-password link and reset form to login page

Follows the existing same-page-modal pattern already used for
Create Account. Reset mode is triggered by a ?reset_token= query
param, matching this app's no-client-routing convention."
```

---

### Task 5: Documentation

**Files:**
- Modify: `.env.example`
- Modify: `docker-compose.yml`
- Modify: `README.md`
- Modify: `CLAUDE.md`

**Interfaces:**
- Consumes: nothing new — this task only documents what Tasks 1–4 already built.
- Produces: nothing consumed by other tasks — this is the last task in the plan.

- [ ] **Step 1: Update `.env.example`**

Find this line:

```
REMEMBER_ME_DAYS=30
COOKIE_SECURE=false
```

Change to:

```
REMEMBER_ME_DAYS=30
COOKIE_SECURE=false
APP_BASE_URL=http://localhost:8000
PASSWORD_RESET_EXPIRE_MINUTES=30
```

- [ ] **Step 2: Update `docker-compose.yml`**

Find this line in the `app` service's `environment:` block:

```yaml
      REMEMBER_ME_DAYS: ${REMEMBER_ME_DAYS:-30}
      COOKIE_SECURE: ${COOKIE_SECURE:-false}
```

Change to:

```yaml
      REMEMBER_ME_DAYS: ${REMEMBER_ME_DAYS:-30}
      COOKIE_SECURE: ${COOKIE_SECURE:-false}
      APP_BASE_URL: ${APP_BASE_URL:-http://localhost:8000}
      PASSWORD_RESET_EXPIRE_MINUTES: ${PASSWORD_RESET_EXPIRE_MINUTES:-30}
```

- [ ] **Step 3: Update `README.md`**

In the Environment Variables table, find this row:

```
| `COOKIE_SECURE` | Set to `true` once the app is served over HTTPS, so the auth cookie only travels encrypted. Keep `false` for plain-HTTP local/dev setups. |
```

Add immediately after it:

```
| `APP_BASE_URL` | Base URL used to build the password-reset link sent by email (e.g. `https://drinks.example.com`). |
| `PASSWORD_RESET_EXPIRE_MINUTES` | How long a password-reset link stays valid. |
```

In the Key API table, find this row:

```
| `POST` | `/auth/register` | Self-register (pending admin approval) |
```

Add immediately after it:

```
| `POST` | `/auth/forgot-password` | Request a password reset email (always returns a generic response) |
| `POST` | `/auth/reset-password` | Reset password using the token from that email |
```

- [ ] **Step 4: Update `CLAUDE.md`**

In the Architecture section, find this paragraph:

```
**Auth:** JWT is issued in `app/core/security.py` and carried in an **httponly cookie** named `access_token` (not an Authorization header). `app/api/deps.py` provides `get_current_user` (reads the cookie, decodes JWT, loads the user) and `require_admin` (wraps it with a role check). All protected routes depend on one of these. The cookie's `Secure` flag is controlled by `settings.cookie_secure` (`COOKIE_SECURE` env var, default `false`) — set it `true` once the app is behind HTTPS.
```

Add immediately after it:

```
**Password reset** (`POST /auth/forgot-password`, `POST /auth/reset-password`) uses stateless JWTs, not a database table. `app/core/security.py:create_password_reset_token`/`decode_password_reset_token` scope the token with a `purpose: password_reset` claim (so a login-session JWT can't be replayed here) and fingerprint it to the user's *current* `password_hash` (`password_fingerprint`). Since a successful reset changes `password_hash`, the fingerprint on every previously issued token for that user — including the one just used — stops matching immediately. That's what makes the token single-use without a database table. Both endpoints return an identical response for every failure/non-existence case, by design, to avoid leaking which emails are registered.
```

- [ ] **Step 5: Commit**

```bash
git add .env.example docker-compose.yml README.md CLAUDE.md
git commit -m "docs: document password reset (APP_BASE_URL, new endpoints)"
```

---

## Plan Self-Review

**Spec coverage:** Token design (Task 1), forgot-password endpoint + generic-response requirement (Task 2), reset-password endpoint + generic-failure-message requirement (Task 3), email template (Task 2), frontend modal + reset-mode flow (Task 4), settings/docs (Task 5), test file (Tasks 1–3). All spec sections have a task.

**Placeholder scan:** No TBD/TODO; every step has complete, runnable code.

**Type consistency:** `create_password_reset_token(user_id: str, password_hash: str, expires_minutes: int | None = None) -> str` (Task 1) is called identically in Task 2 (`create_password_reset_token(str(user.id), user.password_hash)`) and in tests (Tasks 1 and 3). `decode_password_reset_token(token: str) -> tuple[int, str]` (Task 1) is consumed identically in Task 3's endpoint (`user_id, pwd_fp = decode_password_reset_token(payload.token)`). `password_fingerprint(password_hash: str) -> str` (Task 1) is used identically when creating (inside `create_password_reset_token`) and verifying (Task 3's endpoint) tokens.
