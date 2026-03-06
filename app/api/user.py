from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.database import get_db
from app.models import Consumption, Drink, User
from app.schemas.consumption import ConsumptionCreate, ConsumptionOut
from app.services.reporting import user_month_summary

router = APIRouter(tags=["user"])


@router.get("/drinks")
def list_drinks(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[dict]:
    drinks = db.scalars(select(Drink).where(Drink.is_active.is_(True)).order_by(Drink.name.asc())).all()
    return [
        {
            "id": d.id,
            "name": d.name,
            "photo_url": d.photo_url,
            "unit_price": float(d.unit_price),
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

    consumption = Consumption(
        user_id=current_user.id,
        drink_id=drink.id,
        quantity=payload.quantity,
        unit_price_at_time=drink.unit_price,
        consumed_at=datetime.utcnow(),
    )
    db.add(consumption)
    db.commit()
    db.refresh(consumption)
    return ConsumptionOut.model_validate(consumption)


@router.get("/me/summary")
def get_my_summary(
    month: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    summary = user_month_summary(db, current_user.id, month)
    return {
        "user_id": current_user.id,
        "month": month,
        "total_units": summary["total_units"],
        "total_amount": float(summary["total_amount"]),
    }
