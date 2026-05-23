from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class BasalEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    recorded_at: datetime
    duration_seconds: int | None
    rate_units_per_hour: Decimal
    delivery_type: str
    source: str


class BasalListOut(BaseModel):
    total: int
    count: int
    limit: int | None
    offset: int | None
    items: list[BasalEventOut]


class BolusEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    recorded_at: datetime
    insulin_units: Decimal
    requested_units: Decimal | None
    carbs_grams: Decimal | None
    bg_input_mgdl: int | None
    bolus_type: str
    source: str


class BolusListOut(BaseModel):
    total: int
    count: int
    limit: int | None
    offset: int | None
    items: list[BolusEventOut]
