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

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime

import httpx

from ..config import get_settings
from .geofence import inside_eez, is_at_sea
from .marine import FOG_CODES, THUNDERSTORM_CODES, compass

# Rain intensity bands, in mm/hour. These are ORCA's own reading of the forecast
# rather than an Indian standard, and are labelled as such wherever shown.
RAIN_LIGHT_MM = 0.5
RAIN_MODERATE_MM = 2.5
RAIN_HEAVY_MM = 7.5

# Codes that mean precipitation is falling, whatever the millimetres say.
#
# The bands above used to be the only test, so a cell reporting 0.1 mm/h with
# weather code 51 — the forecast stating in plain terms that it is drizzling —
# rendered as clear. Two signals disagreed and the quieter one won. Now the code
# establishes *that* it is precipitating and the millimetres decide only how
# hard, which is the question each is actually able to answer.
#
# WMO 4677: 51/53/55 drizzle, 56/57 freezing drizzle, 61/63/65 rain,
# 66/67 freezing rain, 80/81/82 rain showers. Thunderstorms (95/96/99) are
# handled separately because they outrank rain of any intensity.
PRECIPITATING_CODES = frozenset({51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82})

# --- How far ahead the map can honestly draw ---------------------------------
#
# Two different questions need answering and they do not share a horizon. "If I
# go out now, when must I be back?" is a twelve-hour question. "Where will it
# rain tomorrow?" is a forty-eight hour one.
#
# Resolution therefore tracks skill rather than convenience. Hourly frames for
# the first twelve hours, where a global model can still place a system; three-
# hourly out to forty-eight, where it can speak to likelihood but not position;
# and nothing at all beyond that on the map, though the data runs to 168 hours.
# Drawing a confident patch at day five would be inventing precision.
FINE_WINDOW_HOURS = 12
FINE_STEP_HOURS = 1
COARSE_STEP_HOURS = 3
HORIZON_HOURS = 48


def frame_offsets() -> list[int]:
    """Hours ahead of now that the map draws — 24 frames across 48 hours."""
    fine = list(range(0, FINE_WINDOW_HOURS, FINE_STEP_HOURS))
    coarse = list(range(FINE_WINDOW_HOURS, HORIZON_HOURS, COARSE_STEP_HOURS))
    return fine + coarse

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
class HourSlice:
    """One cell at one forecast hour."""

    hours_ahead: int
    time: str
    precipitation_mm: float | None = None
    weather_code: int | None = None
    # Ensemble-derived chance of precipitation, straight from the forecast
    # provider. Free on the request already being made, and the only honest way
    # to draw anything past the twelve-hour mark.
    probability_pct: int | None = None

    @property
    def is_thunderstorm(self) -> bool:
        return self.weather_code in THUNDERSTORM_CODES

    @property
    def rain_band(self) -> str:
        """none | light | moderate | heavy — before thunderstorms are considered."""
        mm = self.precipitation_mm
        raining = self.weather_code in PRECIPITATING_CODES
        if mm is None:
            return "light" if raining else "none"
        if mm >= RAIN_HEAVY_MM:
            return "heavy"
        if mm >= RAIN_MODERATE_MM:
            return "moderate"
        if mm >= RAIN_LIGHT_MM or raining:
            return "light"
        return "none"

    @property
    def hazard(self) -> str:
        """The single worst thing about this cell, for colouring and routing."""
        if self.is_thunderstorm:
            return "thunderstorm"
        band = self.rain_band
        if band in ("heavy", "moderate"):
            return f"{band}_rain"
        if self.weather_code in FOG_CODES:
            return "fog"
        if band == "light":
            return "light_rain"
        return "clear"


@dataclass
class SeaCell:
    """One patch of sea over the next two days.

    The scalar properties (``hazard``, ``rain_band``, ``precipitation_mm`` and
    the rest) describe the **current hour** and keep the shape every existing
    caller — the router especially — already reads. They used to describe
    ``hourly[0]``, which with a one-day request and a local timezone is midnight:
    at six in the evening the map was drawing conditions eighteen hours stale,
    and the error grew through the day.

    ``hours`` carries the rest of the window so the same fetch can drive a time
    slider without asking the provider for anything more.
    """

    latitude: float
    longitude: float
    is_sea: bool = False
    # Whether the cell lies inside India's EEZ. Rain outside it is still worth
    # seeing — weather arrives from somewhere — but currents are clipped to the
    # national limit, where they are both useful and ORCA's to speak about.
    inside_eez: bool = False
    current_speed_ms: float | None = None
    current_direction_deg: float | None = None
    hours: list[HourSlice] = field(default_factory=list)

    @property
    def now(self) -> HourSlice | None:
        """This hour, which is frame zero of the window."""
        return self.hours[0] if self.hours else None

    @property
    def precipitation_mm(self) -> float | None:
        return self.now.precipitation_mm if self.now else None

    @property
    def weather_code(self) -> int | None:
        return self.now.weather_code if self.now else None

    @property
    def is_thunderstorm(self) -> bool:
        return bool(self.now and self.now.is_thunderstorm)

    @property
    def is_fog(self) -> bool:
        return bool(self.now) and self.now.weather_code in FOG_CODES

    @property
    def rain_band(self) -> str:
        return self.now.rain_band if self.now else "none"

    @property
    def hazard(self) -> str:
        """The single worst thing about this cell right now.

        Thunderstorms outrank rain however heavy, because lightning is what
        actually kills people in open boats.
        """
        return self.now.hazard if self.now else "clear"

    @property
    def worst_ahead(self) -> str:
        """The worst hazard anywhere in the window, for a "later today" view."""
        order = ("clear", "fog", "light_rain", "moderate_rain", "heavy_rain", "thunderstorm")
        worst = "clear"
        for slice_ in self.hours:
            if order.index(slice_.hazard) > order.index(worst):
                worst = slice_.hazard
        return worst

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
        """Every existing key means what it always did, now read from this hour.

        The window is emitted as parallel arrays rather than a list of objects.
        At 24 frames across roughly 150 national sea cells the difference is
        tens of kilobytes against hundreds, which is a real cost on a phone at
        the edge of coverage and free to avoid.
        """
        return {
            "latitude": round(self.latitude, 4),
            "longitude": round(self.longitude, 4),
            "isSea": self.is_sea,
            "insideEez": self.inside_eez,
            "hazard": self.hazard,
            "rainBand": self.rain_band,
            "precipitationMm": self.precipitation_mm,
            "isThunderstorm": self.is_thunderstorm,
            "worstAhead": self.worst_ahead,
            "currentSpeedMs": self.current_speed_trusted_ms,
            "currentDirectionDeg": self.current_direction_deg,
            "currentTowards": compass(self.current_direction_deg),
            "currentSuspect": self.current_is_suspect,
            "series": {
                "hoursAhead": [h.hours_ahead for h in self.hours],
                "hazard": [h.hazard for h in self.hours],
                "precipitationMm": [h.precipitation_mm for h in self.hours],
                "probabilityPct": [h.probability_pct for h in self.hours],
            },
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
    # Three days, not one. A single day's request ends at 23:00 local, so by six
    # in the evening only six hours remained in the array and by ten, one — the
    # forward view shrank to nothing exactly as the day wore on. A 48-hour window
    # measured forward from *now* needs almost three calendar days to be sure of
    # fitting, and asking for them costs no extra request. Only the 24 frames the
    # map draws are kept, so nothing downstream grows.
    common = {"latitude": lats, "longitude": lons, "timezone": "auto", "forecast_days": 3}

    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            marine = await client.get(
                settings.open_meteo_marine_url,
                params={**common, "hourly": "ocean_current_velocity,ocean_current_direction"},
            )
            weather = await client.get(
                settings.open_meteo_forecast_url,
                params={
                    **common,
                    # precipitation_probability rides along on a request already
                    # being made, and is what lets the map say "may" past the
                    # twelve-hour mark instead of drawing a false certainty.
                    "hourly": "precipitation,weather_code,precipitation_probability",
                },
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

    def series(block: dict, key: str) -> list:
        return (block.get("hourly") or {}).get(key) or []

    def current_index(times: list[str]) -> int:
        """Where "now" sits in the returned hours.

        The hour *containing* now, not the nearest label. At 21:35 the nearest
        stamp is 22:00, and reporting the coming hour as current is a small lie
        in the same family as the midnight bug it replaced — the screen should
        describe the weather someone is standing in.

        The provider echoes local time for the requested coordinate, so the
        comparison is against local now. Falling back to zero would reintroduce
        that bug outright, so an unparseable series yields no frames at all
        rather than a confidently wrong one.
        """
        if not times:
            return -1
        now = datetime.now().replace(minute=0, second=0, microsecond=0)
        latest = -1
        for index, stamp in enumerate(times):
            try:
                when = datetime.fromisoformat(stamp)
            except ValueError:
                continue
            if when <= now:
                latest = index
            else:
                break
        # Before the series starts (a clock skewed behind the provider's day)
        # the first hour is the honest answer.
        return latest if latest >= 0 else (0 if times else -1)

    offsets = frame_offsets()
    cells: list[SeaCell] = []
    for index, (lat, lon) in enumerate(points):
        m = marine_list[index] if index < len(marine_list) else {}
        w = weather_list[index] if index < len(weather_list) else {}

        times = series(w, "time")
        precip = series(w, "precipitation")
        codes = series(w, "weather_code")
        chance = series(w, "precipitation_probability")
        base = current_index(times)

        hours: list[HourSlice] = []
        if base >= 0:
            for ahead in offsets:
                at = base + ahead
                if at >= len(times):
                    break
                hours.append(
                    HourSlice(
                        hours_ahead=ahead,
                        time=times[at],
                        precipitation_mm=precip[at] if at < len(precip) else None,
                        weather_code=codes[at] if at < len(codes) else None,
                        probability_pct=chance[at] if at < len(chance) else None,
                    )
                )

        # The current at this hour. Unlike rain it is not drawn over time, so a
        # single value is enough and the series is not carried.
        cv = series(m, "ocean_current_velocity")
        cd = series(m, "ocean_current_direction")
        mi = current_index(series(m, "time"))
        current_speed = cv[mi] if 0 <= mi < len(cv) else None
        current_dir = cd[mi] if 0 <= mi < len(cd) else None

        cells.append(
            SeaCell(
                latitude=lat,
                longitude=lon,
                # Either test is enough, because each is strong exactly where
                # the other is weak. The geometry knows the coastline, which is
                # where the ocean-current model returns nothing and where the
                # old current-only test therefore deleted the coast — the only
                # part of this map a fisherman is ever in. The current model in
                # turn answers for open water anywhere, including a neighbour's
                # EEZ, which the geometry misreads as inland whenever that water
                # sits nearer India's baselines than its own 200 NM limit —
                # Bangladeshi water off the Sundarbans, Palk Bay, the Myanmar
                # side. Rain there is still worth drawing; weather arrives from
                # somewhere.
                is_sea=is_at_sea(lat, lon) or current_speed is not None,
                inside_eez=inside_eez(lat, lon),
                current_speed_ms=current_speed,
                current_direction_deg=current_dir,
                hours=hours,
            )
        )

    _cache[key] = (time.monotonic(), cells)
    return cells


async def fetch_area(
    latitude: float,
    longitude: float,
    span_deg: float = 0.5,
    side: int = 12,
) -> list[SeaCell]:
    """Convenience: build a grid around a point and fetch it.

    The default is 0.09 degrees between samples, about 10 km, which is the
    provider's own grid resolution. It used to be 42 km — sampling an 11 km
    model at a quarter of its detail and discarding the rest, for data already
    fetched and paid for. The national layer supplies the wide view.
    """
    return await fetch_sea_grid(build_grid(latitude, longitude, span_deg, side))


# --- The whole EEZ, not just the box around one boat ------------------------
#
# The local grid answers "what is the weather where I am", which cannot answer
# "where is the weather" — a fisherman deciding whether a system is closing on
# his coast needs the national picture. India's EEZ spans roughly 6-24N and
# 68-94E including the island territories, so this box covers both seas and the
# Andamans.
NATIONAL_BOX = (6.0, 68.0, 24.0, 94.0)  # lat_min, lon_min, lat_max, lon_max

# 1.5 degrees is about 165 km. Coarse, but this layer exists to show where
# systems are, not to route through them — the local grid stays fine.
#
# The step is a quota decision as much as a resolution one. At 1 degree the box
# is over 500 points, and fetching it hard enough to matter earned a 429 from
# Open-Meteo that took the *local* grid down with it — the national picture is
# a nice-to-have, the water around the boat is not. Coarser, slower and second
# in the queue is the right trade.
NATIONAL_STEP_DEG = 1.5

# Open-Meteo takes many coordinates per request, but a 500-point URL is neither
# polite nor reliable, so the national grid is fetched in batches.
NATIONAL_BATCH = 80
# Serial, not parallel. This layer must never out-compete the local grid for
# the same rate limit.
NATIONAL_CONCURRENCY = 1
# A breath between batches, for the same reason.
NATIONAL_BATCH_PAUSE_S = 0.4

# The national picture is identical for every user, so it is cached hard: one
# fetch serves everybody until the forecast itself moves on.
_NATIONAL_TTL_SECONDS = 1800
_national_cache: tuple[float, list[SeaCell]] | None = None


def build_national_grid(step_deg: float = NATIONAL_STEP_DEG) -> list[tuple[float, float]]:
    """Every grid point across India's EEZ box."""
    lat_min, lon_min, lat_max, lon_max = NATIONAL_BOX
    points: list[tuple[float, float]] = []

    lat = lat_min
    while lat <= lat_max + 1e-9:
        lon = lon_min
        while lon <= lon_max + 1e-9:
            points.append((round(lat, 4), round(lon, 4)))
            lon += step_deg
        lat += step_deg
    return points


async def fetch_national(force: bool = False) -> list[SeaCell]:
    """Rain, storms and currents across the whole EEZ.

    Land cells are dropped before returning: they are most of the box, they
    carry no marine data, and shipping them would triple the payload for
    nothing. Batches that fail are skipped rather than failing the map — a
    partial national picture is worth more than none, and the caller can see how
    many cells came back.
    """
    global _national_cache

    if not force and _national_cache is not None:
        fetched_at, cells = _national_cache
        if (time.monotonic() - fetched_at) < _NATIONAL_TTL_SECONDS:
            return cells

    points = build_national_grid()
    batches = [
        points[i : i + NATIONAL_BATCH] for i in range(0, len(points), NATIONAL_BATCH)
    ]

    semaphore = asyncio.Semaphore(NATIONAL_CONCURRENCY)

    async def one(batch: list[tuple[float, float]]) -> list[SeaCell]:
        async with semaphore:
            try:
                return await fetch_sea_grid(batch)
            except SeaGridError:
                # A rate limit or a hiccup loses one batch, not the whole map.
                return []
            finally:
                await asyncio.sleep(NATIONAL_BATCH_PAUSE_S)

    results = await asyncio.gather(*(one(b) for b in batches))
    cells = [cell for batch in results for cell in batch if cell.is_sea]

    if cells:
        _national_cache = (time.monotonic(), cells)
    return cells


def nearest_cell(cells: list[SeaCell], latitude: float, longitude: float) -> SeaCell | None:
    """The grid cell covering a position, for hazard and current lookups."""
    if not cells:
        return None
    return min(
        cells,
        key=lambda c: (c.latitude - latitude) ** 2 + (c.longitude - longitude) ** 2,
    )
