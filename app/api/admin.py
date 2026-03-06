from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.security import get_password_hash
from app.db.database import get_db
from app.models import Drink, User, UserRole
from app.schemas.admin import PasswordReset, UserCreate, UserUpdate
from app.schemas.drink import DrinkCreate, DrinkUpdate
from app.services.billing_job import run_monthly_billing
from app.services.reporting import build_csv, build_pdf, monthly_drink_report_rows, monthly_user_report_rows

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users")
def list_users(db: Session = Depends(get_db), _: User = Depends(require_admin)) -> list[dict]:
    users = db.scalars(select(User).order_by(User.created_at.asc())).all()
    return [
        {
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "role": u.role.value,
            "is_active": u.is_active,
        }
        for u in users
    ]


@router.post("/users")
def create_user(payload: UserCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)) -> dict:
    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing:
        raise HTTPException(status_code=409, detail="Email already exists")

    role = UserRole.ADMIN if payload.role.upper() == UserRole.ADMIN.value else UserRole.USER
    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=get_password_hash(payload.password),
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "email": user.email, "role": user.role.value}


@router.put("/users/{user_id}")
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict:
    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.name is not None:
        user.name = payload.name
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.role is not None:
        user.role = UserRole.ADMIN if payload.role.upper() == UserRole.ADMIN.value else UserRole.USER

    db.commit()
    return {"ok": True}


@router.post("/users/{user_id}/reset-password")
def reset_user_password(
    user_id: int,
    payload: PasswordReset,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict:
    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.password_hash = get_password_hash(payload.password)
    db.commit()
    return {"ok": True}


@router.post("/drinks")
def create_drink(payload: DrinkCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)) -> dict:
    drink = Drink(
        name=payload.name,
        photo_url=str(payload.photo_url),
        unit_price=payload.unit_price,
        is_active=payload.is_active,
    )
    db.add(drink)
    db.commit()
    db.refresh(drink)
    return {"id": drink.id}


@router.put("/drinks/{drink_id}")
def update_drink(
    drink_id: int,
    payload: DrinkUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict:
    drink = db.scalar(select(Drink).where(Drink.id == drink_id))
    if not drink:
        raise HTTPException(status_code=404, detail="Drink not found")

    if payload.name is not None:
        drink.name = payload.name
    if payload.photo_url is not None:
        drink.photo_url = str(payload.photo_url)
    if payload.unit_price is not None:
        drink.unit_price = payload.unit_price
    if payload.is_active is not None:
        drink.is_active = payload.is_active
    db.commit()
    return {"ok": True}


@router.delete("/drinks/{drink_id}")
def delete_drink(drink_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)) -> dict:
    drink = db.scalar(select(Drink).where(Drink.id == drink_id))
    if not drink:
        raise HTTPException(status_code=404, detail="Drink not found")
    db.delete(drink)
    db.commit()
    return {"ok": True}


@router.get("/reports")
def get_reports(
    month: str,
    format: str = Query("json", pattern="^(json|csv|pdf)$"),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    user_rows = monthly_user_report_rows(db, month)
    drink_rows = monthly_drink_report_rows(db, month)
    total = sum(Decimal(row["total_amount"]) for row in user_rows)

    if format == "json":
        return {
            "month": month,
            "users": [
                {
                    **row,
                    "total_amount": float(row["total_amount"]),
                }
                for row in user_rows
            ],
            "drinks": [
                {
                    **row,
                    "total_amount": float(row["total_amount"]),
                }
                for row in drink_rows
            ],
            "overall_total": float(total),
        }

    if format == "csv":
        csv_data = build_csv(user_rows)
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=drinks-report-{month}.csv"},
        )

    pdf_data = build_pdf(user_rows, month)
    return Response(
        content=pdf_data,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=drinks-report-{month}.pdf"},
    )


@router.post("/run-billing")
def run_billing_now(
    month: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict:
    return run_monthly_billing(db, month)
