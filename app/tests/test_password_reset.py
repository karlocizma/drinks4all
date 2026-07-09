import pytest

from app.core.security import (
    create_password_reset_token,
    decode_password_reset_token,
    get_password_hash,
    password_fingerprint,
)
from app.models import User, UserRole


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
