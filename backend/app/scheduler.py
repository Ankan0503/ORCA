"""A tiny daily scheduler for the INCOIS PFZ refresh.

INCOIS publishes each advisory the afternoon before its forecast day, so ORCA
re-scrapes once a day at a configured local (IST) time — 17:00 by default, set
in :class:`app.config.Settings`. This is deliberately dependency-free: one
asyncio task that sleeps until the next run time and calls
:func:`app.tools.pfz.refresh_all`. The per-day cache is the safety net — even if
this task never fired, the first visitor on a new date would still trigger a
fetch — so the scheduler only has to make the common case (a warm cache before
anyone asks) happen on its own.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, time, timedelta, timezone

from .config import Settings
from .tools import pfz

logger = logging.getLogger("orca.pfz.scheduler")

# INCOIS operates on India Standard Time, which has no daylight saving, so a
# fixed +5:30 offset is exact all year.
IST = timezone(timedelta(hours=5, minutes=30))


def _seconds_until_next_run(hour: int, minute: int, now_ist: datetime) -> float:
    """Seconds from now until the next occurrence of hour:minute in IST."""
    target = datetime.combine(now_ist.date(), time(hour, minute), tzinfo=IST)
    if target <= now_ist:
        target += timedelta(days=1)
    return (target - now_ist).total_seconds()


async def _run_forever(settings: Settings) -> None:
    hour = settings.pfz_refresh_hour_ist
    minute = settings.pfz_refresh_minute_ist

    # Warm the cache once at startup so the first user never waits on a cold
    # scrape, and today's advisory is on the map immediately.
    try:
        report = await pfz.refresh_all(force=True)
        logger.info("PFZ startup refresh: %s", report)
    except Exception:  # noqa: BLE001 — a bad scrape must not crash the server
        logger.exception("PFZ startup refresh failed")

    while True:
        delay = _seconds_until_next_run(hour, minute, datetime.now(IST))
        logger.info("Next PFZ refresh in %.0f min (at %02d:%02d IST)", delay / 60, hour, minute)
        await asyncio.sleep(delay)

        # INCOIS sometimes uploads with a 15-60 min delay. Retry up to 8 times (every 15 min)
        # until today's bulletin is confirmed published, then sleep until tomorrow.
        for attempt in range(8):
            try:
                status = await pfz.fetch_forecast_status(force=True)
                report = await pfz.refresh_all(force=True)
                logger.info("PFZ daily refresh: %s", report)

                now_ist = datetime.now(IST)
                today_day = str(now_ist.day)
                # Check if forecast_date or valid_upto reflects today
                is_fresh = bool(
                    (status.forecast_date and today_day in status.forecast_date)
                    or (status.valid_upto and today_day in status.valid_upto)
                )
                if is_fresh or attempt == 7:
                    logger.info("PFZ refresh finalized for today: %s (valid %s)", status.forecast_date, status.valid_upto)
                    break

                logger.info(
                    "INCOIS bulletin not yet updated for %s (current: %s). Retrying in 15 min (attempt %d/8)",
                    now_ist.strftime("%d %b %Y"),
                    status.forecast_date,
                    attempt + 1,
                )
                await asyncio.sleep(900)
            except Exception:  # noqa: BLE001
                logger.exception("PFZ daily refresh attempt %d failed", attempt + 1)
                if attempt < 7:
                    await asyncio.sleep(900)


def start(settings: Settings) -> asyncio.Task | None:
    """Launch the background refresh loop, unless it is disabled in settings."""
    if not settings.pfz_scheduler_enabled:
        logger.info("PFZ scheduler disabled by configuration")
        return None
    return asyncio.create_task(_run_forever(settings), name="pfz-daily-refresh")
