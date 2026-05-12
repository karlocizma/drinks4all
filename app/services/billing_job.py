from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.settings import settings
from app.models import BillingStatus
from app.services.emailer import parse_recipients, send_email
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
    rows = "".join(
        f'<tr>'
        f'<td style="padding:9px 0;border-bottom:1px solid #f1f5f9;color:#0f172a;font-size:14px;">{d["drink_name"]}</td>'
        f'<td style="padding:9px 0;border-bottom:1px solid #f1f5f9;color:#64748b;font-size:14px;text-align:center;">{d["total_units"]}</td>'
        f'<td style="padding:9px 0;border-bottom:1px solid #f1f5f9;color:#0f172a;font-size:14px;font-weight:600;text-align:right;">&#x20AC;{Decimal(d["total_amount"]):.2f}</td>'
        f'</tr>'
        for d in drinks
    ) if drinks else '<tr><td colspan="3" style="padding:16px 0;color:#64748b;font-size:14px;">No drinks this month.</td></tr>'

    paypal_btn = (
        f'<p style="text-align:center;margin:24px 0 0;">'
        f'<a href="{paypal_url}" style="display:inline-block;background:#009cde;color:#ffffff;'
        f'font-size:15px;font-weight:700;text-decoration:none;padding:13px 32px;border-radius:8px;">'
        f'Pay &#x20AC;{total_amount:.2f} with PayPal</a></p>'
    ) if paypal_url else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:'Segoe UI',Arial,sans-serif;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" bgcolor="#f1f5f9">
<tr><td align="center" style="padding:32px 16px;">
<table role="presentation" width="100%" style="max-width:560px;" cellpadding="0" cellspacing="0">

  <tr><td bgcolor="#0f172a" style="border-radius:12px 12px 0 0;padding:28px 32px;">
    <div style="color:#22d3ee;font-size:22px;font-weight:700;letter-spacing:-0.5px;">ALBdrinks</div>
    <div style="color:#94a3b8;font-size:13px;margin-top:4px;">Monthly Statement &middot; {month}</div>
  </td></tr>

  <tr><td bgcolor="#ffffff" style="padding:28px 32px;">
    <p style="margin:0 0 6px;font-size:16px;color:#0f172a;">Hello {name},</p>
    <p style="margin:0 0 24px;font-size:14px;color:#64748b;">Here is your drinks summary for <strong style="color:#0f172a;">{month}</strong>.</p>

    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:28px;">
    <tr>
      <td style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:18px;text-align:center;">
        <div style="color:#64748b;font-size:11px;text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px;">Total Drinks</div>
        <div style="color:#0f172a;font-size:30px;font-weight:700;">{total_units}</div>
      </td>
      <td width="12">&nbsp;</td>
      <td style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:18px;text-align:center;">
        <div style="color:#64748b;font-size:11px;text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px;">Total Amount</div>
        <div style="color:#0369a1;font-size:30px;font-weight:700;">&#x20AC;{total_amount:.2f}</div>
      </td>
    </tr>
    </table>

    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;margin-bottom:24px;">
    <tr>
      <th style="padding:8px 0;border-bottom:2px solid #e2e8f0;color:#64748b;font-size:11px;text-transform:uppercase;letter-spacing:.06em;font-weight:600;text-align:left;">Drink</th>
      <th style="padding:8px 0;border-bottom:2px solid #e2e8f0;color:#64748b;font-size:11px;text-transform:uppercase;letter-spacing:.06em;font-weight:600;text-align:center;">Units</th>
      <th style="padding:8px 0;border-bottom:2px solid #e2e8f0;color:#64748b;font-size:11px;text-transform:uppercase;letter-spacing:.06em;font-weight:600;text-align:right;">Amount</th>
    </tr>
    {rows}
    </table>
    {paypal_btn}
  </td></tr>

  <tr><td style="background:#f8fafc;border-top:1px solid #e2e8f0;border-radius:0 0 12px 12px;padding:18px 32px;">
    <p style="margin:0;font-size:12px;color:#94a3b8;">ALBdrinks &middot; Internal office drinks tracker</p>
  </td></tr>

</table>
</td></tr>
</table>
</body></html>"""


def _buyer_overview_html(month: str, rows: list[dict], low_stock: list[dict]) -> str:
    user_rows = "".join(
        f'<tr>'
        f'<td style="padding:9px 12px;border-bottom:1px solid #f1f5f9;color:#0f172a;font-size:14px;">{r["name"]}</td>'
        f'<td style="padding:9px 12px;border-bottom:1px solid #f1f5f9;color:#64748b;font-size:14px;">{r["email"]}</td>'
        f'<td style="padding:9px 12px;border-bottom:1px solid #f1f5f9;color:#64748b;font-size:14px;text-align:center;">{r["total_units"]}</td>'
        f'<td style="padding:9px 12px;border-bottom:1px solid #f1f5f9;color:#0f172a;font-size:14px;font-weight:600;text-align:right;">&#x20AC;{Decimal(r["total_amount"]):.2f}</td>'
        f'</tr>'
        for r in rows
    ) if rows else '<tr><td colspan="4" style="padding:16px 12px;color:#64748b;font-size:14px;">No user activity this month.</td></tr>'

    total = sum(Decimal(r["total_amount"]) for r in rows)

    stock_section = ""
    if low_stock:
        stock_rows = "".join(
            f'<tr>'
            f'<td style="padding:9px 12px;border-bottom:1px solid #f1f5f9;color:#0f172a;font-size:14px;">{s["drink_name"]}</td>'
            f'<td style="padding:9px 12px;border-bottom:1px solid #f1f5f9;text-align:center;">'
            f'<span style="background:#fff7ed;color:#c2410c;border:1px solid #fed7aa;border-radius:4px;padding:2px 8px;font-size:12px;font-weight:600;">'
            f'{s["stock_quantity"]} left</span></td>'
            f'<td style="padding:9px 12px;border-bottom:1px solid #f1f5f9;color:#64748b;font-size:13px;text-align:right;">threshold: {s["low_stock_threshold"]}</td>'
            f'</tr>'
            for s in low_stock
        )
        stock_section = (
            '<h3 style="margin:28px 0 12px;font-size:13px;font-weight:600;color:#0f172a;text-transform:uppercase;letter-spacing:.05em;">'
            '&#9888; Low Stock Alerts</h3>'
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">'
            '<tr>'
            '<th style="padding:8px 12px;border-bottom:2px solid #e2e8f0;color:#64748b;font-size:11px;text-transform:uppercase;letter-spacing:.06em;font-weight:600;text-align:left;">Drink</th>'
            '<th style="padding:8px 12px;border-bottom:2px solid #e2e8f0;color:#64748b;font-size:11px;text-transform:uppercase;letter-spacing:.06em;font-weight:600;text-align:center;">Stock</th>'
            '<th style="padding:8px 12px;border-bottom:2px solid #e2e8f0;color:#64748b;font-size:11px;text-transform:uppercase;letter-spacing:.06em;font-weight:600;text-align:right;">Threshold</th>'
            '</tr>'
            + stock_rows
            + '</table>'
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:'Segoe UI',Arial,sans-serif;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" bgcolor="#f1f5f9">
<tr><td align="center" style="padding:32px 16px;">
<table role="presentation" width="100%" style="max-width:640px;" cellpadding="0" cellspacing="0">

  <tr><td bgcolor="#0f172a" style="border-radius:12px 12px 0 0;padding:28px 32px;">
    <div style="color:#22d3ee;font-size:22px;font-weight:700;letter-spacing:-0.5px;">ALBdrinks</div>
    <div style="color:#94a3b8;font-size:13px;margin-top:4px;">Monthly Overview &middot; {month}</div>
  </td></tr>

  <tr><td bgcolor="#ffffff" style="padding:28px 32px;">
    <p style="margin:0 0 20px;font-size:14px;color:#64748b;">Monthly drinks overview for <strong style="color:#0f172a;">{month}</strong>.</p>

    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;margin-bottom:8px;">
    <tr>
      <th style="padding:8px 12px;border-bottom:2px solid #e2e8f0;color:#64748b;font-size:11px;text-transform:uppercase;letter-spacing:.06em;font-weight:600;text-align:left;">Name</th>
      <th style="padding:8px 12px;border-bottom:2px solid #e2e8f0;color:#64748b;font-size:11px;text-transform:uppercase;letter-spacing:.06em;font-weight:600;text-align:left;">Email</th>
      <th style="padding:8px 12px;border-bottom:2px solid #e2e8f0;color:#64748b;font-size:11px;text-transform:uppercase;letter-spacing:.06em;font-weight:600;text-align:center;">Units</th>
      <th style="padding:8px 12px;border-bottom:2px solid #e2e8f0;color:#64748b;font-size:11px;text-transform:uppercase;letter-spacing:.06em;font-weight:600;text-align:right;">Amount</th>
    </tr>
    {user_rows}
    </table>
    <p style="margin:8px 0 0;font-size:13px;color:#64748b;text-align:right;">
      Grand total: <strong style="color:#0369a1;">&#x20AC;{total:.2f}</strong>
    </p>
    {stock_section}
  </td></tr>

  <tr><td style="background:#f8fafc;border-top:1px solid #e2e8f0;border-radius:0 0 12px 12px;padding:18px 32px;">
    <p style="margin:0;font-size:12px;color:#94a3b8;">ALBdrinks &middot; Internal office drinks tracker</p>
  </td></tr>

</table>
</td></tr>
</table>
</body></html>"""


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
        body = (
            f"Hello {row['name']},\n\n"
            f"Your drinks summary for {target_month}:\n"
            f"Total units: {row['total_units']}\n"
            f"Total to pay: €{amount:.2f}\n\n"
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
