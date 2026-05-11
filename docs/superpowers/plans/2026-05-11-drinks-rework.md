# Drinks Rework Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove teams/fridges from the entire stack, upgrade to the ALBdrinks design system, and rework the admin/dashboard UIs for desktop/mobile respectively.

**Architecture:** Layered Python (FastAPI + SQLAlchemy 2.0) with Jinja2 templates and vanilla JS. Changes flow from models → schemas → API → templates → JS. Design system is a full CSS replacement with Lucide icons via CDN and two brand SVG assets from the ZIP.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0 (sync), Pydantic v2, Jinja2, vanilla JS (ES2020+), Lucide 0.469.0

**Reference spec:** `docs/superpowers/specs/2026-05-11-drinks-rework-design.md`

---

### Task 1: Strip Team and Fridge from models

**Files:**
- Delete: `app/models/team.py`
- Delete: `app/models/fridge.py`
- Modify: `app/models/__init__.py`
- Modify: `app/models/drink.py`
- Modify: `app/models/user.py`
- Modify: `app/models/consumption.py`

- [ ] **Step 1: Delete the two model files**

```bash
rm app/models/team.py app/models/fridge.py
```

- [ ] **Step 2: Rewrite `app/models/__init__.py`**

```python
from app.models.billing import BillingPeriod, BillingStatus, EmailLog
from app.models.consumption import Consumption
from app.models.drink import Drink
from app.models.user import User, UserRole

__all__ = ["User", "UserRole", "Drink", "Consumption", "BillingPeriod", "BillingStatus", "EmailLog"]
```

- [ ] **Step 3: Rewrite `app/models/drink.py`**

```python
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Drink(Base):
    __tablename__ = "drinks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    photo_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    stock_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    low_stock_threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    consumptions = relationship("Consumption", back_populates="drink")
```

- [ ] **Step 4: Rewrite `app/models/user.py`**

```python
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class UserRole(StrEnum):
    USER = "USER"
    ADMIN = "ADMIN"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False, default=UserRole.USER)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_pending_approval: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    consumptions = relationship("Consumption", back_populates="user")
    billing_periods = relationship("BillingPeriod", back_populates="user")
```

- [ ] **Step 5: Rewrite `app/models/consumption.py`**

```python
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Consumption(Base):
    __tablename__ = "consumptions"
    __table_args__ = (
        UniqueConstraint("user_id", "drink_id", "consumed_at", name="uq_consumption_event"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    drink_id: Mapped[int] = mapped_column(ForeignKey("drinks.id"), nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_price_at_time: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    consumed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    user = relationship("User", back_populates="consumptions")
    drink = relationship("Drink", back_populates="consumptions")
```

- [ ] **Step 6: Run tests to verify models compile**

```bash
python -m pytest app/tests/ -x -q 2>&1 | head -40
```

Expected: tests may fail on API layer (not yet updated) but no import errors from models.

- [ ] **Step 7: Commit**

```bash
git add app/models/
git rm app/models/team.py app/models/fridge.py
git commit -m "feat: remove Team and Fridge models"
```

---

### Task 2: Strip Team and Fridge from schemas

**Files:**
- Modify: `app/schemas/drink.py`
- Modify: `app/schemas/admin.py`

- [ ] **Step 1: Rewrite `app/schemas/drink.py`**

Remove `team_id` and `fridge_id` from all schemas. Fix `DrinkUpdate` so explicitly-sent `null` clears `stock_quantity`.

```python
from decimal import Decimal

from pydantic import BaseModel


class DrinkBase(BaseModel):
    name: str
    photo_url: str
    unit_price: Decimal
    stock_quantity: int | None = None
    low_stock_threshold: int = 5
    is_active: bool = True


class DrinkCreate(DrinkBase):
    pass


class DrinkUpdate(BaseModel):
    name: str | None = None
    photo_url: str | None = None
    unit_price: Decimal | None = None
    stock_quantity: int | None = None
    low_stock_threshold: int | None = None
    is_active: bool | None = None


class DrinkOut(BaseModel):
    id: int
    name: str
    photo_url: str
    unit_price: Decimal
    stock_quantity: int | None
    low_stock_threshold: int
    is_active: bool

    model_config = {"from_attributes": True}
```

- [ ] **Step 2: Rewrite `app/schemas/admin.py`**

Remove `TeamCreate`, `TeamUpdate`, `FridgeCreate`, `FridgeUpdate`. Remove `team_id` from `UserCreate` and `UserUpdate`.

```python
from decimal import Decimal

from pydantic import BaseModel


class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    role: str = "USER"


class UserUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None
    role: str | None = None


class PasswordReset(BaseModel):
    password: str


class PasswordChange(BaseModel):
    old_password: str
    new_password: str


class MonthlyUserReport(BaseModel):
    user_id: int
    name: str
    email: str
    total_units: int
    total_amount: Decimal


class MonthlyDrinkReport(BaseModel):
    drink_id: int
    drink_name: str
    total_units: int
    total_amount: Decimal
```

- [ ] **Step 3: Commit**

```bash
git add app/schemas/
git commit -m "feat: remove team/fridge from schemas; fix DrinkUpdate null handling"
```

---

### Task 3: Rewrite admin API

**Files:**
- Modify: `app/api/admin.py`

- [ ] **Step 1: Rewrite `app/api/admin.py`**

Remove all `/teams` and `/fridges` endpoints, `ensure_team_exists()`, `ensure_fridge_exists()`. Fix `update_drink` to use `model_fields_set` for `stock_quantity`. Remove `team_id`/`fridge_id` from all dict returns and object constructors.

Full file content:

```python
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
from app.models import Drink, User, UserRole
from app.schemas.admin import PasswordReset, UserCreate, UserUpdate
from app.schemas.drink import DrinkCreate, DrinkUpdate
from app.services.billing_job import run_monthly_billing
from app.services.reporting import (
    build_csv,
    build_pdf,
    is_month_closed,
    low_stock_rows,
    monthly_drink_report_rows,
    monthly_user_report_rows,
    reset_billing_month,
)

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
            "is_pending_approval": u.is_pending_approval,
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
        is_pending_approval=False,
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
        {"id": u.id, "name": u.name, "email": u.email, "created_at": str(u.created_at)}
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
    drink = Drink(
        name=payload.name,
        photo_url=str(payload.photo_url),
        unit_price=payload.unit_price,
        stock_quantity=payload.stock_quantity,
        low_stock_threshold=payload.low_stock_threshold,
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
    if "stock_quantity" in payload.model_fields_set:
        drink.stock_quantity = payload.stock_quantity
    if payload.low_stock_threshold is not None:
        drink.low_stock_threshold = payload.low_stock_threshold
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
            "is_closed": is_month_closed(db, month),
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
    return run_monthly_billing(db, month, close_month=True)


@router.post("/reset-month")
def reset_month(
    month: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict:
    result = reset_billing_month(db, month)
    db.commit()
    return result
```

- [ ] **Step 2: Commit**

```bash
git add app/api/admin.py
git commit -m "feat: remove teams/fridges endpoints; fix stock_quantity null update"
```

---

### Task 4: Fix user API

**Files:**
- Modify: `app/api/user.py`

- [ ] **Step 1: Update `list_drinks` — remove team filter**

Replace the current `list_drinks` function body:

```python
@router.get("/drinks")
def list_drinks(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[dict]:
    drinks = db.scalars(select(Drink).where(Drink.is_active.is_(True)).order_by(Drink.name.asc())).all()
    return [
        {
            "id": d.id,
            "name": d.name,
            "photo_url": d.photo_url,
            "unit_price": float(d.unit_price),
            "stock_quantity": d.stock_quantity,
            "low_stock_threshold": d.low_stock_threshold,
            "is_active": d.is_active,
        }
        for d in drinks
    ]
```

Also remove the unused `and_` import.

- [ ] **Step 2: Fix `add_consumption` — remove team_id/fridge_id**

Replace Consumption constructor in `add_consumption`:

```python
    consumption = Consumption(
        user_id=current_user.id,
        drink_id=drink.id,
        quantity=payload.quantity,
        unit_price_at_time=drink.unit_price,
        consumed_at=datetime.utcnow(),
    )
```

- [ ] **Step 3: Fix `notify_low_stock` — remove fridge/team lines**

Replace body of `notify_low_stock`:

```python
def notify_low_stock(db: Session, drink: Drink, stock_before: int | None) -> None:
    stock_after = drink.stock_quantity
    if stock_before is None or stock_after is None:
        return
    if stock_before <= drink.low_stock_threshold or stock_after > drink.low_stock_threshold:
        return

    recipients = parse_recipients(settings.buyer_report_email)
    if not recipients:
        return

    subject = f"Low stock alert: {drink.name}"
    body = (
        f"Drink: {drink.name}\n"
        f"Current stock: {stock_after}\n"
        f"Threshold: {drink.low_stock_threshold}\n"
        f"Price: EUR {float(drink.unit_price):.2f}\n"
    )
    month = datetime.utcnow().strftime("%Y-%m")

    for recipient in recipients:
        try:
            send_email(recipient, subject, body)
            record_email_log(db, recipient, subject, month, "SENT")
        except Exception as exc:  # pragma: no cover
            record_email_log(db, recipient, subject, month, "FAILED", str(exc))
```

- [ ] **Step 4: Run all tests**

```bash
cd /home/karlo/projects/drinks4all && python -m pytest app/tests/ -x -q 2>&1 | tail -20
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add app/api/user.py
git commit -m "feat: remove team filter from drinks list; drop team/fridge from consumption"
```

---

### Task 5: Fix reporting and schema compat

**Files:**
- Modify: `app/services/reporting.py`
- Modify: `app/main.py`

- [ ] **Step 1: Fix `monthly_drink_report_rows` in `app/services/reporting.py`**

Replace the existing function with a subquery approach that correctly handles zero-consumption drinks:

```python
def monthly_drink_report_rows(db: Session, month: str) -> list[dict]:
    start, end = month_bounds(month)

    sub = (
        select(
            Consumption.drink_id,
            func.sum(Consumption.quantity).label("units"),
            func.sum(Consumption.quantity * Consumption.unit_price_at_time).label("amount"),
        )
        .where(Consumption.consumed_at >= start, Consumption.consumed_at < end)
        .group_by(Consumption.drink_id)
        .subquery()
    )

    rows = db.execute(
        select(
            Drink.id,
            Drink.name,
            func.coalesce(sub.c.units, 0).label("units"),
            func.coalesce(sub.c.amount, 0).label("amount"),
        )
        .outerjoin(sub, sub.c.drink_id == Drink.id)
        .order_by(Drink.name.asc())
    ).all()

    return [
        {
            "drink_id": int(r.id),
            "drink_name": r.name,
            "total_units": int(r.units or 0),
            "total_amount": Decimal(r.amount or 0),
        }
        for r in rows
    ]
```

- [ ] **Step 2: Update `ensure_schema_compat` in `app/main.py`**

Replace the statements list to DROP old columns/tables and keep only the ADD statements that are still needed:

```python
def ensure_schema_compat() -> None:
    statements = [
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_pending_approval BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE billing_periods ADD COLUMN IF NOT EXISTS closed_at TIMESTAMP",
        "ALTER TABLE drinks ADD COLUMN IF NOT EXISTS stock_quantity INTEGER",
        "ALTER TABLE drinks ADD COLUMN IF NOT EXISTS low_stock_threshold INTEGER NOT NULL DEFAULT 5",
        "ALTER TABLE consumptions DROP COLUMN IF EXISTS team_id",
        "ALTER TABLE consumptions DROP COLUMN IF EXISTS fridge_id",
        "ALTER TABLE drinks DROP COLUMN IF EXISTS team_id",
        "ALTER TABLE drinks DROP COLUMN IF EXISTS fridge_id",
        "ALTER TABLE users DROP COLUMN IF EXISTS team_id",
        "DROP TABLE IF EXISTS fridges CASCADE",
        "DROP TABLE IF EXISTS teams CASCADE",
    ]
    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))
```

- [ ] **Step 3: Run all tests**

```bash
cd /home/karlo/projects/drinks4all && python -m pytest app/tests/ -x -q 2>&1 | tail -20
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add app/services/reporting.py app/main.py
git commit -m "fix: rewrite monthly_drink_report_rows with subquery; drop team/fridge in schema compat"
```

---

### Task 6: Update tests

**Files:**
- Modify: `app/tests/test_admin_reporting.py`
- Modify: `app/tests/test_consumption_and_pricing.py` (if it references team_id/fridge_id)

- [ ] **Step 1: Check for team_id/fridge_id references in tests**

```bash
grep -n "team_id\|fridge_id" app/tests/*.py
```

- [ ] **Step 2: Fix any occurrences found**

For each `Consumption(... team_id=..., fridge_id=..., ...)` found, remove those kwargs.
For each `User(... team_id=..., ...)` found, remove that kwarg.

- [ ] **Step 3: Add test for stock_quantity null update in `app/tests/test_admin_reporting.py`**

```python
def test_update_drink_stock_to_unlimited(client, admin_user, db):
    login = client.post("/auth/login", json={"email": admin_user.email, "password": "admin123"})
    assert login.status_code == 200

    create = client.post(
        "/admin/drinks",
        json={"name": "Cola", "photo_url": "https://example.com/cola.jpg", "unit_price": 1.5, "stock_quantity": 10},
    )
    assert create.status_code == 200
    drink_id = create.json()["id"]

    update = client.put(f"/admin/drinks/{drink_id}", json={"stock_quantity": None})
    assert update.status_code == 200

    drinks = client.get("/admin/drinks")
    assert drinks.status_code == 200
    drink = next(d for d in drinks.json() if d["id"] == drink_id)
    assert drink["stock_quantity"] is None
```

- [ ] **Step 4: Add test that all active drinks are visible to any user**

```python
def test_all_active_drinks_visible_to_any_user(client, admin_user, normal_user, db):
    login_admin = client.post("/auth/login", json={"email": admin_user.email, "password": "admin123"})
    assert login_admin.status_code == 200

    client.post(
        "/admin/drinks",
        json={"name": "Club Mate", "photo_url": "https://example.com/club-mate.jpg", "unit_price": 1.5},
    )
    client.post(
        "/admin/drinks",
        json={"name": "Cola", "photo_url": "https://example.com/cola.jpg", "unit_price": 1.2},
    )

    login_user = client.post("/auth/login", json={"email": normal_user.email, "password": "user123"})
    assert login_user.status_code == 200

    drinks = client.get("/drinks")
    assert drinks.status_code == 200
    names = [d["name"] for d in drinks.json()]
    assert "Club Mate" in names
    assert "Cola" in names
```

- [ ] **Step 5: Run all tests**

```bash
cd /home/karlo/projects/drinks4all && python -m pytest app/tests/ -v 2>&1 | tail -30
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add app/tests/
git commit -m "test: remove team/fridge from fixtures; add stock_quantity null and visibility tests"
```

---

### Task 7: Design system CSS and brand assets

**Files:**
- Replace: `app/static/css/app.css`
- Create: `app/static/favicon.svg`
- Create: `app/static/logo-wordmark.svg`

- [ ] **Step 1: Extract brand SVG assets from ZIP**

```bash
unzip -p "ALBdrinks Design System.zip" "assets/favicon.svg" > app/static/favicon.svg
unzip -p "ALBdrinks Design System.zip" "assets/logo-wordmark.svg" > app/static/logo-wordmark.svg
```

Verify:
```bash
head -3 app/static/favicon.svg
head -3 app/static/logo-wordmark.svg
```

Expected: both start with `<svg`.

- [ ] **Step 2: Extract CSS from ZIP**

```bash
unzip -p "ALBdrinks Design System.zip" "css/app.css" > app/static/css/app.css
```

If the ZIP uses a different path, list it first:
```bash
unzip -l "ALBdrinks Design System.zip" | grep -E "\.css|\.svg"
```

- [ ] **Step 3: Verify new CSS contains required tokens**

```bash
grep -c "\-\-accent\|Inter\|--panel-subtle\|\.btn-icon\|\.drink-admin-row\|\.modal-backdrop" app/static/css/app.css
```

Expected: count > 0 for each. If the CSS lacks `.drink-admin-row` or `.modal-backdrop` or `.btn-icon`, those need to be added manually — see the design spec for exact selectors needed.

- [ ] **Step 4: Commit**

```bash
git add app/static/
git commit -m "feat: apply ALBdrinks design system CSS and brand assets"
```

---

### Task 8: Rewrite admin.html

**Files:**
- Modify: `app/templates/admin.html`

The new template introduces: favicon link, Lucide CDN, wordmark logo in topbar, two-column layout (Users | Drinks), drink create form with photo upload, drink list rows (thumbnail + name + stock pill + Edit button), drink edit modal, user edit modal (replacing prompt() calls).

- [ ] **Step 1: Read the current admin.html**

```bash
wc -l app/templates/admin.html
```

Then read it fully with the Read tool to understand current Jinja2 blocks and JS hook points.

- [ ] **Step 2: Replace `<head>` additions**

Add to `<head>`:
```html
<link rel="icon" href="/static/favicon.svg">
<script src="https://unpkg.com/lucide@0.469.0/dist/umd/lucide.min.js"></script>
```

- [ ] **Step 3: Replace topbar**

Replace `<h1>Admin Console</h1>` with:
```html
<img src="/static/logo-wordmark.svg" alt="ALBdrinks" style="height:32px;">
```

- [ ] **Step 4: Build two-column layout**

Structure:
```html
<div class="admin-grid">
  <!-- Users column -->
  <section id="users-col">
    <h2><i data-lucide="users" style="width:22px;height:22px;color:var(--accent)"></i> Users</h2>
    <div id="user-list"></div>
  </section>

  <!-- Drinks column -->
  <section id="drinks-col">
    <h2><i data-lucide="coffee" style="width:22px;height:22px;color:var(--accent)"></i> Drinks</h2>

    <!-- Create form -->
    <form id="drink-create-form">
      <div class="upload-row">
        <button type="button" id="upload-btn-create" class="btn-icon">
          <i data-lucide="image-plus" style="width:18px;height:18px"></i> Upload Photo
        </button>
        <input type="file" id="upload-input-create" accept="image/*" style="display:none">
      </div>
      <input type="text" id="create-photo-url" placeholder="Photo URL (or upload above)" class="input-full">
      <input type="text" id="create-name" placeholder="Name" class="input-full" required>
      <div class="row-2">
        <input type="number" id="create-price" placeholder="Price (EUR)" step="0.01" required>
        <input type="number" id="create-stock" placeholder="Stock (blank = unlimited)">
      </div>
      <input type="number" id="create-threshold" value="5" placeholder="Low-stock alert at">
      <button type="submit" class="btn btn-primary">
        <i data-lucide="plus" style="width:18px;height:18px"></i> Create Drink
      </button>
    </form>

    <!-- Drink list -->
    <div id="drink-list"></div>
  </section>
</div>

<!-- Drink edit modal -->
<div id="drink-modal" class="modal-backdrop" style="display:none">
  <div class="modal-panel">
    <div class="modal-hd">
      <h3>Edit Drink</h3>
      <button id="drink-modal-close" class="btn btn-secondary">
        <i data-lucide="x" style="width:18px;height:18px"></i>
      </button>
    </div>
    <div class="modal-body">
      <input type="hidden" id="edit-drink-id">
      <div class="thumb-name-row">
        <img id="edit-thumb" src="" alt="" class="modal-thumb">
        <div class="thumb-controls">
          <input type="text" id="edit-name" placeholder="Name" class="input-full">
          <button type="button" id="upload-btn-edit" class="btn btn-secondary btn-sm">
            <i data-lucide="image-plus" style="width:18px;height:18px"></i> Change Photo
          </button>
          <input type="file" id="upload-input-edit" accept="image/*" style="display:none">
        </div>
      </div>
      <input type="text" id="edit-photo-url" placeholder="Photo URL" class="input-full">
      <div class="row-2">
        <input type="number" id="edit-price" placeholder="Price (EUR)" step="0.01">
        <input type="number" id="edit-stock" placeholder="blank = unlimited">
      </div>
      <input type="number" id="edit-threshold" placeholder="Low-stock alert at">
      <label class="toggle-label">
        <input type="checkbox" id="edit-active"> Active (visible to users)
      </label>
    </div>
    <div class="modal-footer">
      <button id="drink-save-btn" class="btn btn-primary">Save</button>
      <button id="drink-cancel-btn" class="btn btn-secondary">Cancel</button>
      <button id="drink-delete-btn" class="btn btn-danger">Delete</button>
    </div>
  </div>
</div>

<!-- User edit modal -->
<div id="user-modal" class="modal-backdrop" style="display:none">
  <div class="modal-panel">
    <div class="modal-hd">
      <h3>Edit User</h3>
      <button id="user-modal-close" class="btn btn-secondary">
        <i data-lucide="x" style="width:18px;height:18px"></i>
      </button>
    </div>
    <div class="modal-body">
      <input type="hidden" id="edit-user-id">
      <input type="text" id="edit-user-name" placeholder="Name" class="input-full">
      <select id="edit-user-role" class="input-full">
        <option value="USER">User</option>
        <option value="ADMIN">Admin</option>
      </select>
      <label class="toggle-label">
        <input type="checkbox" id="edit-user-active"> Active
      </label>
    </div>
    <div class="modal-footer">
      <button id="user-save-btn" class="btn btn-primary">Save</button>
      <button id="user-cancel-btn" class="btn btn-secondary">Cancel</button>
      <button id="user-reset-pw-btn" class="btn btn-secondary">Reset Password</button>
      <button id="user-delete-btn" class="btn btn-danger">Delete</button>
    </div>
  </div>
</div>
```

- [ ] **Step 5: Add `lucide.createIcons()` call at end of page JS block**

At the bottom of `<script>` in admin.html, after all JS is loaded:
```js
lucide.createIcons();
```

- [ ] **Step 6: Commit**

```bash
git add app/templates/admin.html
git commit -m "feat: admin two-col layout with Lucide icons, drink/user edit modals"
```

---

### Task 9: Rewrite admin.js

**Files:**
- Modify: `app/static/js/admin.js`

- [ ] **Step 1: Read the current admin.js**

```bash
wc -l app/static/js/admin.js
```

Then read it fully to understand existing patterns for auth headers, fetch calls, etc.

- [ ] **Step 2: Write new admin.js**

Key functions to implement:

**`renderDrinks(drinks)`** — builds drink-list rows:
- Each row: 48×48 thumbnail (or placeholder icon div if `photo_url` is empty), name, price, stock pill (ok/low/inf class), Edit button
- Inactive drinks get `opacity:0.55` on the row
- Stock pill: green "N left" if above threshold, amber "⚠ N left" if at/below, grey "unlimited" if null

**`openDrinkModal(drink)`** — populates and shows `#drink-modal`:
- Sets `#edit-drink-id`, `#edit-name`, `#edit-photo-url`, `#edit-price`, `#edit-stock`, `#edit-threshold`, `#edit-active`, `#edit-thumb src`
- `#edit-stock` value: `drink.stock_quantity ?? ""` (empty = unlimited)

**`saveDrink()`** — reads modal fields, calls `PUT /admin/drinks/{id}`:
- `stock_quantity`: parse int if non-empty string, else `null`
- On success: close modal, reload drinks

**`deleteDrink(id)`** — calls `DELETE /admin/drinks/{id}` after `confirm()`

**`uploadPhoto(inputEl, urlEl, thumbEl)`** — handles image upload:
- POST to `/admin/drinks/upload-image` with FormData
- On success: set `urlEl.value` and `thumbEl.src` to returned `photo_url`

**`renderUsers(users)`** — builds user-list rows with Edit button (replaces old prompt-based code)

**`openUserModal(user)`** — populates and shows `#user-modal`

**`saveUser()`** — calls `PUT /admin/users/{id}`

**`resetPassword(userId)`** — prompts for new password, calls `POST /admin/users/{userId}/reset-password`

Wire up after DOM ready:
- `document.addEventListener("DOMContentLoaded", init)`
- `init()` calls `loadDrinks()`, `loadUsers()`, sets up modal close on backdrop click, upload button click handlers
- `#drink-create-form` submit handler: POST to `/admin/drinks`, reload
- `#drink-save-btn` click: `saveDrink()`
- `#drink-delete-btn` click: `deleteDrink(currentDrinkId)`
- `#upload-btn-create` click: `#upload-input-create.click()`
- `#upload-input-create` change: `uploadPhoto(inputEl, #create-photo-url, null)`
- `#upload-btn-edit` click: `#upload-input-edit.click()`
- `#upload-input-edit` change: `uploadPhoto(inputEl, #edit-photo-url, #edit-thumb)`
- Close modals on backdrop click (check `event.target === backdropEl`)
- Call `lucide.createIcons()` after rendering each list

- [ ] **Step 3: Commit**

```bash
git add app/static/js/admin.js
git commit -m "feat: rewrite admin.js with thumbnail rows, drink/user modals, no prompts"
```

---

### Task 10: Update dashboard.html and dashboard.js

**Files:**
- Modify: `app/templates/dashboard.html`
- Modify: `app/static/js/dashboard.js`

- [ ] **Step 1: Update `<head>` in dashboard.html**

Add favicon and Lucide (user-facing surfaces use minimal icons):
```html
<link rel="icon" href="/static/favicon.svg">
```

- [ ] **Step 2: Replace topbar in dashboard.html**

New topbar HTML:
```html
<div class="topbar">
  <div class="topbar-left">
    <img src="/static/logo-wordmark.svg" alt="ALBdrinks" style="height:26px;">
    <span id="topbar-username" class="topbar-name"></span>
    <span id="topbar-month" class="topbar-month"></span>
  </div>
  <div class="topbar-right">
    <button id="undo-btn" class="btn btn-secondary btn-sm">Undo</button>
    <div class="overflow-wrap">
      <button id="overflow-btn" class="btn btn-secondary btn-sm">&#8943;</button>
      <div id="overflow-menu" class="overflow-menu" style="display:none">
        <div class="overflow-item">
          <label for="month-picker">Month</label>
          <input type="month" id="month-picker">
        </div>
        <button id="change-password-btn" class="overflow-item overflow-item-btn">Change Password</button>
        <button id="logout-btn" class="overflow-item overflow-item-btn overflow-item-danger">Logout</button>
      </div>
    </div>
  </div>
</div>
```

- [ ] **Step 3: Update drink-grid CSS class in dashboard.html**

Change the drink grid container to use a `minmax(150px, 1fr)` grid (set via class or inline style). Each card needs:
```html
<div class="drink-card" data-id="...">
  <div class="drink-photo"><img src="..." alt="..."></div>
  <div class="drink-body">
    <div class="drink-name">...</div>
    <div class="drink-price">EUR ...</div>
    <button class="btn btn-primary btn-full btn-touch">+1 Drink</button>
    <div class="drink-stock"></div>
  </div>
</div>
```

These cards are rendered by JS, not static HTML — update the JS template (Step 5).

- [ ] **Step 4: Update confirm modal in dashboard.html**

Ensure confirm modal buttons have `min-height: 48px` (CSS handles this, but verify the HTML structure uses the right classes).

- [ ] **Step 5: Update `dashboard.js` — card template and overflow menu**

In `renderDrinks(drinks)`, update the card template string to match the new structure above. Stock display below the button: show amber `⚠ N left` when `stock_quantity <= low_stock_threshold`, otherwise hide.

Add overflow menu toggle:
```js
document.getElementById("overflow-btn").addEventListener("click", (e) => {
    e.stopPropagation();
    const menu = document.getElementById("overflow-menu");
    menu.style.display = menu.style.display === "none" ? "block" : "none";
});
document.addEventListener("click", () => {
    document.getElementById("overflow-menu").style.display = "none";
});
```

Move change-password and logout button wiring to use `#change-password-btn` and `#logout-btn` inside the overflow menu.

- [ ] **Step 6: Commit**

```bash
git add app/templates/dashboard.html app/static/js/dashboard.js
git commit -m "feat: mobile dashboard topbar with overflow menu, 2-col drink grid"
```

---

### Task 11: Update login.html and smoke test

**Files:**
- Modify: `app/templates/login.html`

- [ ] **Step 1: Add favicon to login.html `<head>`**

```html
<link rel="icon" href="/static/favicon.svg">
```

- [ ] **Step 2: Run full test suite**

```bash
cd /home/karlo/projects/drinks4all && python -m pytest app/tests/ -v 2>&1 | tail -40
```

Expected: all tests pass.

- [ ] **Step 3: Start the dev stack and verify pages load**

```bash
cd /home/karlo/projects/drinks4all && docker compose up -d
```

Then visit http://localhost:8000 (login), http://localhost:8000/admin (admin console), http://localhost:8000/dashboard (user dashboard) and verify:
- Login page shows favicon
- Admin console shows two-column layout, Lucide icons, wordmark logo, drink thumbnails, edit modals
- Dashboard shows overflow menu, two-column drink grid, mobile-friendly cards
- No JavaScript console errors

- [ ] **Step 4: Final commit**

```bash
git add app/templates/login.html
git commit -m "feat: add favicon to login page; complete ALBdrinks rework"
```

