from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Consumption(Base):
    __tablename__ = "consumptions"
    __table_args__ = (
        UniqueConstraint("user_id", "drink_id", "consumed_at", name="uq_consumption_event"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    drink_id: Mapped[int] = mapped_column(ForeignKey("drinks.id"), nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_price_at_time: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    consumed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    user = relationship("User", back_populates="consumptions")
    drink = relationship("Drink", back_populates="consumptions")
