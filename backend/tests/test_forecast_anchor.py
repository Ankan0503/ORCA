"""Tests for which hour of the forecast counts as "now".

Open-Meteo returns its hourly array starting at local midnight, so the first
element is not the current hour — it is however many hours ago the day began.
Reading conditions off ``hourly[0]`` meant that somebody opening ORCA at 22:00
was shown the morning: a verdict eight hours out of date, wearing a live
timestamp, on the three screens that decide whether a boat goes out.

That is the kind of failure nobody notices in testing, because it is invisible
before noon and silently wrong after it. So the anchor is pinned here.
"""

from datetime import datetime, timedelta, timezone

from app.tools.marine import HourlyPoint, MarineConditions

IST_OFFSET = 5 * 3600 + 30 * 60


def _day_of_hours(day: datetime, offset: int = IST_OFFSET) -> MarineConditions:
    """A forecast shaped like Open-Meteo's: 72 hours from local midnight."""
    midnight = day.replace(hour=0, minute=0, second=0, microsecond=0)
    return MarineConditions(
        latitude=21.6272,
        longitude=87.5079,
        timezone="Asia/Kolkata",
        fetched_at=datetime.now(),
        hourly=[HourlyPoint(time=midnight + timedelta(hours=h)) for h in range(72)],
        utc_offset_seconds=offset,
    )


def _local_today(offset: int = IST_OFFSET) -> datetime:
    return (datetime.now(timezone.utc) + timedelta(seconds=offset)).replace(tzinfo=None)


def test_local_now_is_the_current_hour_not_the_start_of_the_array():
    local = _local_today()
    conditions = _day_of_hours(local)

    assert conditions.local_now == local.replace(minute=0, second=0, microsecond=0)
    # The regression itself: only true at midnight, and that is the point.
    if local.hour != 0:
        assert conditions.local_now != conditions.hourly[0].time


def test_local_now_follows_the_forecast_location_not_the_server():
    """Two places, one server clock, two different current hours."""
    local_ist = _local_today(IST_OFFSET)
    ist = _day_of_hours(local_ist, IST_OFFSET)

    # UTC-8, so 13.5 hours behind India.
    offset_pst = -8 * 3600
    pst = _day_of_hours(_local_today(offset_pst), offset_pst)

    delta = abs((ist.local_now - pst.local_now).total_seconds())
    # Same instant, different local hour — the gap is the offset difference,
    # give or take the hour flooring on either side.
    assert abs(delta - (IST_OFFSET - offset_pst)) <= 3600


def test_local_now_is_clamped_to_the_forecast_it_has():
    """A forecast that has run out must not index past its own end."""
    stale = _day_of_hours(_local_today() - timedelta(days=10))
    assert stale.local_now == stale.hourly[-1].time

    future = _day_of_hours(_local_today() + timedelta(days=10))
    assert future.local_now == future.hourly[0].time


def test_index_at_finds_the_first_hour_at_or_after_a_moment():
    conditions = _day_of_hours(_local_today())
    target = conditions.hourly[30].time

    assert conditions.index_at(target) == 30
    assert conditions.index_at(target - timedelta(minutes=1)) == 30
    assert conditions.index_at(target + timedelta(minutes=1)) == 31
    # Past the end, it clamps rather than raising.
    assert conditions.index_at(target + timedelta(days=30)) == len(conditions.hourly) - 1


def test_empty_forecast_does_not_explode():
    empty = MarineConditions(
        latitude=0.0,
        longitude=0.0,
        timezone="UTC",
        fetched_at=datetime.now(),
        hourly=[],
        utc_offset_seconds=0,
    )
    assert empty.local_now.minute == 0
    assert empty.index_at(datetime.now()) == 0
