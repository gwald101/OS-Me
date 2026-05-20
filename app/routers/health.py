from fastapi import APIRouter, Request, Response
from sqlalchemy import text

from app.config import settings
from app.database import AsyncSessionLocal
from app.services.glucose import get_last_reading_age_minutes

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(request: Request, response: Response):
    db_status = "ok"
    poller_status = "ok"
    age_minutes = None

    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
            age_minutes = await get_last_reading_age_minutes(db)
    except Exception:
        db_status = "error"

    scheduler = getattr(request.app.state, "scheduler", None)
    if scheduler is None or not scheduler.running:
        poller_status = "error"
    elif age_minutes is not None and age_minutes > settings.STALE_READING_ALERT_MINUTES:
        poller_status = "stale"

    is_healthy = db_status == "ok" and poller_status in ("ok", "stale")
    response.status_code = 200 if is_healthy else 503

    return {
        "status": "ok" if is_healthy else "degraded",
        "db": db_status,
        "poller": poller_status,
        "latest_reading_age_minutes": round(age_minutes, 1) if age_minutes is not None else None,
    }
