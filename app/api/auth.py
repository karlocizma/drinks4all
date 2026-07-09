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


@router.post("/login", response_model=UserOut)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> UserOut:
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active and user.is_pending_approval:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account pending admin approval")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")

    expires_minutes = (
        settings.remember_me_days * 24 * 60 if payload.remember_me else settings.access_token_expire_minutes
    )
    token = create_access_token(str(user.id), user.role.value, expires_minutes=expires_minutes)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=expires_minutes * 60,
    )
    return UserOut.model_validate(user)


@router.post("/logout")
def logout(response: Response) -> dict:
    response.delete_cookie("access_token")
    return {"ok": True}


@router.post("/register")
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> dict:
    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing:
        raise HTTPException(status_code=409, detail="Email already exists")

    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=get_password_hash(payload.password),
        role=UserRole.USER,
        is_active=False,
        is_pending_approval=True,
    )
    db.add(user)
    db.commit()
    return {"ok": True, "message": "Registration submitted. Wait for admin approval."}


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
