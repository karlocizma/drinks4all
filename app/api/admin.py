from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.security import get_password_hash
from app.core.settings import settings
from app.db.database import get_db
from app.models import Drink, Fridge, Team, User, UserRole
from app.schemas.admin import (
    FridgeCreate,
    FridgeUpdate,
    PasswordReset,
    TeamCreate,
    TeamUpdate,
    UserCreate,
    UserUpdate,
)
from app.schemas.drink import DrinkCreate, DrinkUpdate
from app.services.billing_job import run_monthly_billing
from app.services.reporting import (
    build_csv,
    build_pdf,
    low_stock_rows,
    monthly_drink_report_rows,
    monthly_user_report_rows,
)

router = APIRouter(prefix="/admin", tags=["admin"])


def ensure_team_exists(db: Session, team_id: int | None) -> None:
    if team_id is None:
        return
    if db.scalar(select(Team).where(Team.id == team_id)) is None:
        raise HTTPException(status_code=404, detail="Team not found")


def ensure_fridge_exists(db: Session, fridge_id: int | None) -> None:
    if fridge_id is None:
        return
    if db.scalar(select(Fridge).where(Fridge.id == fridge_id)) is None:
        raise HTTPException(status_code=404, detail="Fridge not found")


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
            "is_pending_approval": u.is_pending_approval,
            "team_id": u.team_id,
        }
        for u in users
    ]


@router.post("/users")
def create_user(payload: UserCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)) -> dict:
    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing:
        raise HTTPException(status_code=409, detail="Email already exists")

    ensure_team_exists(db, payload.team_id)

    role = UserRole.ADMIN if payload.role.upper() == UserRole.ADMIN.value else UserRole.USER
    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=get_password_hash(payload.password),
        role=role,
        is_active=True,
        is_pending_approval=False,
        team_id=payload.team_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "email": user.email, "role": user.role.value}


@router.get("/users/pending")
def list_pending_users(db: Session = Depends(get_db), _: User = Depends(require_admin)) -> list[dict]:
    users = db.scalars(
        select(User).where(User.is_pending_approval.is_(True)).order_by(User.created_at.asc())
    ).all()
    return [
        {"id": u.id, "name": u.name, "email": u.email, "team_id": u.team_id, "created_at": str(u.created_at)}
        for u in users
    ]


@router.post("/users/{user_id}/approve")
def approve_user(user_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)) -> dict:
    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = True
    user.is_pending_approval = False
    db.commit()
    return {"ok": True}


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
        if payload.is_active:
            user.is_pending_approval = False
    if payload.role is not None:
        user.role = UserRole.ADMIN if payload.role.upper() == UserRole.ADMIN.value else UserRole.USER
    if payload.team_id is not None:
        ensure_team_exists(db, payload.team_id)
        user.team_id = payload.team_id

    db.commit()
    return {"ok": True}


@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)) -> dict:
    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Cannot delete user with linked consumption records")
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


@router.get("/teams")
def list_teams(db: Session = Depends(get_db), _: User = Depends(require_admin)) -> list[dict]:
    teams = db.scalars(select(Team).order_by(Team.name.asc())).all()
    return [{"id": t.id, "name": t.name} for t in teams]


@router.post("/teams")
def create_team(payload: TeamCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)) -> dict:
    existing = db.scalar(select(Team).where(Team.name == payload.name))
    if existing:
        raise HTTPException(status_code=409, detail="Team already exists")
    team = Team(name=payload.name)
    db.add(team)
    db.commit()
    db.refresh(team)
    return {"id": team.id, "name": team.name}


@router.put("/teams/{team_id}")
def update_team(team_id: int, payload: TeamUpdate, db: Session = Depends(get_db), _: User = Depends(require_admin)) -> dict:
    team = db.scalar(select(Team).where(Team.id == team_id))
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    team.name = payload.name
    db.commit()
    return {"ok": True}


@router.delete("/teams/{team_id}")
def delete_team(team_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)) -> dict:
    team = db.scalar(select(Team).where(Team.id == team_id))
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    db.delete(team)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Cannot delete team with linked users/fridges/drinks")
    return {"ok": True}


@router.get("/fridges")
def list_fridges(db: Session = Depends(get_db), _: User = Depends(require_admin)) -> list[dict]:
    fridges = db.scalars(select(Fridge).order_by(Fridge.name.asc())).all()
    return [
        {"id": f.id, "name": f.name, "location": f.location, "team_id": f.team_id}
        for f in fridges
    ]


@router.post("/fridges")
def create_fridge(payload: FridgeCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)) -> dict:
    ensure_team_exists(db, payload.team_id)
    fridge = Fridge(name=payload.name, location=payload.location, team_id=payload.team_id)
    db.add(fridge)
    db.commit()
    db.refresh(fridge)
    return {"id": fridge.id, "name": fridge.name}


@router.put("/fridges/{fridge_id}")
def update_fridge(
    fridge_id: int,
    payload: FridgeUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict:
    fridge = db.scalar(select(Fridge).where(Fridge.id == fridge_id))
    if not fridge:
        raise HTTPException(status_code=404, detail="Fridge not found")
    ensure_team_exists(db, payload.team_id)
    fridge.name = payload.name
    fridge.location = payload.location
    fridge.team_id = payload.team_id
    db.commit()
    return {"ok": True}


@router.delete("/fridges/{fridge_id}")
def delete_fridge(fridge_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)) -> dict:
    fridge = db.scalar(select(Fridge).where(Fridge.id == fridge_id))
    if not fridge:
        raise HTTPException(status_code=404, detail="Fridge not found")
    db.delete(fridge)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Cannot delete fridge with linked drinks/consumptions")
    return {"ok": True}


@router.get("/drinks")
def list_all_drinks(db: Session = Depends(get_db), _: User = Depends(require_admin)) -> list[dict]:
    drinks = db.scalars(select(Drink).order_by(Drink.name.asc())).all()
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


@router.post("/drinks/upload-image")
async def upload_drink_image(
    file: UploadFile = File(...),
    _: User = Depends(require_admin),
) -> dict:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    data = await file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(data) > max_bytes:
        raise HTTPException(status_code=400, detail=f"Image too large (max {settings.max_upload_mb}MB)")

    ext = Path(file.filename or "upload.jpg").suffix or ".jpg"
    safe_name = f"drink-{uuid4().hex}{ext}"
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    target = upload_dir / safe_name
    target.write_bytes(data)

    return {"photo_url": f"/static/uploads/{safe_name}"}


@router.post("/drinks")
def create_drink(payload: DrinkCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)) -> dict:
    ensure_team_exists(db, payload.team_id)
    ensure_fridge_exists(db, payload.fridge_id)

    drink = Drink(
        name=payload.name,
        photo_url=str(payload.photo_url),
        unit_price=payload.unit_price,
        stock_quantity=payload.stock_quantity,
        low_stock_threshold=payload.low_stock_threshold,
        team_id=payload.team_id,
        fridge_id=payload.fridge_id,
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
    if payload.stock_quantity is not None:
        drink.stock_quantity = payload.stock_quantity
    if payload.low_stock_threshold is not None:
        drink.low_stock_threshold = payload.low_stock_threshold
    if payload.team_id is not None:
        ensure_team_exists(db, payload.team_id)
        drink.team_id = payload.team_id
    if payload.fridge_id is not None:
        ensure_fridge_exists(db, payload.fridge_id)
        drink.fridge_id = payload.fridge_id
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
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Cannot delete drink with linked consumption records")
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
    stock_rows = low_stock_rows(db)
    total = sum(Decimal(row["total_amount"]) for row in user_rows)

    if format == "json":
        return {
            "currency": "EUR",
            "month": month,
            "users": [
                {
                    **row,
                    "total_amount": float(row["total_amount"]),
                    "drinks": [{**d, "total_amount": float(d["total_amount"])} for d in row["drinks"]],
                }
                for row in user_rows
            ],
            "drinks": [{**row, "total_amount": float(row["total_amount"])} for row in drink_rows],
            "low_stock": stock_rows,
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
