from datetime import datetime

from pydantic import BaseModel, ConfigDict


class GlucoseReadingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    recorded_at: datetime
    glucose_mgdl: int
    trend: str
    trend_arrow: str | None
    source: str


class GlucoseListOut(BaseModel):
    total: int
    count: int
    limit: int | None
    offset: int | None
    items: list[GlucoseReadingOut]


class GlucoseStatsOut(BaseModel):
    start: datetime
    end: datetime
    count: int
    average_mgdl: float
    min_mgdl: int
    max_mgdl: int
    std_dev_mgdl: float
    time_in_range_pct: float
    time_below_range_pct: float
    time_above_range_pct: float
    estimated_a1c: float
    low_threshold: int
    high_threshold: int
