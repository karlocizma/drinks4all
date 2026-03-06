from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, desc, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import get_password_hash, verify_password
from app.core.settings import settings
from app.db.database import get_db
from app.models import Consumption, Drink, User
from app.schemas.admin import PasswordChange
from app.schemas.consumption import ConsumptionCreate, ConsumptionOut
from app.services.reporting import user_month_summary

router = APIRouter(tags=["user"])


@router.get("/drinks")
def list_drinks(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[dict]:
    filters = [Drink.is_active.is_(True)]
    if current_user.team_id is not None:
        filters.append((Drink.team_id == current_user.team_id) | (Drink.team_id.is_(None)))

    drinks = db.scalars(select(Drink).where(and_(*filters)).order_by(Drink.name.asc())).all()
    return [
        {
            "id": d.id,
            "name": d.name,
            "photo_url": d.photo_url,
            "unit_price": float(d.unit_price),
            "stock_quantity": d.stock_quantity,
            "low_stock_threshold": d.low_stock_threshold,
            "team_id": d.team_id,
            "fridge_id": d.fridge_id,
            "is_active": d.is_active,
        }
        for d in drinks
    ]


@router.post("/consumptions", response_model=ConsumptionOut)
def add_consumption(
    payload: ConsumptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConsumptionOut:
    drink = db.scalar(select(Drink).where(Drink.id == payload.drink_id, Drink.is_active.is_(True)))
    if drink is None:
        raise HTTPException(status_code=404, detail="Drink not found")

    if payload.quantity < 1:
        raise HTTPException(status_code=400, detail="Quantity must be >= 1")

    if drink.stock_quantity is not None and drink.stock_quantity < payload.quantity:
        raise HTTPException(status_code=400, detail="Not enough stock")

    if drink.stock_quantity is not None:
        drink.stock_quantity -= payload.quantity

    consumption = Consumption(
        user_id=current_user.id,
        drink_id=drink.id,
        team_id=current_user.team_id,
        fridge_id=drink.fridge_id,
        quantity=payload.quantity,
        unit_price_at_time=drink.unit_price,
        consumed_at=datetime.utcnow(),
    )
    db.add(consumption)
    db.commit()
    db.refresh(consumption)
    return ConsumptionOut.model_validate(consumption)


@router.delete("/consumptions/last")
def undo_last_consumption(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    last = db.scalar(
        select(Consumption)
        .where(Consumption.user_id == current_user.id)
        .order_by(desc(Consumption.consumed_at))
        .limit(1)
    )
    if last is None:
        raise HTTPException(status_code=404, detail="No consumption to undo")

    drink = db.scalar(select(Drink).where(Drink.id == last.drink_id))
    if drink and drink.stock_quantity is not None:
        drink.stock_quantity += last.quantity

    db.delete(last)
    db.commit()
    return {"ok": True}


@router.get("/me/summary")
def get_my_summary(
    month: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    summary = user_month_summary(db, current_user.id, month)
    total_amount = float(summary["total_amount"])
    paypal_url = None
    if settings.paypal_me_url and total_amount > 0:
        paypal_url = f"{settings.paypal_me_url.rstrip('/')}/{total_amount:.2f}"
    return {
        "user_id": current_user.id,
        "month": month,
        "total_units": summary["total_units"],
        "total_amount": total_amount,
        "currency": "EUR",
        "paypal_url": paypal_url,
        "drinks": [{**d, "total_amount": float(d["total_amount"])} for d in summary["drinks"]],
    }


@router.post("/me/change-password")
def change_my_password(
    payload: PasswordChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    if not verify_password(payload.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Old password is incorrect")
    if len(payload.new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters")
    current_user.password_hash = get_password_hash(payload.new_password)
    db.commit()
    return {"ok": True}
