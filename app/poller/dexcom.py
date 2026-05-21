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

# Dexcom Share retains ~24h of history. On the first poll after startup we pull
# the full window to backfill any gap; subsequent polls only need a small window
# (the upsert is idempotent, so a little overlap is harmless and covers missed polls).
BACKFILL_MINUTES = 1440
BACKFILL_MAX_COUNT = 288
STEADY_MINUTES = 30
STEADY_MAX_COUNT = 6

# Flipped to False after the first successful backfill poll.
_needs_backfill = True


def _make_reading_id(recorded_at_iso: str, glucose_mgdl: int) -> str:
    raw = f"{recorded_at_iso}:{glucose_mgdl}"
    return hashlib.md5(raw.encode()).hexdigest()


def _fetch_sync(minutes: int, max_count: int) -> list[dict] | None:
    """Synchronous Dexcom Share poll — runs in a thread executor.

    Returns a list of reading rows (possibly empty) on success, or None if the
    poll failed, so the caller can tell "no recent data" apart from "error".
    """
    try:
        region = Region.OUS if settings.DEXCOM_OUTSIDE_US else Region.US
        dx = Dexcom(
            username=settings.DEXCOM_USERNAME,
            password=settings.DEXCOM_PASSWORD,
            region=region,
        )
        readings = dx.get_glucose_readings(minutes=minutes, max_count=max_count)
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
        return None


async def poll_dexcom() -> None:
    global _needs_backfill

    if not settings.DEXCOM_USERNAME or not settings.DEXCOM_PASSWORD:
        log.warning("Dexcom credentials not configured — skipping poll")
        return

    if _needs_backfill:
        minutes, max_count = BACKFILL_MINUTES, BACKFILL_MAX_COUNT
    else:
        minutes, max_count = STEADY_MINUTES, STEADY_MAX_COUNT

    rows = await asyncio.get_event_loop().run_in_executor(
        None, _fetch_sync, minutes, max_count
    )

    if rows is None:
        # Poll errored; keep backfill pending so the next cycle retries the wide window.
        return

    # Poll succeeded — mark backfill done even if it returned nothing (no recent
    # data), so we don't re-pull 24h on every cycle.
    _needs_backfill = False

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
