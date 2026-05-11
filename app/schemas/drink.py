from decimal import Decimal

from pydantic import BaseModel


class DrinkBase(BaseModel):
    name: str
    photo_url: str
    unit_price: Decimal
    stock_quantity: int | None = None
    low_stock_threshold: int = 5
    is_active: bool = True


class DrinkCreate(DrinkBase):
    pass


class DrinkUpdate(BaseModel):
    name: str | None = None
    photo_url: str | None = None
    unit_price: Decimal | None = None
    stock_quantity: int | None = None
    low_stock_threshold: int | None = None
    is_active: bool | None = None


class DrinkOut(BaseModel):
    id: int
    name: str
    photo_url: str
    unit_price: Decimal
    stock_quantity: int | None
    low_stock_threshold: int
    is_active: bool

    model_config = {"from_attributes": True}
