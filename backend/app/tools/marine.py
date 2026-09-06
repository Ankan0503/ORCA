"""Marine and weather conditions from Open-Meteo.

Two endpoints are needed and they are different services: the marine API has
waves, swell, tides and currents but no wind, and the forecast API has wind,
gusts, rain, visibility and weather codes but no waves. Both are free and need
no key, which is why ORCA can show real conditions without any account setup.

Responses are cached briefly. Forecasts update hourly at best, so refetching on
every question would only add latency and burn a public service's goodwill.
"""

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import httpx

from ..config import get_settings


MARINE_VARS = (
    "wave_height,wave_direction,wave_period,wave_peak_period,"
    "swell_wave_height,swell_wave_direction,swell_wave_period,wind_wave_height,"
    "sea_surface_temperature,sea_level_height_msl,"
    "ocean_current_velocity,ocean_current_direction"
)
FORECAST_VARS = (
    "wind_speed_10m,wind_gusts_10m,wind_direction_10m,"
    "precipitation,visibility,temperature_2m,weather_code"
)

# WMO weather codes. Thunderstorms matter more than rain to an open boat: they
# carry lightning, which is one of the biggest killers of Indian fishermen.
THUNDERSTORM_CODES = {95, 96, 99}
FOG_CODES = {45, 48}

_CACHE_TTL_SECONDS = 900  # 15 minutes
_cache: dict[str, tuple[float, "MarineConditions"]] = {}

_COMPASS = (
    "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
)


class MarineDataError(RuntimeError):
    """Raised when the forecast services cannot be reached or return nothing."""


def compass(degrees: float | None) -> str | None:
    """Turn a bearing into a point of the compass.

    A fisherman navigates by "south-westerly", not by 217 degrees.
    """
    if degrees is None:
        return None
    return _COMPASS[int((degrees % 360) / 22.5 + 0.5) % 16]


@dataclass
class HourlyPoint:
    """One hour of combined sea and weather conditions."""

    time: datetime
    wave_height_m: float | None = None
    wave_direction_deg: float | None = None
    wave_period_s: float | None = None
    swell_height_m: float | None = None
    swell_direction_deg: float | None = None
    swell_period_s: float | None = None
    wind_wave_height_m: float | None = None
    wave_peak_period_s: float | None = None
    sea_temperature_c: float | None = None
    tide_height_m: float | None = None
    current_speed_ms: float | None = None
    current_direction_deg: float | None = None
    wind_speed_kmh: float | None = None
    wind_gusts_kmh: float | None = None
    wind_direction_deg: float | None = None
    precipitation_mm: float | None = None
    visibility_m: float | None = None
    air_temperature_c: float | None = None
    weather_code: int | None = None

    @property
    def is_thunderstorm(self) -> bool:
        return self.weather_code in THUNDERSTORM_CODES

    @property
    def is_fog(self) -> bool:
        return self.weather_code in FOG_CODES


@dataclass
class TideEvent:
    time: datetime
    height_m: float
    kind: str  # "high" | "low"


@dataclass
class WindowSummary:
    """The worst conditions across a slice of time, which is what safety turns on."""

    label: str
    start: datetime
    end: datetime
    max_wave_height_m: float | None = None
    max_swell_height_m: float | None = None
    max_swell_period_s: float | None = None
    max_wind_wave_height_m: float | None = None
    wave_period_s: float | None = None
    wave_from: str | None = None
    max_wind_speed_kmh: float | None = None
    max_wind_gusts_kmh: float | None = None
    wind_from: str | None = None
    total_precipitation_mm: float | None = None
    min_visibility_m: float | None = None
    avg_sea_temperature_c: float | None = None
    avg_air_temperature_c: float | None = None
    max_current_speed_ms: float | None = None
    current_towards: str | None = None
    has_thunderstorm: bool = False
    thunderstorm_at: datetime | None = None
    has_fog: bool = False
    tides: list[TideEvent] = field(default_factory=list)
    hours: int = 0


@dataclass
class MarineConditions:
    latitude: float
    longitude: float
    timezone: str
    fetched_at: datetime
    hourly: list[HourlyPoint] = field(default_factory=list)
    sunrise: list[datetime] = field(default_factory=list)
    sunset: list[datetime] = field(default_factory=list)


def _series(payload: dict[str, Any], key: str, block: str = "hourly") -> list[Any]:
    return (payload.get(block) or {}).get(key) or []


def _combine(marine: dict[str, Any], weather: dict[str, Any]) -> MarineConditions:
    times = _series(marine, "time") or _series(weather, "time")
    if not times:
        raise MarineDataError("Forecast response contained no hourly data")

    weather_index = {t: i for i, t in enumerate(_series(weather, "time"))}

    def m(key: str, i: int) -> Any:
        values = _series(marine, key)
        return values[i] if i < len(values) else None

    def w(key: str, stamp: str) -> Any:
        i = weather_index.get(stamp)
        if i is None:
            return None
        values = _series(weather, key)
        return values[i] if i < len(values) else None

    points = [
        HourlyPoint(
            time=datetime.fromisoformat(stamp),
            wave_height_m=m("wave_height", i),
            wave_direction_deg=m("wave_direction", i),
            wave_period_s=m("wave_period", i),
            swell_height_m=m("swell_wave_height", i),
            swell_direction_deg=m("swell_wave_direction", i),
            swell_period_s=m("swell_wave_period", i),
            wind_wave_height_m=m("wind_wave_height", i),
            wave_peak_period_s=m("wave_peak_period", i),
            sea_temperature_c=m("sea_surface_temperature", i),
            tide_height_m=m("sea_level_height_msl", i),
            current_speed_ms=m("ocean_current_velocity", i),
            current_direction_deg=m("ocean_current_direction", i),
            wind_speed_kmh=w("wind_speed_10m", stamp),
            wind_gusts_kmh=w("wind_gusts_10m", stamp),
            wind_direction_deg=w("wind_direction_10m", stamp),
            precipitation_mm=w("precipitation", stamp),
            visibility_m=w("visibility", stamp),
            air_temperature_c=w("temperature_2m", stamp),
            weather_code=w("weather_code", stamp),
        )
        for i, stamp in enumerate(times)
    ]

    def parse_daily(key: str) -> list[datetime]:
        return [datetime.fromisoformat(v) for v in _series(weather, key, "daily") if v]

    return MarineConditions(
        latitude=marine.get("latitude") or weather.get("latitude"),
        longitude=marine.get("longitude") or weather.get("longitude"),
        timezone=marine.get("timezone") or weather.get("timezone") or "UTC",
        fetched_at=datetime.now(),
        hourly=points,
        sunrise=parse_daily("sunrise"),
        sunset=parse_daily("sunset"),
    )


async def fetch_marine_conditions(
    latitude: float,
    longitude: float,
    forecast_days: int = 3,
    timeout: float = 20.0,
) -> MarineConditions:
    """Fetch waves, tides and weather for a point, combined into one hourly series."""
    key = f"{round(latitude, 2)},{round(longitude, 2)},{forecast_days}"
    hit = _cache.get(key)
    if hit and (time.monotonic() - hit[0]) < _CACHE_TTL_SECONDS:
        return hit[1]

    common = {
        "latitude": latitude,
        "longitude": longitude,
        "timezone": "auto",
        "forecast_days": forecast_days,
    }

    try:
        settings = get_settings()
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            marine_response = await client.get(
                settings.open_meteo_marine_url, params={**common, "hourly": MARINE_VARS}
            )
            weather_response = await client.get(
                settings.open_meteo_forecast_url,
                params={**common, "hourly": FORECAST_VARS, "daily": "sunrise,sunset"},
            )
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


def find_tides(points: list[HourlyPoint]) -> list[TideEvent]:
    """Pick out high and low water from the sea level series.

    A turning point is an hour higher (or lower) than both its neighbours. Hourly
    samples put the time within about half an hour of true slack water, which is
    the precision a fisherman planning a launch actually needs.
    """
    usable = [p for p in points if p.tide_height_m is not None]
    events: list[TideEvent] = []

    for previous, current, following in zip(usable, usable[1:], usable[2:]):
        height = current.tide_height_m
        if height > previous.tide_height_m and height >= following.tide_height_m:
            events.append(TideEvent(current.time, round(height, 2), "high"))
        elif height < previous.tide_height_m and height <= following.tide_height_m:
            events.append(TideEvent(current.time, round(height, 2), "low"))

    return events


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

    # Direction is taken from the roughest hour rather than averaged: bearings
    # either side of north average to due south, and the hour that matters is
    # the worst one anyway.
    roughest = max(
        (p for p in inside if p.wind_speed_kmh is not None),
        key=lambda p: p.wind_speed_kmh,
        default=None,
    )
    biggest_wave = max(
        (p for p in inside if p.wave_height_m is not None),
        key=lambda p: p.wave_height_m,
        default=None,
    )
    storm = next((p for p in inside if p.is_thunderstorm), None)
    # Current direction is taken from the hour with the strongest current, for
    # the same reason wind direction is: bearings either side of north average
    # to due south, and the strongest set is the one that matters for steering.
    strongest_current = max(
        (p for p in inside if p.current_speed_ms is not None),
        key=lambda p: p.current_speed_ms,
        default=None,
    )

    return WindowSummary(
        label=label,
        start=start,
        end=end,
        max_wave_height_m=worst("wave_height_m"),
        max_swell_height_m=worst("swell_height_m"),
        max_swell_period_s=worst("swell_period_s"),
        max_wind_wave_height_m=worst("wind_wave_height_m"),
        wave_period_s=biggest_wave.wave_period_s if biggest_wave else None,
        wave_from=compass(biggest_wave.wave_direction_deg) if biggest_wave else None,
        max_wind_speed_kmh=worst("wind_speed_kmh"),
        max_wind_gusts_kmh=worst("wind_gusts_kmh"),
        wind_from=compass(roughest.wind_direction_deg) if roughest else None,
        total_precipitation_mm=total("precipitation_mm"),
        min_visibility_m=gentlest("visibility_m"),
        avg_sea_temperature_c=mean("sea_temperature_c"),
        avg_air_temperature_c=mean("air_temperature_c"),
        max_current_speed_ms=worst("current_speed_ms"),
        current_towards=compass(strongest_current.current_direction_deg)
        if strongest_current
        else None,
        has_thunderstorm=storm is not None,
        thunderstorm_at=storm.time if storm else None,
        has_fog=any(p.is_fog for p in inside),
        tides=find_tides(inside),
        hours=len(inside),
    )
