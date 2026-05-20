import asyncio
import hashlib
import logging
from datetime import UTC

from pydexcom import Dexcom
from pydexcom.const import Region
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.glucose import GlucoseReading

log = logging.getLogger(__name__)


def _make_reading_id(recorded_at_iso: str, glucose_mgdl: int) -> str:
    raw = f"{recorded_at_iso}:{glucose_mgdl}"
    return hashlib.md5(raw.encode()).hexdigest()


def _fetch_sync() -> list[dict]:
    """Synchronous Dexcom Share poll — runs in a thread executor."""
    try:
        region = Region.OUS if settings.DEXCOM_OUTSIDE_US else Region.US
        dx = Dexcom(
            username=settings.DEXCOM_USERNAME,
            password=settings.DEXCOM_PASSWORD,
            region=region,
        )
        readings = dx.get_glucose_readings(minutes=10, max_count=3)
        rows = []
        for r in readings or []:
            # Ensure UTC-aware timestamp
            recorded_at = r.datetime
            if recorded_at.tzinfo is None:
                recorded_at = recorded_at.replace(tzinfo=UTC)
            else:
                recorded_at = recorded_at.astimezone(UTC)

            rows.append(
                {
                    "reading_id": _make_reading_id(recorded_at.isoformat(), r.value),
                    "recorded_at": recorded_at,
                    "glucose_mgdl": r.value,
                    "trend": r.trend_direction,
                    "trend_arrow": r.trend_arrow,
                    "source": "dexcom_share",
                }
            )
        return rows
    except Exception:
        log.exception("Dexcom Share poll failed")
        return []


async def poll_dexcom() -> None:
    if not settings.DEXCOM_USERNAME or not settings.DEXCOM_PASSWORD:
        log.warning("Dexcom credentials not configured — skipping poll")
        return

    rows = await asyncio.get_event_loop().run_in_executor(None, _fetch_sync)
    if not rows:
        log.debug("No new readings from Dexcom Share")
        return

    async with AsyncSessionLocal() as session:
        stmt = pg_insert(GlucoseReading).values(rows).on_conflict_do_nothing(
            index_elements=["reading_id"]
        )
        await session.execute(stmt)
        await session.commit()

    log.info("Upserted %d Dexcom reading(s)", len(rows))
