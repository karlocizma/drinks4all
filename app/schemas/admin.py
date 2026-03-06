from decimal import Decimal

from pydantic import BaseModel


class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    role: str = "USER"
    team_id: int | None = None


class UserUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None
    role: str | None = None
    team_id: int | None = None


class PasswordReset(BaseModel):
    password: str


class PasswordChange(BaseModel):
    old_password: str
    new_password: str


class TeamCreate(BaseModel):
    name: str


class TeamUpdate(BaseModel):
    name: str


class FridgeCreate(BaseModel):
    name: str
    location: str | None = None
    team_id: int | None = None


class FridgeUpdate(BaseModel):
    name: str
    location: str | None = None
    team_id: int | None = None


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
