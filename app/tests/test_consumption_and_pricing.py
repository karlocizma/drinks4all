from app.core.settings import settings
from app.core.time import utcnow
from app.models import Drink
from app.services.reporting import close_billing_month, user_month_summary


def test_consumption_adds_units_and_total(client, normal_user, db):
    drink = Drink(name="Cola", photo_url="https://example.com/cola.jpg", unit_price=2.5, is_active=True)
    db.add(drink)
    db.commit()
    db.refresh(drink)

    login = client.post("/auth/login", json={"email": normal_user.email, "password": "user123"})
    assert login.status_code == 200

    add = client.post("/consumptions", json={"drink_id": drink.id, "quantity": 2})
    assert add.status_code == 200

    current_month = utcnow().strftime("%Y-%m")
    summary = client.get(f"/me/summary?month={current_month}")
    assert summary.status_code == 200
    assert summary.json()["total_units"] == 2
    assert summary.json()["total_amount"] == 5.0


def test_historical_price_is_preserved(client, normal_user, db):
    drink = Drink(name="Juice", photo_url="https://example.com/juice.jpg", unit_price=1.5, is_active=True)
    db.add(drink)
    db.commit()
    db.refresh(drink)

    login = client.post("/auth/login", json={"email": normal_user.email, "password": "user123"})
    assert login.status_code == 200

    add = client.post("/consumptions", json={"drink_id": drink.id, "quantity": 1})
    assert add.status_code == 200

    drink.unit_price = 3.0
    db.commit()

    add2 = client.post("/consumptions", json={"drink_id": drink.id, "quantity": 1})
    assert add2.status_code == 200
    first_price = float(add.json()["unit_price_at_time"])
    second_price = float(add2.json()["unit_price_at_time"])
    assert first_price == 1.5
    assert second_price == 3.0


def test_low_stock_email_sent_once_when_threshold_is_crossed(client, normal_user, db, monkeypatch):
    drink = Drink(
        name="Mate",
        photo_url="https://example.com/mate.jpg",
        unit_price=1.8,
        stock_quantity=6,
        low_stock_threshold=5,
        is_active=True,
    )
    db.add(drink)
    db.commit()
    db.refresh(drink)

    sent = []

    def fake_send_email(recipient: str, subject: str, body: str, html: str | None = None):
        sent.append((recipient, subject, body))

    monkeypatch.setattr("app.api.user.send_email", fake_send_email)
    monkeypatch.setattr(settings, "buyer_report_email", "stock@test.local")

    login = client.post("/auth/login", json={"email": normal_user.email, "password": "user123"})
    assert login.status_code == 200

    first = client.post("/consumptions", json={"drink_id": drink.id, "quantity": 1})
    second = client.post("/consumptions", json={"drink_id": drink.id, "quantity": 1})

    assert first.status_code == 200
    assert second.status_code == 200
    assert len(sent) == 1
    assert sent[0][0] == "stock@test.local"
    assert "Low stock alert" in sent[0][1]


def test_consumption_is_blocked_for_closed_month(client, normal_user, db):
    drink = Drink(name="Cola", photo_url="https://example.com/cola.jpg", unit_price=2.5, is_active=True)
    db.add(drink)
    db.commit()
    db.refresh(drink)

    summary = user_month_summary(db, normal_user.id, utcnow().strftime("%Y-%m"))
    close_billing_month(
        db,
        utcnow().strftime("%Y-%m"),
        [
            {
                "user_id": normal_user.id,
                "name": normal_user.name,
                "email": normal_user.email,
                "total_units": summary["total_units"],
                "total_amount": summary["total_amount"],
                "drinks": summary["drinks"],
            }
        ],
    )
    db.commit()

    login = client.post("/auth/login", json={"email": normal_user.email, "password": "user123"})
    assert login.status_code == 200

    add = client.post("/consumptions", json={"drink_id": drink.id, "quantity": 1})
    assert add.status_code == 409
    assert "closed for billing" in add.text
