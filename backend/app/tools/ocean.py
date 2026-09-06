"""Ocean productivity data: chlorophyll and sea surface temperature.

Potential Fishing Zones are not a dataset anyone publishes as an API. INCOIS
derives them from satellite sea surface temperature and chlorophyll: fish
gather where thermal fronts concentrate plankton, so a zone is worth fishing
when productive water sits next to a temperature boundary. This module gathers
the two ingredients; the agent does the reasoning.

Chlorophyll comes from NOAA CoastWatch's gap-filled VIIRS product, which fills
cloud holes — ordinary satellite chlorophyll is missing exactly when the weather
is interesting. Sea surface temperature comes from Open-Meteo, already used for
the forecasts.

Both are free and keyless.
"""

import time
from dataclasses import dataclass
from datetime import datetime
from math import atan2, cos, radians, sin, sqrt

import httpx

from ..config import get_settings


# CoastWatch rejects unidentified clients with a 403.
USER_AGENT = "ORCA-Marine/0.1 (SIH 26176 marine advisory prototype)"

# Chlorophyll is a daily satellite composite, so caching for hours is accurate
# rather than merely convenient. SST follows the forecast cadence.
_CHL_TTL_SECONDS = 6 * 3600
_SST_TTL_SECONDS = 900

_chl_cache: dict[str, tuple[float, list["GridValue"]]] = {}
_sst_cache: dict[str, tuple[float, list["GridValue"]]] = {}

EARTH_RADIUS_KM = 6371.0
_COMPASS = (
    "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
)


class OceanDataError(RuntimeError):
    """Raised when the ocean data services cannot be reached or return nothing."""


@dataclass
class GridValue:
    latitude: float
    longitude: float
    value: float
    observed_at: datetime | None = None


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance. Fuel and safety both scale with this."""
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * atan2(sqrt(a), sqrt(1 - a))


def bearing_compass(lat1: float, lon1: float, lat2: float, lon2: float) -> str:
    """Which way to steer, as a point of the compass."""
    dlon = radians(lon2 - lon1)
    y = sin(dlon) * cos(radians(lat2))
    x = cos(radians(lat1)) * sin(radians(lat2)) - sin(radians(lat1)) * cos(
        radians(lat2)
    ) * cos(dlon)
    degrees = (atan2(y, x) * 180 / 3.141592653589793 + 360) % 360
    return _COMPASS[int(degrees / 22.5 + 0.5) % 16]


async def fetch_chlorophyll_grid(
    lat_min: float,
    lat_max: float,
    lon_min: float,
    lon_max: float,
    stride: int = 8,
    timeout: float = 60.0,
) -> list[GridValue]:
    """Chlorophyll across a box, in a single request.

    ERDDAP orders latitude descending, so the range is given high to low. The
    stride subsamples the 2 km grid: at stride 8 the spacing is roughly 17 km,
    which is finer than a fishing decision needs and keeps the response small.
    """
    key = f"{lat_min:.2f},{lat_max:.2f},{lon_min:.2f},{lon_max:.2f},{stride}"
    hit = _chl_cache.get(key)
    if hit and (time.monotonic() - hit[0]) < _CHL_TTL_SECONDS:
        return hit[1]

    query = (
        f"chlor_a[(last)][(0.0)]"
        f"[({lat_max}):{stride}:({lat_min})]"
        f"[({lon_min}):{stride}:({lon_max})]"
    )

    try:
        settings = get_settings()
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(
                f"{settings.noaa_erddap_url}?{query}", headers={"User-Agent": USER_AGENT}
            )
    except httpx.HTTPError as exc:
        raise OceanDataError(f"Could not reach the chlorophyll service: {exc}") from exc

    if response.status_code >= 400:
        raise OceanDataError(
            f"Chlorophyll request failed ({response.status_code}): {response.text[:160]}"
        )

    try:
        rows = response.json()["table"]["rows"]
    except (ValueError, KeyError) as exc:
        raise OceanDataError("Chlorophyll response was not in the expected form") from exc

    values: list[GridValue] = []
    for row in rows:
        stamp, _altitude, latitude, longitude, value = row
        if value is None:
            continue
        values.append(
            GridValue(
                latitude=float(latitude),
                longitude=float(longitude),
                value=float(value),
                observed_at=datetime.fromisoformat(stamp.replace("Z", "+00:00"))
                if stamp
                else None,
            )
        )

    _chl_cache[key] = (time.monotonic(), values)
    return values


async def fetch_sst_points(
    points: list[tuple[float, float]],
    timeout: float = 60.0,
) -> list[GridValue]:
    """Sea surface temperature for many points in one request.

    Points over land come back with no temperature, which is how land is
    filtered out of the search — no coastline test required.
    """
    if not points:
        return []

    key = ";".join(f"{lat:.3f},{lon:.3f}" for lat, lon in points)
    hit = _sst_cache.get(key)
    if hit and (time.monotonic() - hit[0]) < _SST_TTL_SECONDS:
        return hit[1]

    params = {
        "latitude": ",".join(str(lat) for lat, _ in points),
        "longitude": ",".join(str(lon) for _, lon in points),
        "hourly": "sea_surface_temperature",
        "forecast_days": 1,
        "timezone": "auto",
    }

    try:
        settings = get_settings()
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(settings.open_meteo_marine_url, params=params)
    except httpx.HTTPError as exc:
        raise OceanDataError(f"Could not reach the temperature service: {exc}") from exc

    if response.status_code >= 400:
        raise OceanDataError(
            f"Temperature request failed ({response.status_code}): {response.text[:160]}"
        )

    payload = response.json()
    locations = payload if isinstance(payload, list) else [payload]

    values: list[GridValue] = []
    for (latitude, longitude), location in zip(points, locations):
        series = (location.get("hourly") or {}).get("sea_surface_temperature") or []
        current = next((v for v in series if v is not None), None)
        if current is None:
            continue  # land
        values.append(GridValue(latitude=latitude, longitude=longitude, value=float(current)))

    _sst_cache[key] = (time.monotonic(), values)
    return values


def nearest(values: list[GridValue], latitude: float, longitude: float) -> GridValue | None:
    """Closest sample to a point, used to line the two grids up."""
    if not values:
        return None
    return min(values, key=lambda v: distance_km(latitude, longitude, v.latitude, v.longitude))
