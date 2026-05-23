from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.insulin import BasalEvent, BolusEvent
from app.schemas.insulin import (
    BasalEventOut,
    BasalListOut,
    BolusEventOut,
    BolusListOut,
)


async def get_latest_basal(db: AsyncSession) -> BasalEvent | None:
    result = await db.execute(
        select(BasalEvent).order_by(BasalEvent.recorded_at.desc()).limit(1)
    )
    return result.scalar_one_or_none()


async def list_basal(
    db: AsyncSession,
    start: datetime | None,
    end: datetime | None,
    limit: int,
    offset: int,
) -> BasalListOut:
    query = select(BasalEvent).order_by(BasalEvent.recorded_at.desc())
    if start is not None:
        query = query.where(BasalEvent.recorded_at >= start)
    if end is not None:
        query = query.where(BasalEvent.recorded_at <= end)

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()

    no_limit = limit == 0
    if not no_limit:
        query = query.limit(limit).offset(offset)
    rows = (await db.execute(query)).scalars().all()

    return BasalListOut(
        total=total,
        count=len(rows),
        limit=None if no_limit else limit,
        offset=None if no_limit else offset,
        items=[BasalEventOut.model_validate(r) for r in rows],
    )


async def get_latest_bolus(db: AsyncSession) -> BolusEvent | None:
    result = await db.execute(
        select(BolusEvent).order_by(BolusEvent.recorded_at.desc()).limit(1)
    )
    return result.scalar_one_or_none()


async def list_bolus(
    db: AsyncSession,
    start: datetime | None,
    end: datetime | None,
    limit: int,
    offset: int,
) -> BolusListOut:
    query = select(BolusEvent).order_by(BolusEvent.recorded_at.desc())
    if start is not None:
        query = query.where(BolusEvent.recorded_at >= start)
    if end is not None:
        query = query.where(BolusEvent.recorded_at <= end)

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()

    no_limit = limit == 0
    if not no_limit:
        query = query.limit(limit).offset(offset)
    rows = (await db.execute(query)).scalars().all()

    return BolusListOut(
        total=total,
        count=len(rows),
        limit=None if no_limit else limit,
        offset=None if no_limit else offset,
        items=[BolusEventOut.model_validate(r) for r in rows],
    )


async def get_last_basal_age_minutes(db: AsyncSession) -> float | None:
    result = await db.execute(
        select(BasalEvent.recorded_at).order_by(BasalEvent.recorded_at.desc()).limit(1)
    )
    ts = result.scalar_one_or_none()
    if ts is None:
        return None
    recorded = ts if ts.tzinfo else ts.replace(tzinfo=UTC)
    return (datetime.now(UTC) - recorded).total_seconds() / 60
