from pathlib import Path

from alembic.config import Config
from sqlalchemy import select

from alembic import command
from app.core.security import get_password_hash
from app.db.database import SessionLocal
from app.models import Drink, User, UserRole

REPO_ROOT = Path(__file__).resolve().parent.parent


def run_migrations() -> None:
    cfg = Config(str(REPO_ROOT / "alembic.ini"))
    command.upgrade(cfg, "head")


def main() -> None:
    run_migrations()
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
