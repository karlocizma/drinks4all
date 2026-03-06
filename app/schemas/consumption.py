from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class ConsumptionCreate(BaseModel):
    drink_id: int
    quantity: int = 1


class ConsumptionOut(BaseModel):
    id: int
    user_id: int
    drink_id: int
    quantity: int
    unit_price_at_time: Decimal
    consumed_at: datetime

    model_config = {"from_attributes": True}
