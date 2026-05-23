from fastapi import APIRouter, Request, Response
from sqlalchemy import text

from app.config import settings
from app.database import AsyncSessionLocal
from app.services.glucose import get_last_reading_age_minutes
from app.services.insulin import get_last_basal_age_minutes

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(request: Request, response: Response):
    db_status = "ok"
    dexcom_status = "ok"
    tandem_status = "disabled" if not settings.tandem_enabled else "ok"
    glucose_age_min = None
    basal_age_min = None
    active_pump = None

    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
            glucose_age_min = await get_last_reading_age_minutes(db)
            if settings.tandem_enabled:
                basal_age_min = await get_last_basal_age_minutes(db)
    except Exception:
        db_status = "error"

    scheduler = getattr(request.app.state, "scheduler", None)
    scheduler_running = scheduler is not None and scheduler.running

    # Dexcom poller is always expected when scheduler runs
    if not scheduler_running:
        dexcom_status = "error"
    elif glucose_age_min is not None and glucose_age_min > settings.STALE_READING_ALERT_MINUTES:
        dexcom_status = "stale"

    # Tandem poller only when enabled
    if settings.tandem_enabled:
        if not scheduler_running:
            tandem_status = "error"
        else:
            try:
                from app.poller.tandem import get_active_pump, STALE_WARN_DAYS

                active_pump = get_active_pump()
            except Exception:
                active_pump = None
                STALE_WARN_DAYS = 7  # type: ignore
            if basal_age_min is not None and basal_age_min > STALE_WARN_DAYS * 24 * 60:
                tandem_status = "stale"

    is_healthy = (
        db_status == "ok"
        and dexcom_status in ("ok", "stale")
        and tandem_status in ("ok", "stale", "disabled")
    )
    response.status_code = 200 if is_healthy else 503

    return {
        "status": "ok" if is_healthy else "degraded",
        "db": db_status,
        "dexcom": dexcom_status,
        "tandem": tandem_status,
        "latest_glucose_age_minutes": round(glucose_age_min, 1) if glucose_age_min is not None else None,
        "latest_basal_age_minutes": round(basal_age_min, 1) if basal_age_min is not None else None,
        "tandem_active_pump": active_pump,
    }
