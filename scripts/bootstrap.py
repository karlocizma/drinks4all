from sqlalchemy import select

from app.core.security import get_password_hash
from app.db.database import Base, SessionLocal, engine
from app.models import Drink, User, UserRole


def main() -> None:
    Base.metadata.create_all(bind=engine)
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
                    Drink(name="Cola", photo_url="https://picsum.photos/seed/cola/400/300", unit_price=1.50, is_active=True),
                    Drink(name="Sparkling Water", photo_url="https://picsum.photos/seed/water/400/300", unit_price=1.00, is_active=True),
                    Drink(name="Orange Juice", photo_url="https://picsum.photos/seed/oj/400/300", unit_price=2.20, is_active=True),
                ]
            )

        db.commit()
        print("Bootstrapped admin and sample drinks")
        print("Admin login: admin@drinks.local / admin123")
    finally:
        db.close()


if __name__ == "__main__":
    main()
