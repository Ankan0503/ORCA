"""Marine and weather conditions from Open-Meteo.

Two endpoints are needed and they are different services: the marine API has
waves, swell, tides and currents but no wind, and the forecast API has wind,
gusts, rain, visibility and weather codes but no waves. Both are free and need
no key, which is why ORCA can show real conditions without any account setup.

Responses are cached briefly. Forecasts update hourly at best, so refetching on
every question would only add latency and burn a public service's goodwill.

Neither endpoint is guaranteed to answer. Open-Meteo meters a free caller by the
day, and a shared address -- a college campus, a hackathon venue -- can exhaust
that before noon, at which point every request returns 429 until the small hours.
So each half degrades on its own rather than taking the other down with it:

  wind, rain, visibility   forecast host -> ensemble host -> last good -> refuse
  waves, swell, tides      marine host                    -> last good -> refuse

The ensemble host is the same forecast from the same models behind a separately
metered subdomain, so it is a genuine second way in rather than a guess. Waves
have no such twin, and must never quietly become nothing: a missing wave height
reads downstream as a flat calm sea, which is the one error that would make ORCA
call an unsafe day safe. Where there is nothing honest left to serve, this module
refuses, and the refusal travels up as :class:`MarineDataError`.

Whatever is served carries a :class:`SourceNote` saying which host answered and
how old the figures are, because a fisherman trusting a six-hour-old wave height
is entitled to know that is what he is looking at.
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
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

# Which ensemble to fall back to. GFS is global, so it covers the whole Indian
# EEZ, and its unsuffixed series is the control run -- the single forecast the
# plain endpoint would have returned. The thirty perturbed members ride along in
# the same response and are ignored here; nothing downstream has to change.
ENSEMBLE_MODEL = "gfs_seamless"

# WMO weather codes. Thunderstorms matter more than rain to an open boat: they
# carry lightning, which is one of the biggest killers of Indian fishermen.
THUNDERSTORM_CODES = {95, 96, 99}
FOG_CODES = {45, 48}

_CACHE_TTL_SECONDS = 900  # 15 minutes
_cache: dict[str, tuple[float, "MarineConditions"]] = {}

# The last response each half gave, kept well past the cache's own lifetime so a
# quota wall degrades the answer instead of emptying it. Half a day is the limit:
# a forecast fetched this morning still covers this afternoon, because each one
# spans three days from the hour it was fetched, but by tomorrow it describes a
# sea that has already happened.
_STALE_MAX_AGE_SECONDS = 12 * 3600
_last_good: dict[str, tuple[float, dict[str, Any]]] = {}

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


@dataclass(frozen=True)
class SourceNote:
    """Which host answered for one half of the forecast, and how fresh it is.

    Carried rather than inferred. Once there is more than one way to get the
    wind, "Open-Meteo" stops being a sufficient answer to where a number came
    from -- and a figure served from cache during an outage has to be labelled
    as such wherever it is shown, or the app is quietly claiming a freshness it
    does not have.
    """

    label: str
    #: False when this came from the stale store rather than off the wire.
    live: bool
    #: How old the figures are, in minutes. Only set when served from cache.
    age_minutes: int | None = None
    #: Why the usual source was not used, in words fit to show a person.
    detail: str | None = None

    def __str__(self) -> str:
        if self.live:
            return self.label
        age = "unknown age" if self.age_minutes is None else f"{self.age_minutes} min old"
        return f"{self.label} ({age})"


@dataclass
class MarineConditions:
    latitude: float
    longitude: float
    timezone: str
    fetched_at: datetime
    hourly: list[HourlyPoint] = field(default_factory=list)
    sunrise: list[datetime] = field(default_factory=list)
    sunset: list[datetime] = field(default_factory=list)
    #: Seconds east of UTC at the forecast location, straight from Open-Meteo.
    #: Needed because every timestamp above is naive *local* time, so the only
    #: way to know which of them is "now" is to shift the server's clock by this.
    utc_offset_seconds: int = 0
    #: Where the wind half came from. None only in tests, which build this directly.
    weather_source: SourceNote | None = None
    #: Where the wave half came from.
    marine_source: SourceNote | None = None

    @property
    def sources(self) -> tuple[SourceNote, ...]:
        return tuple(n for n in (self.weather_source, self.marine_source) if n is not None)

    @property
    def degraded(self) -> bool:
        """True when any half is cached, or came from somewhere other than first choice."""
        return any(not n.live or n.detail for n in self.sources)

    @property
    def provenance(self) -> str:
        """One line naming every source, for showing beside the figures."""
        return "; ".join(str(n) for n in self.sources) or "Open-Meteo"

    @property
    def local_now(self) -> datetime:
        """The current hour at the forecast location, as a naive local time.

        Every timestamp in :attr:`hourly` is local to the sea being forecast,
        and the array starts at local midnight — so the first element is *not*
        now, it is however many hours ago the day began. Reading conditions off
        ``hourly[0]`` told a fisherman at 22:00 what the morning had been like.

        Falls back to the start of the series when the clock lands before it,
        and to the last hour when the forecast has run out.
        """
        wall = datetime.now(timezone.utc) + timedelta(seconds=self.utc_offset_seconds)
        current = wall.replace(tzinfo=None, minute=0, second=0, microsecond=0)
        if not self.hourly:
            return current
        return min(max(current, self.hourly[0].time), self.hourly[-1].time)

    def index_at(self, moment: datetime) -> int:
        """Index of the first hour at or after ``moment``, clamped to the array."""
        for i, point in enumerate(self.hourly):
            if point.time >= moment:
                return i
        return max(0, len(self.hourly) - 1)


def _series(payload: dict[str, Any], key: str, block: str = "hourly") -> list[Any]:
    return (payload.get(block) or {}).get(key) or []


def _combine(
    marine: dict[str, Any],
    weather: dict[str, Any],
    weather_source: SourceNote | None = None,
    marine_source: SourceNote | None = None,
) -> MarineConditions:
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
        utc_offset_seconds=int(
            marine.get("utc_offset_seconds") or weather.get("utc_offset_seconds") or 0
        ),
        weather_source=weather_source,
        marine_source=marine_source,
    )


class _HalfUnavailable(RuntimeError):
    """One half of the forecast could not be fetched. Caught; never raised outward."""


def _why(response: "httpx.Response | None") -> str:
    """Why a request did not yield usable data, in words worth showing a person."""
    if response is None:
        return "the service could not be reached"
    if response.status_code == 429:
        # Worth naming precisely: this is the failure ORCA actually meets, and it
        # is not a fault in the app. Open-Meteo's own wording says to try tomorrow.
        return "429, the free daily request limit for this address is spent"
    return f"HTTP {response.status_code}: {response.text[:120]}"


async def _get(
    client: httpx.AsyncClient, url: str, params: dict[str, Any]
) -> "httpx.Response | None":
    """One GET, retried once on a server error. None if it could not be reached.

    Retried on 5xx only: Open-Meteo answers "503 overloaded" in short bursts and a
    second attempt usually lands, but a 429 means the day's allowance is gone and
    asking again neither helps nor is polite.
    """
    for attempt in (1, 2):
        try:
            response = await client.get(url, params=params)
        except httpx.HTTPError:
            if attempt == 2:
                return None
        else:
            if response.status_code < 500 or attempt == 2:
                return response
        await asyncio.sleep(1.0)
    return None


async def _fetch_weather(
    client: httpx.AsyncClient, common: dict[str, Any]
) -> tuple[dict[str, Any], SourceNote]:
    """Wind, rain, visibility and weather codes, from whichever host will answer."""
    settings = get_settings()
    params = {**common, "hourly": FORECAST_VARS, "daily": "sunrise,sunset"}

    response = await _get(client, settings.open_meteo_forecast_url, params)
    if response is not None and response.status_code < 400:
        return response.json(), SourceNote("Open-Meteo forecast", live=True)
    refusal = _why(response)

    # The same forecast, from the same models, behind a subdomain metered on its
    # own. Its unsuffixed series is the control run -- precisely what the plain
    # endpoint would have returned -- so the parser below needs no special case;
    # only the note changes, and it says plainly that this is what happened.
    # The unit is stated outright because the control run has to arrive in the
    # units the primary would have used, not in whatever the host defaults to.
    spare = await _get(
        client,
        settings.open_meteo_ensemble_url,
        {**params, "models": ENSEMBLE_MODEL, "wind_speed_unit": "kmh"},
    )
    if spare is not None and spare.status_code < 400:
        return spare.json(), SourceNote(
            "Open-Meteo ensemble, GFS control run",
            live=True,
            detail=f"the forecast endpoint refused: {refusal}",
        )

    raise _HalfUnavailable(refusal)


async def _fetch_marine(
    client: httpx.AsyncClient, common: dict[str, Any]
) -> tuple[dict[str, Any], SourceNote]:
    """Waves, swell, tides and currents.

    One host only. No free service publishes global wave forecasts the way the
    ensemble host publishes wind, so when this fails the choice is the last good
    response or nothing -- and nothing is the honest answer, never zeroes.
    """
    response = await _get(
        client, get_settings().open_meteo_marine_url, {**common, "hourly": MARINE_VARS}
    )
    if response is not None and response.status_code < 400:
        return response.json(), SourceNote("Open-Meteo Marine", live=True)
    raise _HalfUnavailable(_why(response))


def _resolve(
    result: "tuple[dict[str, Any], SourceNote] | BaseException",
    store_key: str,
    what: str,
    label: str,
) -> tuple[dict[str, Any], SourceNote]:
    """Take what was fetched, or the last good copy of it, or refuse.

    Refusing is a real outcome here. Serving a half as empty would be worse than
    serving nothing: absent numbers are read downstream as calm, so an outage
    would present itself as good weather.
    """
    if not isinstance(result, BaseException):
        return result

    held = _last_good.get(store_key)
    if held is None:
        raise MarineDataError(f"{what} unavailable ({result}), and nothing cached to fall back on")

    stored_at, payload = held
    age = time.time() - stored_at
    if age > _STALE_MAX_AGE_SECONDS:
        raise MarineDataError(
            f"{what} unavailable ({result}), and the last copy is "
            f"{age / 3600:.0f} hours old -- too stale to stand in for now"
        )

    return payload, SourceNote(
        f"{label}, cached",
        live=False,
        age_minutes=int(age / 60),
        detail=f"fetched earlier because the service is unavailable now: {result}",
    )


async def fetch_marine_conditions(
    latitude: float,
    longitude: float,
    forecast_days: int = 3,
    timeout: float = 20.0,
) -> MarineConditions:
    """Fetch waves, tides and weather for a point, combined into one hourly series.

    Raises :class:`MarineDataError` only when a half is both unfetchable and
    uncached. Anything it does return says where it came from; see
    :attr:`MarineConditions.provenance`.
    """
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

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        # Together, and with failures held rather than raised: the halves are
        # independent services and one being rate-limited is no reason to go
        # without the other. Gathering them also halves the wait.
        marine_result, weather_result = await asyncio.gather(
            _fetch_marine(client, common),
            _fetch_weather(client, common),
            return_exceptions=True,
        )

    # Bank every half that answered before judging any of them. Resolving one at
    # a time threw away a good response when the *other* half was the one that
    # failed, so a fetch that had already succeeded had to be made again.
    marine_key, weather_key = f"marine:{key}", f"weather:{key}"
    for result, store_key in ((marine_result, marine_key), (weather_result, weather_key)):
        if not isinstance(result, BaseException):
            _last_good[store_key] = (time.time(), result[0])

    marine_payload, marine_note = _resolve(
        marine_result, marine_key, "Marine forecast", "Open-Meteo Marine"
    )
    weather_payload, weather_note = _resolve(
        weather_result, weather_key, "Weather forecast", "Open-Meteo forecast"
    )

    conditions = _combine(marine_payload, weather_payload, weather_note, marine_note)
    # Only a fully live answer earns the short-lived cache. A degraded one is
    # left out so the next question retries the real service rather than being
    # served stale figures for another fifteen minutes.
    if not conditions.degraded:
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
