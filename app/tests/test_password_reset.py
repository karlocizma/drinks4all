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
