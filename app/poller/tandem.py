"""Tandem Source poller.

Authenticates against Tandem Source (no official public API; we use tconnectsync,
which reverse-engineers the undocumented endpoints), selects the most recently
active pump on the account, fetches basal + bolus events, and upserts them.

Mirrors the patterns from app/poller/dexcom.py:
- Synchronous library wrapped in run_in_executor to keep the event loop free
- Adaptive window: wide (24h) backfill on first poll, narrow (2h) thereafter
- Distinguishes error (None) from no-data (empty list) so a failed first poll
  retries the backfill on the next cycle
- ``ON CONFLICT (event_id) DO NOTHING`` upsert — idempotent across restarts
"""
import asyncio
import logging
from datetime import UTC

import arrow
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.insulin import BasalEvent, BolusEvent

log = logging.getLogger(__name__)

BACKFILL_HOURS = 24
STEADY_HOURS = 2
STALE_WARN_DAYS = 7

# Module-level state — flipped after first successful poll completes.
_needs_backfill = True
# Cached active pump info (refreshed each poll, but stored for /health visibility).
_active_pump: dict | None = None


def _select_active_device(api) -> dict:
    """Return the pump record with the most recent uploaded events."""
    pumps = api.tandemsource.pump_event_metadata()
    if not pumps:
        raise RuntimeError("No pumps on this Tandem Source account")
    chosen = max(pumps, key=lambda p: arrow.get(p["maxDateWithEvents"]))
    return chosen


def _to_utc(ts):
    """Coerce an arrow/datetime to a UTC-aware datetime."""
    a = arrow.get(ts)
    return a.to("utc").datetime


def _parse_basal(events, window_end) -> list[dict]:
    """Convert Tandem basal events into our row shape.

    Replicates tconnectsync's ProcessBasal logic: each basal-rate-change event is
    a segment whose duration extends until the next change (or window_end).
    """
    from tconnectsync.eventparser import events as et
    from tconnectsync.sync.tandemsource.helpers import (
        insulin_float_round,
        insulin_milliunits_to_real,
    )
    from tconnectsync.eventparser.utils import bitmask_to_list

    basal_events = [
        e for e in events
        if isinstance(e, (et.LidBasalDelivery, et.LidBasalRateChange))
    ]
    basal_events.sort(key=lambda e: arrow.get(e.eventTimestamp))

    rows = []
    for i, e in enumerate(basal_events):
        start = arrow.get(e.eventTimestamp)
        next_start = (
            arrow.get(basal_events[i + 1].eventTimestamp)
            if i + 1 < len(basal_events)
            else arrow.get(window_end)
        )
        duration = (next_start - start).total_seconds()

        if isinstance(e, et.LidBasalDelivery):
            rate = insulin_milliunits_to_real(e.commandedRate)
            delivery_type = ", ".join(bitmask_to_list(e.commandedRateSource)) or "basal"
        else:  # LidBasalRateChange
            rate = insulin_float_round(e.commandedbasalrate)
            delivery_type = ", ".join(bitmask_to_list(e.changetype)) or "rate_change"

        rows.append({
            "event_id": f"basal:{e.seqNum}",
            "recorded_at": _to_utc(start),
            "duration_seconds": int(max(0, duration)),
            "rate_units_per_hour": rate,
            "delivery_type": delivery_type[:255],
            "source": "tandem_source",
        })
    return rows


def _parse_bolus(events) -> list[dict]:
    """Convert Tandem bolus events into our row shape.

    Replicates tconnectsync's ProcessBolus logic: bolus events come as multiple
    messages (Completed + RequestedMsg1/2/3) grouped by bolusid; combine them.
    """
    from tconnectsync.eventparser import events as et
    from tconnectsync.sync.tandemsource.helpers import insulin_float_round

    by_bolus_id: dict = {}
    for e in events:
        if isinstance(
            e,
            (
                et.LidBolusCompleted,
                et.LidBolusRequestedMsg1,
                et.LidBolusRequestedMsg2,
                et.LidBolusRequestedMsg3,
            ),
        ):
            by_bolus_id.setdefault(e.bolusid, {})[type(e)] = e

    rows = []
    for bolus_id, msgs in by_bolus_id.items():
        completed = msgs.get(et.LidBolusCompleted)
        if completed is None:
            continue
        msg1 = msgs.get(et.LidBolusRequestedMsg1)
        msg2 = msgs.get(et.LidBolusRequestedMsg2)

        delivered = insulin_float_round(completed.insulindelivered)
        requested = None
        carbs = None
        bg = None
        if msg1 is not None:
            if getattr(msg1, "carbamount", 0) and msg1.carbamount > 0:
                carbs = float(msg1.carbamount)
            if getattr(msg1, "BG", 0) and msg1.BG > 0:
                bg = int(msg1.BG)

        # Determine bolus type
        if msg2 is not None and getattr(msg2, "optionsRaw", None) is not None:
            opts = et.LidBolusRequestedMsg2.OptionsMap.get(str(msg2.optionsRaw))
            bolus_type = (opts or "standard").lower().replace(" ", "_")
        else:
            bolus_type = "standard"

        rows.append({
            "event_id": f"bolus:{bolus_id}",
            "recorded_at": _to_utc(completed.eventTimestamp),
            "insulin_units": delivered,
            "requested_units": requested,
            "carbs_grams": carbs,
            "bg_input_mgdl": bg,
            "bolus_type": bolus_type[:64],
            "source": "tandem_source",
        })
    return rows


def _fetch_sync(window_hours: int) -> tuple[list[dict], list[dict]] | None:
    """Synchronous fetch + parse. Returns (basal_rows, bolus_rows) or None on error."""
    global _active_pump
    try:
        from tconnectsync.api import TConnectApi

        api = TConnectApi(settings.TANDEM_EMAIL, settings.TANDEM_PASSWORD)
        chosen = _select_active_device(api)
        _active_pump = {
            "serial_number": chosen["serialNumber"],
            "tconnect_device_id": chosen["tconnectDeviceId"],
            "max_date_with_events": chosen["maxDateWithEvents"],
        }
        last_event = arrow.get(chosen["maxDateWithEvents"])
        stale_days = (arrow.utcnow() - last_event).total_seconds() / 86400
        if stale_days > STALE_WARN_DAYS:
            log.warning(
                "Selected pump serial=%s last uploaded %.1f days ago — sync may be paused upstream",
                chosen["serialNumber"], stale_days,
            )

        end = arrow.utcnow()
        start = end.shift(hours=-window_hours)
        events = list(
            api.tandemsource.pump_events(
                chosen["tconnectDeviceId"], min_date=start, max_date=end
            )
        )
        if not events:
            return [], []

        basal_rows = _parse_basal(events, end)
        bolus_rows = _parse_bolus(events)
        return basal_rows, bolus_rows
    except Exception:
        log.exception("Tandem Source poll failed")
        return None


def get_active_pump() -> dict | None:
    """Read-only accessor for /health to report which pump is being polled."""
    return _active_pump


async def poll_tandem() -> None:
    global _needs_backfill

    if not settings.TANDEM_EMAIL or not settings.TANDEM_PASSWORD:
        log.debug("Tandem credentials not configured — skipping poll")
        return

    window_hours = BACKFILL_HOURS if _needs_backfill else STEADY_HOURS
    result = await asyncio.get_event_loop().run_in_executor(
        None, _fetch_sync, window_hours
    )

    if result is None:
        # Error already logged; keep backfill flag so next poll retries wide window.
        return

    basal_rows, bolus_rows = result
    _needs_backfill = False

    if not basal_rows and not bolus_rows:
        log.debug("Tandem poll returned no events")
        return

    async with AsyncSessionLocal() as session:
        if basal_rows:
            stmt = pg_insert(BasalEvent).values(basal_rows).on_conflict_do_nothing(
                index_elements=["event_id"]
            )
            await session.execute(stmt)
        if bolus_rows:
            stmt = pg_insert(BolusEvent).values(bolus_rows).on_conflict_do_nothing(
                index_elements=["event_id"]
            )
            await session.execute(stmt)
        await session.commit()

    log.info(
        "Tandem upsert: %d basal, %d bolus", len(basal_rows), len(bolus_rows)
    )
