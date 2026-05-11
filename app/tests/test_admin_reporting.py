from datetime import datetime

from app.models import BillingPeriod, Consumption, Drink


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


def test_manual_billing_closes_month_and_report_marks_it_closed(client, admin_user, normal_user, db, monkeypatch):
    drink = Drink(name="Water", photo_url="https://example.com/water.jpg", unit_price=1.0, is_active=True)
    db.add(drink)
    db.commit()
    db.refresh(drink)

    db.add(
        Consumption(
            user_id=normal_user.id,
            drink_id=drink.id,
            quantity=1,
            unit_price_at_time=1.0,
            consumed_at=datetime(2026, 3, 5, 10, 0, 0),
        )
    )
    db.commit()

    monkeypatch.setattr("app.services.billing_job.send_email", lambda recipient, subject, body: None)

    login_admin = client.post("/auth/login", json={"email": admin_user.email, "password": "admin123"})
    assert login_admin.status_code == 200

    run = client.post("/admin/run-billing?month=2026-03")
    assert run.status_code == 200
    assert run.json()["month_closed"] is True
    assert run.json()["closed_periods"] >= 1

    period = db.query(BillingPeriod).filter(BillingPeriod.month == "2026-03").first()
    assert period is not None
    assert period.closed_at is not None

    report = client.get("/admin/reports?month=2026-03")
    assert report.status_code == 200
    assert report.json()["is_closed"] is True


def test_reset_month_deletes_month_data_and_restores_stock(client, admin_user, normal_user, db):
    drink = Drink(
        name="Cola",
        photo_url="https://example.com/cola.jpg",
        unit_price=2.0,
        stock_quantity=8,
        is_active=True,
    )
    db.add(drink)
    db.commit()
    db.refresh(drink)

    db.add(
        Consumption(
            user_id=normal_user.id,
            drink_id=drink.id,
            quantity=2,
            unit_price_at_time=2.0,
            consumed_at=datetime(2026, 3, 6, 10, 0, 0),
        )
    )
    drink.stock_quantity = 6
    db.commit()

    login_admin = client.post("/auth/login", json={"email": admin_user.email, "password": "admin123"})
    assert login_admin.status_code == 200

    reset = client.post("/admin/reset-month?month=2026-03")
    assert reset.status_code == 200
    payload = reset.json()
    assert payload["deleted_consumptions"] == 1
    assert payload["restored_stock_units"] == 2

    db.refresh(drink)
    assert drink.stock_quantity == 8

    report = client.get("/admin/reports?month=2026-03")
    assert report.status_code == 200
    assert report.json()["overall_total"] == 0.0
    assert report.json()["is_closed"] is False


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
