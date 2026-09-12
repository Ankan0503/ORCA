"""The weather agent reads "now" and "tomorrow" off the forecast's current hour, not its first."""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from app.agents import weather as weather_module
from app.agents.base import QueryContext
from app.agents.registry import default_agents
from app.tools.marine import HourlyPoint, MarineConditions

IST_OFFSET = 19800
THUNDERSTORM = 95


def _forecast_from_yesterday(storm_at: datetime) -> MarineConditions:
    """Like the live feed: the series begins at yesterday's local midnight."""
    local = (datetime.now(timezone.utc) + timedelta(seconds=IST_OFFSET)).replace(tzinfo=None)
    start = local.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
    hours = []
    for h in range(96):
        moment = start + timedelta(hours=h)
        hours.append(
            HourlyPoint(
                time=moment,
                wave_height_m=0.5,
                wave_period_s=6.0,
                wind_speed_kmh=10.0,
                wind_gusts_kmh=15.0,
                visibility_m=10000.0,
                precipitation_mm=0.0,
                weather_code=THUNDERSTORM if moment == storm_at else 1,
            )
        )
    return MarineConditions(
        latitude=21.63,
        longitude=87.51,
        timezone="Asia/Kolkata",
        fetched_at=datetime.now(),
        hourly=hours,
        utc_offset_seconds=IST_OFFSET,
    )


def _local_midnight(days: int) -> datetime:
    local = (datetime.now(timezone.utc) + timedelta(seconds=IST_OFFSET)).replace(tzinfo=None)
    return local.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=days)


def _summary(monkeypatch, forecast: MarineConditions, when: str | None) -> str:
    async def fake_fetch(latitude, longitude, *args, **kwargs):
        return forecast

    monkeypatch.setattr(weather_module, "fetch_marine_conditions", fake_fetch)
    params = {"when": when} if when else {}
    context = QueryContext(question="Is it safe?", latitude=21.63, longitude=87.51, params=params)
    agent = next(a for a in default_agents() if a.name == "weather_intelligence")
    result = asyncio.run(agent.run(context))
    assert result.error is None
    return result.summary.lower()


def test_next_12_hours_ignores_yesterdays_storm(monkeypatch):
    yesterday_dawn = _local_midnight(-1) + timedelta(hours=5)
    assert "thunder" not in _summary(monkeypatch, _forecast_from_yesterday(yesterday_dawn), None)


@pytest.mark.parametrize("hour", [7])
def test_tomorrow_morning_is_tomorrow(monkeypatch, hour):
    tomorrow_dawn = _local_midnight(1) + timedelta(hours=hour)
    assert "thunder" in _summary(monkeypatch, _forecast_from_yesterday(tomorrow_dawn), "tomorrow_morning")
