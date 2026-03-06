from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class BillingStatus(StrEnum):
    OPEN = "OPEN"
    SENT = "SENT"
    PAID = "PAID"


class BillingPeriod(Base):
    __tablename__ = "billing_periods"
    __table_args__ = (UniqueConstraint("month", "user_id", name="uq_billing_month_user"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    month: Mapped[str] = mapped_column(String(7), nullable=False, index=True)  # YYYY-MM
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    total_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    status: Mapped[BillingStatus] = mapped_column(Enum(BillingStatus), nullable=False, default=BillingStatus.OPEN)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="billing_periods")


class EmailLog(Base):
    __tablename__ = "email_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    recipient: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    month: Mapped[str] = mapped_column(String(7), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    error: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
