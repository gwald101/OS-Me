import math
import statistics
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.glucose import GlucoseReading
from app.schemas.glucose import GlucoseListOut, GlucoseReadingOut, GlucoseStatsOut


async def get_latest(db: AsyncSession) -> GlucoseReading | None:
    result = await db.execute(
        select(GlucoseReading).order_by(GlucoseReading.recorded_at.desc()).limit(1)
    )
    return result.scalar_one_or_none()


async def list_readings(
    db: AsyncSession,
    start: datetime | None,
    end: datetime | None,
    limit: int,
    offset: int,
) -> GlucoseListOut:
    query = select(GlucoseReading).order_by(GlucoseReading.recorded_at.desc())

    if start is not None:
        query = query.where(GlucoseReading.recorded_at >= start)
    if end is not None:
        query = query.where(GlucoseReading.recorded_at <= end)

    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar_one()

    no_limit = limit == 0
    if not no_limit:
        query = query.limit(limit).offset(offset)

    rows = (await db.execute(query)).scalars().all()

    return GlucoseListOut(
        total=total,
        count=len(rows),
        limit=None if no_limit else limit,
        offset=None if no_limit else offset,
        items=[GlucoseReadingOut.model_validate(r) for r in rows],
    )


async def get_stats(
    db: AsyncSession,
    start: datetime,
    end: datetime,
    low_threshold: int,
    high_threshold: int,
) -> GlucoseStatsOut:
    result = await db.execute(
        select(GlucoseReading)
        .where(GlucoseReading.recorded_at >= start)
        .where(GlucoseReading.recorded_at <= end)
        .order_by(GlucoseReading.recorded_at)
    )
    readings = result.scalars().all()

    count = len(readings)
    if count == 0:
        return GlucoseStatsOut(
            start=start,
            end=end,
            count=0,
            average_mgdl=0.0,
            min_mgdl=0,
            max_mgdl=0,
            std_dev_mgdl=0.0,
            time_in_range_pct=0.0,
            time_below_range_pct=0.0,
            time_above_range_pct=0.0,
            estimated_a1c=0.0,
            low_threshold=low_threshold,
            high_threshold=high_threshold,
        )

    values = [r.glucose_mgdl for r in readings]
    avg = statistics.mean(values)
    std_dev = statistics.stdev(values) if count > 1 else 0.0

    in_range = sum(low_threshold <= v <= high_threshold for v in values)
    below = sum(v < low_threshold for v in values)
    above = sum(v > high_threshold for v in values)

    return GlucoseStatsOut(
        start=start,
        end=end,
        count=count,
        average_mgdl=round(avg, 1),
        min_mgdl=min(values),
        max_mgdl=max(values),
        std_dev_mgdl=round(std_dev, 1),
        time_in_range_pct=round(in_range / count * 100, 1),
        time_below_range_pct=round(below / count * 100, 1),
        time_above_range_pct=round(above / count * 100, 1),
        estimated_a1c=round((avg + 46.7) / 28.7, 1),
        low_threshold=low_threshold,
        high_threshold=high_threshold,
    )


async def get_last_reading_age_minutes(db: AsyncSession) -> float | None:
    result = await db.execute(
        select(GlucoseReading.recorded_at)
        .order_by(GlucoseReading.recorded_at.desc())
        .limit(1)
    )
    ts = result.scalar_one_or_none()
    if ts is None:
        return None
    now = datetime.now(UTC)
    recorded = ts if ts.tzinfo else ts.replace(tzinfo=UTC)
    return (now - recorded).total_seconds() / 60
