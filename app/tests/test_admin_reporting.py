from datetime import datetime

from app.models import Consumption, Drink


def test_admin_can_create_drink_and_report(client, admin_user, normal_user, db):
    login_admin = client.post("/auth/login", json={"email": admin_user.email, "password": "admin123"})
    assert login_admin.status_code == 200

    create_drink = client.post(
        "/admin/drinks",
        json={
            "name": "Water",
            "photo_url": "https://example.com/water.jpg",
            "unit_price": 1.25,
            "is_active": True,
        },
    )
    assert create_drink.status_code == 200

    drink_id = create_drink.json()["id"]
    db.add(
        Consumption(
            user_id=normal_user.id,
            drink_id=drink_id,
            quantity=3,
            unit_price_at_time=1.25,
            consumed_at=datetime(2026, 3, 3, 10, 0, 0),
        )
    )
    db.commit()

    report = client.get("/admin/reports?month=2026-03")
    assert report.status_code == 200
    payload = report.json()
    assert payload["overall_total"] == 3.75
    assert any(user["email"] == normal_user.email for user in payload["users"])


def test_run_billing_records_email_logs(client, admin_user, normal_user, db, monkeypatch):
    drink = Drink(name="Cola", photo_url="https://example.com/cola.jpg", unit_price=2.0, is_active=True)
    db.add(drink)
    db.commit()
    db.refresh(drink)

    db.add(
        Consumption(
            user_id=normal_user.id,
            drink_id=drink.id,
            quantity=2,
            unit_price_at_time=2.0,
            consumed_at=datetime(2026, 3, 2, 10, 0, 0),
        )
    )
    db.commit()

    sent = []

    def fake_send_email(recipient: str, subject: str, body: str):
        sent.append((recipient, subject, body))

    monkeypatch.setattr("app.services.billing_job.send_email", fake_send_email)

    login_admin = client.post("/auth/login", json={"email": admin_user.email, "password": "admin123"})
    assert login_admin.status_code == 200

    run = client.post("/admin/run-billing?month=2026-03")
    assert run.status_code == 200
    assert run.json()["sent_users"] >= 1
    assert len(sent) >= 2
