from decimal import Decimal

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "USER"


class UserUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None
    role: str | None = None


class PasswordReset(BaseModel):
    password: str


class MonthlyUserReport(BaseModel):
    user_id: int
    name: str
    email: str
    total_units: int
    total_amount: Decimal


class MonthlyDrinkReport(BaseModel):
    drink_id: int
    drink_name: str
    total_units: int
    total_amount: Decimal
