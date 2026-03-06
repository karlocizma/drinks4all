from app.models import Drink


def test_login_success_and_failure(client, admin_user):
    fail = client.post("/auth/login", json={"email": admin_user.email, "password": "wrong"})
    assert fail.status_code == 401

    ok = client.post("/auth/login", json={"email": admin_user.email, "password": "admin123"})
    assert ok.status_code == 200
    assert ok.json()["role"] == "ADMIN"


def test_role_protection(client, normal_user, db):
    db.add(Drink(name="Water", photo_url="https://example.com/water.jpg", unit_price=1.0, is_active=True))
    db.commit()

    login = client.post("/auth/login", json={"email": normal_user.email, "password": "user123"})
    assert login.status_code == 200

    blocked = client.get("/admin/users")
    assert blocked.status_code == 403
