from decimal import Decimal

from pydantic import BaseModel, HttpUrl


class DrinkBase(BaseModel):
    name: str
    photo_url: HttpUrl
    unit_price: Decimal
    is_active: bool = True


class DrinkCreate(DrinkBase):
    pass


class DrinkUpdate(BaseModel):
    name: str | None = None
    photo_url: HttpUrl | None = None
    unit_price: Decimal | None = None
    is_active: bool | None = None


class DrinkOut(BaseModel):
    id: int
    name: str
    photo_url: str
    unit_price: Decimal
    is_active: bool

    model_config = {"from_attributes": True}
