from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from io import StringIO

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import BillingPeriod, BillingStatus, Consumption, Drink, EmailLog, User, UserRole


def month_bounds(month: str) -> tuple[datetime, datetime]:
    start = datetime.strptime(month + "-01", "%Y-%m-%d")
    if start.month == 12:
        end = datetime(start.year + 1, 1, 1)
    else:
        end = datetime(start.year, start.month + 1, 1)
    return start, end


def user_month_summary(db: Session, user_id: int, month: str) -> dict:
    start, end = month_bounds(month)
    row = db.execute(
        select(
            func.coalesce(func.sum(Consumption.quantity), 0).label("units"),
            func.coalesce(func.sum(Consumption.quantity * Consumption.unit_price_at_time), 0).label("amount"),
        ).where(
            Consumption.user_id == user_id,
            Consumption.consumed_at >= start,
            Consumption.consumed_at < end,
        )
    ).one()

    breakdown_rows = db.execute(
        select(
            Drink.id,
            Drink.name,
            func.coalesce(func.sum(Consumption.quantity), 0).label("units"),
            func.coalesce(func.sum(Consumption.quantity * Consumption.unit_price_at_time), 0).label("amount"),
        )
        .join(Drink, Drink.id == Consumption.drink_id)
        .where(
            Consumption.user_id == user_id,
            Consumption.consumed_at >= start,
            Consumption.consumed_at < end,
        )
        .group_by(Drink.id, Drink.name)
        .order_by(Drink.name.asc())
    ).all()

    return {
        "total_units": int(row.units or 0),
        "total_amount": Decimal(row.amount or 0),
        "drinks": [
            {
                "drink_id": int(r.id),
                "drink_name": r.name,
                "total_units": int(r.units or 0),
                "total_amount": Decimal(r.amount or 0),
            }
            for r in breakdown_rows
        ],
    }


def monthly_user_report_rows(db: Session, month: str) -> list[dict]:
    start, end = month_bounds(month)
    users = db.scalars(select(User).where(User.role == UserRole.USER).order_by(User.name.asc())).all()

    rows: list[dict] = []
    for user in users:
        summary = user_month_summary(db, user.id, month)
        rows.append(
            {
                "user_id": user.id,
                "name": user.name,
                "email": user.email,
                "total_units": summary["total_units"],
                "total_amount": summary["total_amount"],
                "drinks": summary["drinks"],
            }
        )
    return rows


def monthly_drink_report_rows(db: Session, month: str) -> list[dict]:
    start, end = month_bounds(month)
    rows = db.execute(
        select(
            Drink.id,
            Drink.name,
            func.coalesce(func.sum(Consumption.quantity), 0).label("units"),
            func.coalesce(func.sum(Consumption.quantity * Consumption.unit_price_at_time), 0).label("amount"),
        )
        .join(Consumption, Consumption.drink_id == Drink.id, isouter=True)
        .where((Consumption.consumed_at >= start) | (Consumption.id.is_(None)))
        .where((Consumption.consumed_at < end) | (Consumption.id.is_(None)))
        .group_by(Drink.id, Drink.name)
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


def low_stock_rows(db: Session) -> list[dict]:
    drinks = db.scalars(
        select(Drink)
        .where(Drink.stock_quantity.is_not(None), Drink.stock_quantity <= Drink.low_stock_threshold)
        .order_by(Drink.stock_quantity.asc(), Drink.name.asc())
    ).all()
    return [
        {
            "drink_id": d.id,
            "drink_name": d.name,
            "stock_quantity": d.stock_quantity,
            "low_stock_threshold": d.low_stock_threshold,
        }
        for d in drinks
    ]


def build_csv(rows: list[dict]) -> str:
    output = StringIO()
    output.write("user_id,name,email,total_units,total_amount_eur,drink_name,drink_units,drink_amount_eur\n")
    for row in rows:
        if not row["drinks"]:
            output.write(
                f"{row['user_id']},{row['name']},{row['email']},{row['total_units']},{row['total_amount']:.2f},,,\n"
            )
            continue
        for drink in row["drinks"]:
            output.write(
                f"{row['user_id']},{row['name']},{row['email']},{row['total_units']},{row['total_amount']:.2f},"
                f"{drink['drink_name']},{drink['total_units']},{Decimal(drink['total_amount']):.2f}\n"
            )
    return output.getvalue()


def build_pdf(rows: list[dict], month: str) -> bytes:
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 10, f"Monthly Drinks Report {month}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    for row in rows:
        pdf.set_font("Helvetica", style="B", size=11)
        pdf.multi_cell(0, 8, f"{row['name']} ({row['email']}) - total €{Decimal(row['total_amount']):.2f}")
        pdf.set_font("Helvetica", size=10)
        for drink in row["drinks"]:
            pdf.multi_cell(
                0,
                7,
                f"  - {drink['drink_name']}: {drink['total_units']} x (€{Decimal(drink['total_amount']):.2f})",
            )
        pdf.ln(1)

    data = pdf.output(dest="S")
    if isinstance(data, bytearray):
        return bytes(data)
    if isinstance(data, str):
        return data.encode("latin-1")
    return data


def upsert_billing_period(db: Session, user_id: int, month: str, total_amount: Decimal) -> BillingPeriod:
    period = db.scalar(select(BillingPeriod).where(BillingPeriod.user_id == user_id, BillingPeriod.month == month))
    if period is None:
        period = BillingPeriod(user_id=user_id, month=month, total_amount=total_amount, status=BillingStatus.OPEN)
        db.add(period)
    else:
        period.total_amount = total_amount
    return period


def record_email_log(db: Session, recipient: str, subject: str, month: str, status: str, error: str | None = None) -> None:
    db.add(EmailLog(recipient=recipient, subject=subject, month=month, status=status, error=error))
