"""Marine and weather conditions from Open-Meteo.

Two endpoints are needed and they are different services: the marine API has
waves, swell and sea surface temperature but no wind, and the forecast API has
wind, gusts, rain and visibility but no waves. Both are free and need no key,
which is why ORCA can show real conditions without any account setup.

Responses are cached briefly. Forecasts update hourly at best, so refetching on
every question would only add latency and burn a public service's goodwill.
"""

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import httpx

MARINE_URL = "https://marine-api.open-meteo.com/v1/marine"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

_CACHE_TTL_SECONDS = 900  # 15 minutes
_cache: dict[str, tuple[float, "MarineConditions"]] = {}


class MarineDataError(RuntimeError):
    """Raised when the forecast services cannot be reached or return nothing."""


@dataclass
class HourlyPoint:
    """One hour of combined sea and weather conditions."""

    time: datetime
    wave_height_m: float | None = None
    swell_height_m: float | None = None
    wave_period_s: float | None = None
    sea_temperature_c: float | None = None
    wind_speed_kmh: float | None = None
    wind_gusts_kmh: float | None = None
    precipitation_mm: float | None = None
    visibility_m: float | None = None


@dataclass
class WindowSummary:
    """The worst conditions across a slice of time, which is what safety turns on."""

    label: str
    start: datetime
    end: datetime
    max_wave_height_m: float | None = None
    max_swell_height_m: float | None = None
    max_wind_speed_kmh: float | None = None
    max_wind_gusts_kmh: float | None = None
    total_precipitation_mm: float | None = None
    min_visibility_m: float | None = None
    avg_sea_temperature_c: float | None = None
    hours: int = 0


@dataclass
class MarineConditions:
    latitude: float
    longitude: float
    timezone: str
    fetched_at: datetime
    hourly: list[HourlyPoint] = field(default_factory=list)


def _series(payload: dict[str, Any], key: str) -> list[Any]:
    return (payload.get("hourly") or {}).get(key) or []


def _combine(marine: dict[str, Any], weather: dict[str, Any]) -> MarineConditions:
    times = _series(marine, "time") or _series(weather, "time")
    if not times:
        raise MarineDataError("Forecast response contained no hourly data")

    # The two services are queried with the same coordinates and timezone, so
    # their hourly arrays line up; index by time anyway to be safe.
    weather_index = {t: i for i, t in enumerate(_series(weather, "time"))}

    def marine_at(key: str, i: int) -> float | None:
        values = _series(marine, key)
        return values[i] if i < len(values) else None

    def weather_at(key: str, stamp: str) -> float | None:
        i = weather_index.get(stamp)
        if i is None:
            return None
        values = _series(weather, key)
        return values[i] if i < len(values) else None

    points: list[HourlyPoint] = []
    for i, stamp in enumerate(times):
        points.append(
            HourlyPoint(
                time=datetime.fromisoformat(stamp),
                wave_height_m=marine_at("wave_height", i),
                swell_height_m=marine_at("swell_wave_height", i),
                wave_period_s=marine_at("wave_period", i),
                sea_temperature_c=marine_at("sea_surface_temperature", i),
                wind_speed_kmh=weather_at("wind_speed_10m", stamp),
                wind_gusts_kmh=weather_at("wind_gusts_10m", stamp),
                precipitation_mm=weather_at("precipitation", stamp),
                visibility_m=weather_at("visibility", stamp),
            )
        )

    return MarineConditions(
        latitude=marine.get("latitude") or weather.get("latitude"),
        longitude=marine.get("longitude") or weather.get("longitude"),
        timezone=marine.get("timezone") or weather.get("timezone") or "UTC",
        fetched_at=datetime.now(),
        hourly=points,
    )


async def fetch_marine_conditions(
    latitude: float,
    longitude: float,
    forecast_days: int = 3,
    timeout: float = 20.0,
) -> MarineConditions:
    """Fetch waves and weather for a point, combined into one hourly series."""
    key = f"{round(latitude, 2)},{round(longitude, 2)},{forecast_days}"
    hit = _cache.get(key)
    if hit and (time.monotonic() - hit[0]) < _CACHE_TTL_SECONDS:
        return hit[1]

    marine_params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "wave_height,wave_direction,wave_period,swell_wave_height,sea_surface_temperature",
        "timezone": "auto",
        "forecast_days": forecast_days,
    }
    weather_params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "wind_speed_10m,wind_gusts_10m,precipitation,visibility,temperature_2m",
        "timezone": "auto",
        "forecast_days": forecast_days,
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            marine_response = await client.get(MARINE_URL, params=marine_params)
            weather_response = await client.get(FORECAST_URL, params=weather_params)
    except httpx.HTTPError as exc:
        raise MarineDataError(f"Could not reach the forecast service: {exc}") from exc

    if marine_response.status_code >= 400:
        raise MarineDataError(
            f"Marine forecast failed ({marine_response.status_code}): {marine_response.text[:200]}"
        )
    if weather_response.status_code >= 400:
        raise MarineDataError(
            f"Weather forecast failed ({weather_response.status_code}): {weather_response.text[:200]}"
        )

    conditions = _combine(marine_response.json(), weather_response.json())
    _cache[key] = (time.monotonic(), conditions)
    return conditions


def summarise_window(
    conditions: MarineConditions,
    start: datetime,
    end: datetime,
    label: str,
) -> WindowSummary:
    """Reduce a time slice to its worst case.

    Safety is decided by the roughest hour in the window, not the average — a
    calm morning with one squall in it is not a calm morning.
    """
    inside = [p for p in conditions.hourly if start <= p.time <= end]

    def worst(attr: str) -> float | None:
        values = [getattr(p, attr) for p in inside if getattr(p, attr) is not None]
        return max(values) if values else None

    def gentlest(attr: str) -> float | None:
        values = [getattr(p, attr) for p in inside if getattr(p, attr) is not None]
        return min(values) if values else None

    def total(attr: str) -> float | None:
        values = [getattr(p, attr) for p in inside if getattr(p, attr) is not None]
        return round(sum(values), 1) if values else None

    def mean(attr: str) -> float | None:
        values = [getattr(p, attr) for p in inside if getattr(p, attr) is not None]
        return round(sum(values) / len(values), 1) if values else None

    return WindowSummary(
        label=label,
        start=start,
        end=end,
        max_wave_height_m=worst("wave_height_m"),
        max_swell_height_m=worst("swell_height_m"),
        max_wind_speed_kmh=worst("wind_speed_kmh"),
        max_wind_gusts_kmh=worst("wind_gusts_kmh"),
        total_precipitation_mm=total("precipitation_mm"),
        min_visibility_m=gentlest("visibility_m"),
        avg_sea_temperature_c=mean("sea_temperature_c"),
        hours=len(inside),
    )
