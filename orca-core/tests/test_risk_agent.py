"""Risk assessment runs end to end on a forecast shaped like the real one."""

import asyncio
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.agents import risk as risk_module
from app.agents.base import QueryContext
from app.agents.risk import RiskAssessmentAgent
from app.tools.closures import BanStatus
from app.tools.marine import HourlyPoint, MarineConditions

IST_OFFSET = 19800


def _conditions(wind_kmh: float | None) -> MarineConditions:
    local = datetime.now(timezone.utc) + timedelta(seconds=IST_OFFSET)
    midnight = local.replace(tzinfo=None, hour=0, minute=0, second=0, microsecond=0)
    hours = [
        HourlyPoint(
            time=midnight + timedelta(hours=h),
            wave_height_m=0.6,
            wave_period_s=6.0,
            wave_direction_deg=180.0,
            wind_speed_kmh=wind_kmh,
            wind_gusts_kmh=18.0,
            wind_direction_deg=200.0,
            visibility_m=10000.0,
            weather_code=1,
            precipitation_mm=0.0,
            air_temperature_c=29.0,
            sea_temperature_c=29.5,
        )
        for h in range(72)
    ]
    return MarineConditions(
        latitude=21.63,
        longitude=87.51,
        timezone="Asia/Kolkata",
        fetched_at=datetime.now(),
        hourly=hours,
        utc_offset_seconds=IST_OFFSET,
    )


@pytest.fixture
def offline(monkeypatch):
    def use_forecast(wind_kmh: float | None = 12.0) -> None:
        async def fake_fetch(latitude, longitude, *args, **kwargs):
            return _conditions(wind_kmh)

        monkeypatch.setattr(risk_module, "fetch_marine_conditions", fake_fetch)

    async def no_advisory(secid, language="en"):
        return SimpleNamespace(points=[], sector_name="Test")

    monkeypatch.setattr(risk_module.pfz_tool, "sector_for_location", lambda lat, lon: SimpleNamespace(secid="T"))
    monkeypatch.setattr(risk_module.pfz_tool, "get_sector_advisory", no_advisory)
    use_forecast()
    return SimpleNamespace(use_forecast=use_forecast, monkeypatch=monkeypatch)


def _run():
    context = QueryContext(question="Is it safe to go fishing?", latitude=21.63, longitude=87.51)
    return asyncio.run(RiskAssessmentAgent().run(context))


@pytest.mark.parametrize("wind_kmh", [12.0, None])
def test_risk_agent_completes_with_an_ml_verdict(offline, wind_kmh):
    offline.use_forecast(wind_kmh)
    result = _run()
    assert result.error is None
    assert any(e.label == "ML Risk Assessment" for e in result.evidence)


def test_active_fishing_ban_is_reported_not_dropped(offline):
    ban = BanStatus(
        coast="east",
        active=True,
        start=date(2026, 4, 15),
        end=date(2026, 6, 14),
        days_remaining=10,
        days_until=None,
        message="The east-coast ban is in force",
    )
    offline.monkeypatch.setattr(risk_module.closures_tool, "ban_status", lambda longitude, on=None: ban)
    result = _run()
    ban_evidence = [e for e in result.evidence if e.label == "Monsoon Fishing Ban"]
    assert ban_evidence and "east-coast ban is in force" in ban_evidence[0].note
