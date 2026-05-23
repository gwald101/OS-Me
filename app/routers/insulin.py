from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.insulin import (
    BasalEventOut,
    BasalListOut,
    BolusEventOut,
    BolusListOut,
)
from app.services import insulin as svc

basal_router = APIRouter(prefix="/basal", tags=["basal"])
bolus_router = APIRouter(prefix="/bolus", tags=["bolus"])


@basal_router.get("/latest", response_model=BasalEventOut)
async def get_latest_basal(db: AsyncSession = Depends(get_db)):
    row = await svc.get_latest_basal(db)
    if row is None:
        raise HTTPException(status_code=404, detail="No basal events found")
    return row


@basal_router.get("", response_model=BasalListOut)
async def list_basal(
    start: datetime | None = Query(None),
    end: datetime | None = Query(None),
    limit: int = Query(288, ge=0, le=10000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_basal(db, start, end, limit, offset)


@bolus_router.get("/latest", response_model=BolusEventOut)
async def get_latest_bolus(db: AsyncSession = Depends(get_db)):
    row = await svc.get_latest_bolus(db)
    if row is None:
        raise HTTPException(status_code=404, detail="No bolus events found")
    return row


@bolus_router.get("", response_model=BolusListOut)
async def list_bolus(
    start: datetime | None = Query(None),
    end: datetime | None = Query(None),
    limit: int = Query(288, ge=0, le=10000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_bolus(db, start, end, limit, offset)
