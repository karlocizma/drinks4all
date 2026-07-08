from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.settings import settings
from app.models import BillingStatus
from app.services.emailer import parse_recipients, render_email, send_email
from app.services.reporting import (
    close_billing_month,
    low_stock_rows,
    monthly_user_report_rows,
    record_email_log,
    upsert_billing_period,
)


def _user_statement_html(
    name: str,
    month: str,
    total_units: int,
    total_amount: Decimal,
    drinks: list[dict],
    paypal_url: str | None,
) -> str:
    return render_email(
        "emails/user_statement.html",
        name=name,
        month=month,
        total_units=total_units,
        total_amount=f"{total_amount:.2f}",
        drinks=[
            {
                "drink_name": d["drink_name"],
                "total_units": d["total_units"],
                "total_amount": f"{Decimal(d['total_amount']):.2f}",
            }
            for d in drinks
        ],
        paypal_url=paypal_url,
        payment_email=settings.payment_email,
    )


def _buyer_overview_html(month: str, rows: list[dict], low_stock: list[dict]) -> str:
    total = sum(Decimal(r["total_amount"]) for r in rows)
    return render_email(
        "emails/buyer_overview.html",
        month=month,
        rows=[
            {
                "name": r["name"],
                "email": r["email"],
                "total_units": r["total_units"],
                "total_amount": f"{Decimal(r['total_amount']):.2f}",
            }
            for r in rows
        ],
        total_amount=f"{total:.2f}",
        low_stock=low_stock,
    )


def previous_month(today: date | None = None) -> str:
    d = today or date.today()
    if d.month == 1:
        return f"{d.year - 1}-12"
    return f"{d.year}-{d.month - 1:02d}"


def run_monthly_billing(db: Session, month: str | None = None, close_month: bool = False) -> dict:
    target_month = month or previous_month()
    rows = monthly_user_report_rows(db, target_month)
    low_stock = low_stock_rows(db)

    sent_users = 0
    failed_users = 0

    for row in rows:
        amount = Decimal(row["total_amount"])
        period = upsert_billing_period(db, row["user_id"], target_month, amount)

        paypal_url = None
        if settings.paypal_me_url and amount > 0:
            paypal_url = f"{settings.paypal_me_url.rstrip('/')}/{amount:.2f}"

        subject = f"Drinks statement for {target_month}"
        drink_lines = "\n".join(
            f"- {d['drink_name']}: {d['total_units']} units (€{Decimal(d['total_amount']):.2f})"
            for d in row["drinks"]
        ) or "- No drinks consumed"
        payment_line = f"Please send payment to: {settings.payment_email}\n\n" if settings.payment_email else ""
        body = (
            f"Hello {row['name']},\n\n"
            f"Your drinks summary for {target_month}:\n"
            f"Total units: {row['total_units']}\n"
            f"Total to pay: €{amount:.2f}\n\n"
            f"{payment_line}"
            f"Breakdown:\n{drink_lines}\n"
        )
        html = _user_statement_html(
            name=row["name"],
            month=target_month,
            total_units=row["total_units"],
            total_amount=amount,
            drinks=row["drinks"],
            paypal_url=paypal_url,
        )

        try:
            send_email(row["email"], subject, body, html=html)
            record_email_log(db, row["email"], subject, target_month, "SENT")
            period.status = BillingStatus.SENT
            sent_users += 1
        except Exception as exc:  # pragma: no cover
            record_email_log(db, row["email"], subject, target_month, "FAILED", str(exc))
            failed_users += 1

    buyer_subject = f"Monthly drinks overview {target_month}"
    buyer_lines = [
        f"{r['name']} ({r['email']}): total=€{Decimal(r['total_amount']):.2f} | units={r['total_units']}"
        for r in rows
    ]
    stock_lines = [
        f"{s['drink_name']}: stock={s['stock_quantity']} threshold={s['low_stock_threshold']}" for s in low_stock
    ]
    buyer_body = (
        "Per-user totals:\n"
        + ("\n".join(buyer_lines) if buyer_lines else "No user activity")
        + "\n\nLow stock alerts:\n"
        + ("\n".join(stock_lines) if stock_lines else "No low stock alerts")
    )
    buyer_html = _buyer_overview_html(target_month, rows, low_stock)
    for recipient in parse_recipients(settings.buyer_report_email):
        try:
            send_email(recipient, buyer_subject, buyer_body, html=buyer_html)
            record_email_log(db, recipient, buyer_subject, target_month, "SENT")
        except Exception as exc:  # pragma: no cover
            record_email_log(db, recipient, buyer_subject, target_month, "FAILED", str(exc))

    closed_periods = 0
    if close_month:
        db.flush()
        closed_periods = close_billing_month(db, target_month, rows)

    db.commit()
    return {
        "month": target_month,
        "users_count": len(rows),
        "sent_users": sent_users,
        "failed_users": failed_users,
        "low_stock_count": len(low_stock),
        "closed_periods": closed_periods,
        "month_closed": close_month,
    }
