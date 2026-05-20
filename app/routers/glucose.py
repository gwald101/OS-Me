from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.glucose import GlucoseListOut, GlucoseReadingOut, GlucoseStatsOut
from app.services import glucose as svc

router = APIRouter(prefix="/glucose", tags=["glucose"])


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
    low_threshold: int = Query(70, description="Low glucose threshold mg/dL"),
    high_threshold: int = Query(180, description="High glucose threshold mg/dL"),
    db: AsyncSession = Depends(get_db),
):
    return await svc.get_stats(db, start, end, low_threshold, high_threshold)


@router.get("", response_model=GlucoseListOut)
async def list_readings(
    start: datetime | None = Query(None, description="Filter from this datetime (inclusive)"),
    end: datetime | None = Query(None, description="Filter until this datetime (inclusive)"),
    limit: int = Query(288, ge=0, description="Max rows to return; 0 = no limit (return all)"),
    offset: int = Query(0, ge=0, description="Pagination offset (ignored when limit=0)"),
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_readings(db, start, end, limit, offset)
