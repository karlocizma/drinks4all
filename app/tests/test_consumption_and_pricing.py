from app.models import Drink


def test_consumption_adds_units_and_total(client, normal_user, db):
    drink = Drink(name="Cola", photo_url="https://example.com/cola.jpg", unit_price=2.5, is_active=True)
    db.add(drink)
    db.commit()
    db.refresh(drink)

    login = client.post("/auth/login", json={"email": normal_user.email, "password": "user123"})
    assert login.status_code == 200

    add = client.post("/consumptions", json={"drink_id": drink.id, "quantity": 2})
    assert add.status_code == 200

    summary = client.get("/me/summary?month=2026-03")
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
