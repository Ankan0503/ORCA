"""A grid of sea conditions over an area, rather than at a single point.

Everything else in ORCA asks "what is it like *here*". That is enough to judge
whether to go out, and useless for deciding *which way to go*. Three questions
need an area:

- Where is the heavy rain and lightning on the sea right now?
- Which way is the current setting, and how hard?
- Is there a way around the weather to reach the fishing ground?

This module answers all three from one grid, because they come from the same two
Open-Meteo endpoints and the router needs them aligned cell-for-cell anyway. The
multi-point query pattern is the same one `ocean.py` already uses for sea surface
temperature: a list of coordinates in a single request, not one request per cell.

Cells over land come back with no marine data, which is how land is identified
here — the same trick `fetch_sst_points` relies on, and the reason no coastline
file is needed for the *hazard* layer (the router does need one; see the
navigation work).

A caution about currents, learned by checking rather than assuming: the
*direction* Open-Meteo reports agrees with published monsoon climatology on both
coasts, but *speeds* close to shore can read implausibly high (3+ m/s off
Chennai, where a surface current of 1-1.5 m/s would be typical), and Open-Meteo's
own documentation warns that current accuracy "is limited in coastal areas". So
speeds are capped before anything downstream steers by them, and the cap is
reported rather than hidden.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import httpx

from ..config import get_settings
from .marine import FOG_CODES, THUNDERSTORM_CODES, compass

# Rain intensity bands, in mm/hour. These are ORCA's own reading of the forecast
# rather than an Indian standard, and are labelled as such wherever shown.
RAIN_LIGHT_MM = 0.5
RAIN_MODERATE_MM = 2.5
RAIN_HEAVY_MM = 7.5

# The plausibility ceiling for a surface current, from the coastal-accuracy
# caveat above. Anything beyond this is reported as suspect instead of steered by.
CURRENT_PLAUSIBLE_MAX_MS = 2.0

_CACHE_TTL_SECONDS = 900
_cache: dict[str, tuple[float, list["SeaCell"]]] = {}

# Open-Meteo accepts many coordinates per request, but politeness and response
# size both argue for a ceiling. 12x12 covers a day's steaming in either
# direction at a resolution finer than any routing decision needs.
MAX_GRID_SIDE = 12


class SeaGridError(RuntimeError):
    """Raised when the grid cannot be fetched."""


@dataclass
class SeaCell:
    """One patch of sea, with the hazards and the current in it."""

    latitude: float
    longitude: float
    # None when the cell is over land, or the field is unavailable there.
    precipitation_mm: float | None = None
    weather_code: int | None = None
    current_speed_ms: float | None = None
    current_direction_deg: float | None = None
    is_sea: bool = False

    @property
    def is_thunderstorm(self) -> bool:
        return self.weather_code in THUNDERSTORM_CODES

    @property
    def is_fog(self) -> bool:
        return self.weather_code in FOG_CODES

    @property
    def rain_band(self) -> str:
        """none | light | moderate | heavy — before thunderstorms are considered."""
        mm = self.precipitation_mm
        if mm is None or mm < RAIN_LIGHT_MM:
            return "none"
        if mm < RAIN_MODERATE_MM:
            return "light"
        if mm < RAIN_HEAVY_MM:
            return "moderate"
        return "heavy"

    @property
    def hazard(self) -> str:
        """The single worst thing about this cell, for colouring and routing.

        Thunderstorms outrank rain however heavy, because lightning is what
        actually kills people in open boats.
        """
        if self.is_thunderstorm:
            return "thunderstorm"
        band = self.rain_band
        if band in ("heavy", "moderate"):
            return f"{band}_rain"
        if self.is_fog:
            return "fog"
        if band == "light":
            return "light_rain"
        return "clear"

    @property
    def current_speed_trusted_ms(self) -> float | None:
        """Current speed, capped at what a surface current can plausibly be."""
        if self.current_speed_ms is None:
            return None
        return min(self.current_speed_ms, CURRENT_PLAUSIBLE_MAX_MS)

    @property
    def current_is_suspect(self) -> bool:
        return (
            self.current_speed_ms is not None
            and self.current_speed_ms > CURRENT_PLAUSIBLE_MAX_MS
        )

    def to_dict(self) -> dict:
        return {
            "latitude": round(self.latitude, 4),
            "longitude": round(self.longitude, 4),
            "isSea": self.is_sea,
            "hazard": self.hazard,
            "rainBand": self.rain_band,
            "precipitationMm": self.precipitation_mm,
            "isThunderstorm": self.is_thunderstorm,
            "currentSpeedMs": self.current_speed_trusted_ms,
            "currentDirectionDeg": self.current_direction_deg,
            "currentTowards": compass(self.current_direction_deg),
            "currentSuspect": self.current_is_suspect,
        }


def build_grid(
    latitude: float,
    longitude: float,
    span_deg: float = 1.0,
    side: int = 9,
) -> list[tuple[float, float]]:
    """A square of coordinates centred on a point."""
    side = max(2, min(side, MAX_GRID_SIDE))
    lat_min, lat_max = latitude - span_deg, latitude + span_deg
    lon_min, lon_max = longitude - span_deg, longitude + span_deg
    return [
        (
            round(lat_min + (lat_max - lat_min) * i / (side - 1), 4),
            round(lon_min + (lon_max - lon_min) * j / (side - 1), 4),
        )
        for i in range(side)
        for j in range(side)
    ]


async def fetch_sea_grid(
    points: list[tuple[float, float]],
    timeout: float = 60.0,
) -> list[SeaCell]:
    """Rain, storms and currents for every point, in two requests.

    Marine and weather are separate Open-Meteo services, so one request each —
    not one per cell. Results are cached for the forecast's own cadence.
    """
    if not points:
        return []

    key = f"{len(points)}|{points[0]}|{points[-1]}"
    hit = _cache.get(key)
    if hit and (time.monotonic() - hit[0]) < _CACHE_TTL_SECONDS:
        return hit[1]

    lats = ",".join(str(lat) for lat, _ in points)
    lons = ",".join(str(lon) for _, lon in points)
    common = {"latitude": lats, "longitude": lons, "timezone": "auto", "forecast_days": 1}

    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            marine = await client.get(
                settings.open_meteo_marine_url,
                params={**common, "hourly": "ocean_current_velocity,ocean_current_direction"},
            )
            weather = await client.get(
                settings.open_meteo_forecast_url,
                params={**common, "hourly": "precipitation,weather_code"},
            )
    except httpx.HTTPError as exc:
        raise SeaGridError(f"Could not reach the forecast service: {exc}") from exc

    if marine.status_code >= 400 or weather.status_code >= 400:
        raise SeaGridError(
            f"Grid request failed (marine {marine.status_code}, weather {weather.status_code})"
        )

    marine_list = marine.json()
    weather_list = weather.json()
    if isinstance(marine_list, dict):
        marine_list = [marine_list]
    if isinstance(weather_list, dict):
        weather_list = [weather_list]

    def first(block: dict, key: str) -> float | int | None:
        series = (block.get("hourly") or {}).get(key) or []
        return next((v for v in series if v is not None), None)

    cells: list[SeaCell] = []
    for index, (lat, lon) in enumerate(points):
        m = marine_list[index] if index < len(marine_list) else {}
        w = weather_list[index] if index < len(weather_list) else {}

        current_speed = first(m, "ocean_current_velocity")
        current_dir = first(m, "ocean_current_direction")
        cells.append(
            SeaCell(
                latitude=lat,
                longitude=lon,
                precipitation_mm=first(w, "precipitation"),
                weather_code=first(w, "weather_code"),
                current_speed_ms=current_speed,
                current_direction_deg=current_dir,
                # A cell the marine model answers for is sea; land returns nothing.
                is_sea=current_speed is not None,
            )
        )

    _cache[key] = (time.monotonic(), cells)
    return cells


async def fetch_area(
    latitude: float,
    longitude: float,
    span_deg: float = 1.0,
    side: int = 9,
) -> list[SeaCell]:
    """Convenience: build a grid around a point and fetch it."""
    return await fetch_sea_grid(build_grid(latitude, longitude, span_deg, side))


def nearest_cell(cells: list[SeaCell], latitude: float, longitude: float) -> SeaCell | None:
    """The grid cell covering a position, for hazard and current lookups."""
    if not cells:
        return None
    return min(
        cells,
        key=lambda c: (c.latitude - latitude) ** 2 + (c.longitude - longitude) ** 2,
    )
