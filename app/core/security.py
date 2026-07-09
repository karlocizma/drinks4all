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
