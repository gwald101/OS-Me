from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.glucose import GlucoseListOut, GlucoseReadingOut, GlucoseStatsOut
from app.services import glucose as svc

router = APIRouter(prefix="/glucose", tags=["glucose"])

MAX_STATS_RANGE = timedelta(days=366)


@router.get("/latest", response_model=GlucoseReadingOut)
async def get_latest(db: AsyncSession = Depends(get_db)):
    reading = await svc.get_latest(db)
    if reading is None:
        raise HTTPException(status_code=404, detail="No readings found")
    return reading


@router.get("/stats", response_model=GlucoseStatsOut)
async def get_stats(
    start: datetime = Query(..., description="Range start (ISO8601)"),
    end: datetime = Query(..., description="Range end (ISO8601)"),
    low_threshold: int = Query(70, ge=0, le=500, description="Low glucose threshold mg/dL"),
    high_threshold: int = Query(180, ge=0, le=500, description="High glucose threshold mg/dL"),
    db: AsyncSession = Depends(get_db),
):
    if start > end:
        raise HTTPException(status_code=400, detail="start must be before end")
    if end - start > MAX_STATS_RANGE:
        raise HTTPException(status_code=400, detail="Date range must not exceed 366 days")
    if low_threshold >= high_threshold:
        raise HTTPException(
            status_code=400, detail="low_threshold must be less than high_threshold"
        )
    return await svc.get_stats(db, start, end, low_threshold, high_threshold)


@router.get("", response_model=GlucoseListOut)
async def list_readings(
    start: datetime | None = Query(None, description="Filter from this datetime (inclusive)"),
    end: datetime | None = Query(None, description="Filter until this datetime (inclusive)"),
    limit: int = Query(288, ge=0, le=10000, description="Max rows to return; 0 = no limit (return all)"),
    offset: int = Query(0, ge=0, description="Pagination offset (ignored when limit=0)"),
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_readings(db, start, end, limit, offset)
