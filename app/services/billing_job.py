from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.settings import settings
from app.models import BillingStatus
from app.services.emailer import send_email
from app.services.reporting import (
    low_stock_rows,
    monthly_user_report_rows,
    record_email_log,
    upsert_billing_period,
)


def previous_month(today: date | None = None) -> str:
    d = today or date.today()
    if d.month == 1:
        return f"{d.year - 1}-12"
    return f"{d.year}-{d.month - 1:02d}"


def run_monthly_billing(db: Session, month: str | None = None) -> dict:
    target_month = month or previous_month()
    rows = monthly_user_report_rows(db, target_month)
    low_stock = low_stock_rows(db)

    sent_users = 0
    failed_users = 0

    for row in rows:
        amount = Decimal(row["total_amount"])
        period = upsert_billing_period(db, row["user_id"], target_month, amount)

        subject = f"Drinks statement for {target_month}"
        drink_lines = "\n".join(
            [
                f"- {d['drink_name']}: {d['total_units']} units (€{Decimal(d['total_amount']):.2f})"
                for d in row["drinks"]
            ]
        ) or "- No drinks consumed"
        body = (
            f"Hello {row['name']},\n\n"
            f"Your drinks summary for {target_month}:\n"
            f"Total units: {row['total_units']}\n"
            f"Total to pay: €{amount:.2f}\n\n"
            f"Breakdown:\n{drink_lines}\n"
        )

        try:
            send_email(row["email"], subject, body)
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
    try:
        send_email(settings.buyer_report_email, buyer_subject, buyer_body)
        record_email_log(db, settings.buyer_report_email, buyer_subject, target_month, "SENT")
    except Exception as exc:  # pragma: no cover
        record_email_log(db, settings.buyer_report_email, buyer_subject, target_month, "FAILED", str(exc))

    db.commit()
    return {
        "month": target_month,
        "users_count": len(rows),
        "sent_users": sent_users,
        "failed_users": failed_users,
        "low_stock_count": len(low_stock),
    }
