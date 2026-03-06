from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.settings import settings
from app.models import BillingStatus
from app.services.emailer import send_email
from app.services.reporting import (
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

    sent_users = 0
    failed_users = 0

    for row in rows:
        amount = Decimal(row["total_amount"])
        period = upsert_billing_period(db, row["user_id"], target_month, amount)

        subject = f"Drinks statement for {target_month}"
        body = (
            f"Hello {row['name']},\n\n"
            f"Your drinks summary for {target_month}:\n"
            f"Units: {row['total_units']}\n"
            f"Total: {amount:.2f}\n\n"
            "Please settle payment with your admin."
        )
        try:
            send_email(row["email"], subject, body)
            record_email_log(db, row["email"], subject, target_month, "SENT")
            period.status = BillingStatus.SENT
            sent_users += 1
        except Exception as exc:  # pragma: no cover
            record_email_log(db, row["email"], subject, target_month, "FAILED", str(exc))
            failed_users += 1

    admin_subject = f"Monthly drinks overview {target_month}"
    admin_lines = [f"{r['name']} ({r['email']}): {Decimal(r['total_amount']):.2f}" for r in rows]
    admin_body = "Monthly totals:\n" + "\n".join(admin_lines)
    try:
        send_email(settings.admin_report_email, admin_subject, admin_body)
        record_email_log(db, settings.admin_report_email, admin_subject, target_month, "SENT")
    except Exception as exc:  # pragma: no cover
        record_email_log(db, settings.admin_report_email, admin_subject, target_month, "FAILED", str(exc))

    db.commit()
    return {"month": target_month, "users_count": len(rows), "sent_users": sent_users, "failed_users": failed_users}
