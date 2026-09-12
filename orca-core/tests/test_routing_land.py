"""Routes stay in Indian water: the fast land test matches the exact one, and the router goes around land."""

import asyncio
import random
from dataclasses import dataclass

import pytest

from app.tools import geofence, routing


def test_banded_land_test_matches_the_exact_polygon_test():
    if not geofence.EEZ_PATH.exists():
        pytest.skip("EEZ data not present")
    rng = random.Random(7)
    points = [(rng.uniform(6.0, 24.0), rng.uniform(68.0, 94.0)) for _ in range(300)]
    points += [(21.40, 87.60), (21.6266, 87.5074), (19.70, 85.35), (9.60, 79.40)]
    for lat, lon in points:
        assert geofence.in_indian_waters(lat, lon) == geofence._inside(lat, lon)[0], (lat, lon)


@dataclass
class FakeCell:
    latitude: float
    longitude: float
    is_sea: bool = True
    hazard: str = "clear"
    current_speed_trusted_ms: float | None = None
    current_direction_deg: float | None = None


WALL_LON = 87.585  # between two grid columns, so only legs can cross it
GAP_LAT = 21.34    # the wall stops short of the top row


def _navigable(lat: float, lon: float) -> bool:
    return not (abs(lon - WALL_LON) < 0.03 and lat < GAP_LAT)


def test_route_goes_around_land_instead_of_across_it(monkeypatch):
    async def fake_grid(points):
        return [FakeCell(lat, lon) for lat, lon in points]

    monkeypatch.setattr(routing, "fetch_sea_grid", fake_grid)
    monkeypatch.setattr(routing.geofence, "is_navigable", _navigable)

    route = asyncio.run(routing.plan_route((21.0, 87.0), (21.0, 88.0)))

    assert route.legs
    assert "land" in route.avoided
    assert max(lat for lat, _ in route.waypoints) >= GAP_LAT
    for leg in route.legs:
        for k in range(21):
            lat = leg.from_lat + (leg.to_lat - leg.from_lat) * k / 20
            lon = leg.from_lon + (leg.to_lon - leg.from_lon) * k / 20
            assert _navigable(lat, lon), (lat, lon)
