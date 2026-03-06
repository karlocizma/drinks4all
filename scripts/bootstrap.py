from sqlalchemy import select

from app.core.security import get_password_hash
from app.db.database import Base, SessionLocal, engine
from app.models import Drink, Fridge, Team, User, UserRole


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        team = db.scalar(select(Team).where(Team.name == "Office"))
        if team is None:
            team = Team(name="Office")
            db.add(team)
            db.flush()

        fridge = db.scalar(select(Fridge).where(Fridge.name == "Main Fridge"))
        if fridge is None:
            fridge = Fridge(name="Main Fridge", location="Kitchen", team_id=team.id)
            db.add(fridge)
            db.flush()

        admin = db.scalar(select(User).where(User.email == "admin@drinks.local"))
        if admin is None:
            db.add(
                User(
                    name="Admin",
                    email="admin@drinks.local",
                    password_hash=get_password_hash("admin123"),
                    role=UserRole.ADMIN,
                    is_active=True,
                    team_id=team.id,
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
                        team_id=team.id,
                        fridge_id=fridge.id,
                        is_active=True,
                    ),
                    Drink(
                        name="Sparkling Water",
                        photo_url="https://picsum.photos/seed/water/400/300",
                        unit_price=1.00,
                        stock_quantity=40,
                        low_stock_threshold=8,
                        team_id=team.id,
                        fridge_id=fridge.id,
                        is_active=True,
                    ),
                    Drink(
                        name="Orange Juice",
                        photo_url="https://picsum.photos/seed/oj/400/300",
                        unit_price=2.20,
                        stock_quantity=20,
                        low_stock_threshold=4,
                        team_id=team.id,
                        fridge_id=fridge.id,
                        is_active=True,
                    ),
                ]
            )

        db.commit()
        print("Bootstrapped admin, team/fridge and sample drinks")
        print("Admin login: admin@drinks.local / admin123")
    finally:
        db.close()


if __name__ == "__main__":
    main()
