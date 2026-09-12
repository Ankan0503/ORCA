"""The route agent picks the nearest zone, plans the passage and says when to be back."""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from app.agents import route as route_module
from app.agents.base import AgentResult, QueryContext
from app.agents.ocean import OceanAnalyticsAgent
from app.agents.route import RoutePlanningAgent
from app.tools.marine import HourlyPoint, MarineConditions
from app.tools.routing import Leg, Route

IST_OFFSET = 19800
ZONE = {"latitude": 21.38, "longitude": 87.51, "label": "ORCA-estimated zone 27.8 km S", "distanceKm": 27.8}


def _local_now() -> datetime:
    local = (datetime.now(timezone.utc) + timedelta(seconds=IST_OFFSET)).replace(tzinfo=None)
    return local.replace(minute=0, second=0, microsecond=0)


def _conditions(storm_at: datetime | None) -> MarineConditions:
    start = _local_now().replace(hour=0) - timedelta(days=1)
    hours = [
        HourlyPoint(
            time=start + timedelta(hours=h),
            wave_height_m=0.5,
            wave_period_s=6.0,
            wind_speed_kmh=10.0,
            wind_gusts_kmh=15.0,
            visibility_m=10000.0,
            precipitation_mm=0.0,
            weather_code=95 if storm_at and start + timedelta(hours=h) == storm_at else 1,
        )
        for h in range(120)
    ]
    return MarineConditions(
        latitude=21.63, longitude=87.51, timezone="Asia/Kolkata",
        fetched_at=datetime.now(), hourly=hours, utc_offset_seconds=IST_OFFSET,
    )


def _route() -> Route:
    leg = Leg(
        from_lat=21.6, from_lon=87.5, to_lat=21.38, to_lon=87.51, distance_km=28.0,
        course_deg=180.0, heading_deg=182.0, speed_over_ground_kmh=14.7, hours=1.9,
        hazard="clear", current_speed_ms=None, current_towards_deg=None,
    )
    return Route(legs=[leg], total_distance_km=28.0, total_hours=1.9, avoided=["thunderstorm"], direct_km=25.0)


@pytest.fixture
def offline(monkeypatch):
    async def zones(self, context):
        return AgentResult(agent="ocean_analytics", summary="", data={"estimate": True, "zones": [ZONE]})

    async def plan(origin, destination, **kwargs):
        assert destination == (ZONE["latitude"], ZONE["longitude"])
        return _route()

    monkeypatch.setattr(OceanAnalyticsAgent, "run", zones)
    monkeypatch.setattr(route_module.routing, "plan_route", plan)

    def use(storm_at):
        async def fetch(latitude, longitude, *args, **kwargs):
            return _conditions(storm_at)

        monkeypatch.setattr(route_module, "fetch_marine_conditions", fetch)

    return use


def _run() -> AgentResult:
    context = QueryContext(question="Safe route to the nearest fishing zone", latitude=21.63, longitude=87.51)
    return asyncio.run(RoutePlanningAgent().run(context))


def test_calm_day_gives_leave_and_back_by_times(offline):
    offline(None)
    result = _run()
    assert result.error is None
    assert result.data["fitsSafeWindow"] is True
    assert "be back by" in result.summary
    assert result.data["destination"]["label"] == ZONE["label"]
    assert result.data["estimate"] is True
    assert result.data["route"]["totalDistanceKm"] == 28.0


def test_storm_before_return_says_when_to_turn_home(offline):
    offline(_local_now() + timedelta(hours=5))
    result = _run()
    assert result.data["fitsSafeWindow"] is False
    assert "turn for home by" in result.summary


def test_storm_at_departure_says_do_not_set_out(offline):
    offline(_local_now())
    result = _run()
    assert result.data["fitsSafeWindow"] is False
    assert "Do not set out" in result.summary
