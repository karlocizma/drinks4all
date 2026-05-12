from sqlalchemy import select, text

from app.core.security import get_password_hash
from app.db.database import Base, SessionLocal, engine
from app.models import Drink, User, UserRole


def ensure_schema_compat() -> None:
    statements = [
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_pending_approval BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE billing_periods ADD COLUMN IF NOT EXISTS closed_at TIMESTAMP",
        "ALTER TABLE drinks ADD COLUMN IF NOT EXISTS stock_quantity INTEGER",
        "ALTER TABLE drinks ADD COLUMN IF NOT EXISTS low_stock_threshold INTEGER NOT NULL DEFAULT 5",
        "ALTER TABLE consumptions DROP COLUMN IF EXISTS team_id",
        "ALTER TABLE consumptions DROP COLUMN IF EXISTS fridge_id",
        "ALTER TABLE drinks DROP COLUMN IF EXISTS team_id",
        "ALTER TABLE drinks DROP COLUMN IF EXISTS fridge_id",
        "ALTER TABLE users DROP COLUMN IF EXISTS team_id",
        "DROP TABLE IF EXISTS fridges CASCADE",
        "DROP TABLE IF EXISTS teams CASCADE",
    ]
    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))


def main() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_schema_compat()
    db = SessionLocal()
    try:
        admin = db.scalar(select(User).where(User.email == "admin@drinks.local"))
        if admin is None:
            db.add(
                User(
                    name="Admin",
                    email="admin@drinks.local",
                    password_hash=get_password_hash("admin123"),
                    role=UserRole.ADMIN,
                    is_active=True,
                )
            )

        if db.scalar(select(Drink).limit(1)) is None:
            db.add_all(
                [
                    Drink(
                        name="Cola",
                        photo_url="https://picsum.photos/seed/cola/400/300",
                        unit_price=1.50,
                        stock_quantity=30,
                        low_stock_threshold=5,
                        is_active=True,
                    ),
                    Drink(
                        name="Sparkling Water",
                        photo_url="https://picsum.photos/seed/water/400/300",
                        unit_price=1.00,
                        stock_quantity=40,
                        low_stock_threshold=8,
                        is_active=True,
                    ),
                    Drink(
                        name="Orange Juice",
                        photo_url="https://picsum.photos/seed/oj/400/300",
                        unit_price=2.20,
                        stock_quantity=20,
                        low_stock_threshold=4,
                        is_active=True,
                    ),
                ]
            )

        db.commit()
        print("Bootstrap complete.")
        print("Admin login: admin@drinks.local / admin123")
    finally:
        db.close()


if __name__ == "__main__":
    main()
