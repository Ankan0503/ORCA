"""Multi-year ocean history for one place, and the trend through it.

The problem statement's own list of user questions ends with one nothing else in
ORCA can approach: *"Why has fish productivity declined in this region?"* Every
other agent reasons about now and the next few days. This one reasons across
years.

**What this can and cannot say, stated plainly, because the distinction is the
whole integrity of the feature.** ORCA holds no catch records. There is no
landing data, no CPUE series, no fisheries census in this project. So nothing
here may claim that fish productivity has declined — that would be exactly the
invented figure this codebase has spent its time removing. What it can do is
report, from the observational record, *what the water has actually done* over
the past decade at a given place, and name the mechanisms by which those changes
are known to affect productivity. The conclusion is left to the reader, and the
agent says so out loud.

Four measurements, each from a source that publishes a real historical record:

- **Sea surface temperature** — NOAA Geo-Polar Blended SST Analysis via ERDDAP.
  Warming surface water strengthens stratification, which is what stops nutrients
  from below reaching the sunlit layer where plankton grow.
- **Wind speed** — ERA5 reanalysis via Open-Meteo's archive. Wind is the engine
  of that mixing; weaker wind means a more stable, more nutrient-starved surface.
- **Rainfall** — ERA5. In the Bay of Bengal specifically, monsoon runoff caps the
  sea with a fresh, buoyant lens that suppresses mixing independently of heat.
  This is a regional mechanism, not a generic one.
- **Wave height** — ERA5-Ocean via Open-Meteo's marine API, as a second,
  independent record of how hard the sea has been worked.

Comparison is like-for-like: the same calendar window in every year, so a
September is only ever compared against other Septembers. Comparing a year to
date against a full-year average would manufacture a trend out of the seasons.

**Sources that were tested and rejected**, so nobody repeats the search:
Open-Meteo's archive and marine APIs both accept ``sea_surface_temperature`` for
historical dates and return a full array of nulls — the variable is advertised
and not served. NOAA's OISST v2.1 aggregate (``ncdcOisst21Agg``, the longer
1981-present record, which would have been the better baseline) is served from
``coastwatch.pfeg.noaa.gov``, which refuses connections here. The blended
analysis used instead begins 2019-07-22, so the SST baseline is shorter than the
wind and rain baselines and is reported with that limit attached.
"""

from __future__ import annotations

import asyncio
import statistics
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

import httpx

USER_AGENT = "ORCA/0.1 (marine advisory; contact via project repository)"

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
MARINE_URL = "https://marine-api.open-meteo.com/v1/marine"
SST_URL = "https://coastwatch.noaa.gov/erddap/griddap/noaacwBLENDEDsstDNDaily.json"

#: The blended SST analysis does not exist before this date.
SST_RECORD_STARTS = date(2019, 7, 22)

#: Days either side of today's calendar date that make up the seasonal window.
#: A month-wide window smooths weather out of the comparison while staying
#: firmly inside one season.
WINDOW_DAYS = 15

#: How many past years to compare against by default.
DEFAULT_YEARS = 10

#: ERA5 lags real time by about five days, so the most recent window is trimmed.
ERA5_LAG_DAYS = 6

SOURCES = {
    "sst": "NOAA Geo-Polar Blended SST Analysis (ERDDAP, 5 km daily)",
    "wind": "ERA5 reanalysis via Open-Meteo Archive API",
    "rain": "ERA5 reanalysis via Open-Meteo Archive API",
    "wave": "ERA5-Ocean via Open-Meteo Marine API",
}


class HistoryDataError(RuntimeError):
    """A historical record could not be read. Never silently substituted."""


@dataclass
class MetricTrend:
    """One measurement's yearly values and the line through them."""

    key: str
    label: str
    unit: str
    source: str
    #: {year: seasonal mean}, only years that actually returned data.
    by_year: dict[int, float] = field(default_factory=dict)
    #: Change per decade from a least-squares fit. None when too few years.
    slope_per_decade: float | None = None
    #: This year's value minus the mean of the earlier years.
    anomaly: float | None = None
    baseline: float | None = None
    latest: float | None = None
    first_year: int | None = None
    last_year: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "unit": self.unit,
            "source": self.source,
            "byYear": [{"year": y, "value": round(v, 3)} for y, v in sorted(self.by_year.items())],
            "slopePerDecade": None if self.slope_per_decade is None else round(self.slope_per_decade, 3),
            "anomaly": None if self.anomaly is None else round(self.anomaly, 3),
            "baseline": None if self.baseline is None else round(self.baseline, 3),
            "latest": None if self.latest is None else round(self.latest, 3),
            "firstYear": self.first_year,
            "lastYear": self.last_year,
        }


@dataclass
class SeasonHistory:
    latitude: float
    longitude: float
    window_label: str
    metrics: list[MetricTrend] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "location": {"latitude": self.latitude, "longitude": self.longitude},
            "window": self.window_label,
            "metrics": [m.to_dict() for m in self.metrics],
            "notes": self.notes,
        }


def _shift_year(anchor: date, years_back: int) -> date:
    """The same calendar day, that many years earlier."""
    try:
        return anchor.replace(year=anchor.year - years_back)
    except ValueError:  # 29 February in a non-leap year
        return anchor.replace(year=anchor.year - years_back, day=28)


def _windows(years: int, today: date) -> list[tuple[int, date, date]]:
    """One identical calendar window per year, newest last.

    Every year gets the *same* span of the same months. That sounds obvious and
    is the single easiest thing to get wrong here: the obvious implementation
    centres the window on today and clips the current year to whatever has been
    published, which leaves this year with eleven days of late August while
    every earlier year gets thirty-one days running into September. Off Bengal
    that is the difference between peak monsoon and the easing after it, and it
    produced a fabricated anomaly of +10 km/h of wind and +15 mm/day of rain —
    a trend made entirely out of the calendar.

    So the window is anchored to the end instead: it finishes at the most recent
    day ERA5 has actually published and runs back a fixed span, and those two
    month-and-day pairs are then applied unchanged to every year.
    """
    end_current = today - timedelta(days=ERA5_LAG_DAYS)
    start_current = end_current - timedelta(days=2 * WINDOW_DAYS)

    out: list[tuple[int, date, date]] = []
    for offset in range(years, -1, -1):
        start = _shift_year(start_current, offset)
        end = _shift_year(end_current, offset)
        # The window can straddle New Year; shifting both ends by the same
        # number of years keeps its width either way.
        out.append((end.year, start, end))
    return out


def _fit_slope_per_decade(by_year: dict[int, float]) -> float | None:
    """Least-squares change per decade. None when there is too little to fit."""
    if len(by_year) < 4:
        return None
    xs = list(by_year.keys())
    ys = [by_year[x] for x in xs]
    mean_x = statistics.fmean(xs)
    mean_y = statistics.fmean(ys)
    denominator = sum((x - mean_x) ** 2 for x in xs)
    if denominator == 0:
        return None
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / denominator
    return slope * 10.0


def _mean(values: list[Any]) -> float | None:
    numbers = [v for v in values if isinstance(v, (int, float))]
    return statistics.fmean(numbers) if numbers else None


async def _no_sst() -> None:
    """Stand-in when no SST cell could be resolved, so gather() stays uniform."""
    return None


async def _get_json(client: httpx.AsyncClient, url: str, params: dict[str, Any]) -> dict:
    response = await client.get(url, params=params, headers={"User-Agent": USER_AGENT})
    response.raise_for_status()
    return response.json()


async def _era5_window(
    client: httpx.AsyncClient, lat: float, lon: float, start: date, end: date
) -> tuple[float | None, float | None]:
    """Mean wind speed and total-to-mean daily rainfall for one window."""
    payload = await _get_json(
        client,
        ARCHIVE_URL,
        {
            "latitude": lat,
            "longitude": lon,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "daily": "wind_speed_10m_mean,precipitation_sum",
            "timezone": "auto",
        },
    )
    daily = payload.get("daily") or {}
    return _mean(daily.get("wind_speed_10m_mean") or []), _mean(
        daily.get("precipitation_sum") or []
    )


async def _wave_window(
    client: httpx.AsyncClient, lat: float, lon: float, start: date, end: date
) -> float | None:
    payload = await _get_json(
        client,
        MARINE_URL,
        {
            "latitude": lat,
            "longitude": lon,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "daily": "wave_height_max",
            "models": "era5_ocean",
            "timezone": "auto",
        },
    )
    return _mean((payload.get("daily") or {}).get("wave_height_max") or [])


async def _sst_window(
    client: httpx.AsyncClient,
    gate: asyncio.Semaphore,
    lat: float,
    lon: float,
    start: date,
    end: date,
) -> float | None:
    """Mean SST for one window, or None when the record does not reach back.

    Serialised behind its own gate and retried once. Every year answers fine on
    its own, but eleven of them arriving together made ERDDAP drop most of the
    requests — which came back as two years of data out of eight and looked
    exactly like a patchy satellite record rather than the rate limit it was.
    A thin record and a throttled one are indistinguishable downstream, so the
    fix belongs here.
    """
    if end < SST_RECORD_STARTS:
        return None
    start = max(start, SST_RECORD_STARTS)

    # ERDDAP wants its constraints inline, not as query parameters.
    query = (
        f"analysed_sst[({start.isoformat()}):1:({end.isoformat()})]"
        f"[({lat}):1:({lat})][({lon}):1:({lon})]"
    )
    async with gate:
        for attempt in range(2):
            try:
                response = await client.get(
                    f"{SST_URL}?{query}", headers={"User-Agent": USER_AGENT}
                )
            except httpx.HTTPError:
                if attempt == 0:
                    await asyncio.sleep(1.5)
                    continue
                return None
            if response.status_code == 404:
                # ERDDAP answers "no matching results" with a 404 — a genuine
                # absence for that cell, not worth a retry.
                return None
            if response.status_code >= 500 and attempt == 0:
                await asyncio.sleep(1.5)
                continue
            response.raise_for_status()
            rows = (response.json().get("table") or {}).get("rows") or []
            return _mean([row[3] for row in rows if len(row) > 3])
    return None


#: Offsets tried when the requested point has no SST pixel, in degrees. A
#: harbour sits inside a land cell of a 5 km satellite analysis, so the record
#: has to be sampled from open water a short way off.
_SST_PROBE_OFFSETS = (0.0, 0.25, 0.5, 0.75, 1.0)


async def _resolve_sst_point(
    client: httpx.AsyncClient,
    gate: asyncio.Semaphore,
    lat: float,
    lon: float,
    start: date,
    end: date,
) -> tuple[float, float, float] | None:
    """The nearest cell to (lat, lon) that the SST analysis actually covers.

    Digha is a harbour, and a harbour sits in a land cell of a 5 km satellite
    product — so asking for the user's own position returns nothing and the
    warming record, the single most relevant measurement here, silently vanishes
    from the answer. Rather than drop it, the sample is taken from open water a
    short way off and the distance is reported, which is honest and still
    describes the water the boat fishes in.

    Resolved once against the most recent window and reused for every year, so
    the probing costs a handful of requests rather than a handful per year.
    """
    for offset in _SST_PROBE_OFFSETS:
        if offset == 0.0:
            candidates = [(lat, lon)]
        else:
            # Eight compass directions, so this works on either coast and around
            # the islands without ORCA having to decide which way the sea is.
            candidates = [
                (lat + offset, lon), (lat - offset, lon),
                (lat, lon + offset), (lat, lon - offset),
                (lat + offset * 0.7, lon + offset * 0.7),
                (lat + offset * 0.7, lon - offset * 0.7),
                (lat - offset * 0.7, lon + offset * 0.7),
                (lat - offset * 0.7, lon - offset * 0.7),
            ]
        for probe_lat, probe_lon in candidates:
            value = await _sst_window(client, gate, probe_lat, probe_lon, start, end)
            if value is not None:
                return probe_lat, probe_lon, offset * 111.0
    return None


async def fetch_season_history(
    latitude: float,
    longitude: float,
    years: int = DEFAULT_YEARS,
    today: date | None = None,
    timeout: float = 60.0,
) -> SeasonHistory:
    """Yearly seasonal means for one place, with the trend through each.

    Every year's window is fetched concurrently, and a year that fails is
    dropped rather than taking the whole trend down with it — but the years that
    did answer are reported with their own first and last year attached, so a
    thin record is visible as a thin record.
    """
    windows = _windows(years, today or date.today())
    if not windows:
        raise HistoryDataError("No complete seasonal window is available yet")

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        # One bounded pool: four calls a year against three services would
        # otherwise arrive as a burst and earn a rate limit.
        gate = asyncio.Semaphore(4)
        # ERDDAP gets its own gate of one: see _sst_window.
        sst_gate = asyncio.Semaphore(1)

        # Where the SST record can actually be read near this position.
        newest_year, newest_start, newest_end = windows[-1]
        sst_point = await _resolve_sst_point(
            client, sst_gate, latitude, longitude, newest_start, newest_end
        )

        async def one_year(year: int, start: date, end: date) -> tuple[int, dict[str, float | None]]:
            async with gate:
                era5, wave, sst = await asyncio.gather(
                    _era5_window(client, latitude, longitude, start, end),
                    _wave_window(client, latitude, longitude, start, end),
                    (
                        _sst_window(client, sst_gate, sst_point[0], sst_point[1], start, end)
                        if sst_point
                        else _no_sst()
                    ),
                    return_exceptions=True,
                )
            wind, rain = era5 if isinstance(era5, tuple) else (None, None)
            return year, {
                "wind": wind,
                "rain": rain,
                "wave": wave if isinstance(wave, (int, float)) else None,
                "sst": sst if isinstance(sst, (int, float)) else None,
            }

        results = await asyncio.gather(
            *(one_year(y, s, e) for y, s, e in windows), return_exceptions=True
        )

    collected: dict[int, dict[str, float | None]] = {}
    for item in results:
        if isinstance(item, Exception):
            continue
        year, values = item
        collected[year] = values

    if not collected:
        raise HistoryDataError("No historical record could be read for this location")

    current_year = windows[-1][0]

    definitions = [
        ("sst", "Sea surface temperature", "°C", SOURCES["sst"]),
        ("wind", "Wind speed", "km/h", SOURCES["wind"]),
        ("rain", "Rainfall", "mm/day", SOURCES["rain"]),
        ("wave", "Wave height", "m", SOURCES["wave"]),
    ]

    metrics: list[MetricTrend] = []
    for key, label, unit, source in definitions:
        by_year = {
            year: values[key]
            for year, values in sorted(collected.items())
            if values.get(key) is not None
        }
        if len(by_year) < 2:
            continue

        ordered = sorted(by_year)
        latest_year = ordered[-1]
        latest = by_year[latest_year]
        earlier = [by_year[y] for y in ordered[:-1]]
        baseline = statistics.fmean(earlier) if earlier else None

        # An anomaly is a statement about *now*. If the newest year this metric
        # returned is not the current season, comparing it to the years before
        # it would be presented as a live signal while describing an old one.
        if latest_year != current_year or len(earlier) < 2:
            baseline = None

        metrics.append(
            MetricTrend(
                key=key,
                label=label,
                unit=unit,
                source=source,
                by_year={y: float(v) for y, v in by_year.items()},
                slope_per_decade=_fit_slope_per_decade({y: float(v) for y, v in by_year.items()}),
                anomaly=None if baseline is None else float(latest) - baseline,
                baseline=baseline,
                latest=float(latest),
                first_year=ordered[0],
                last_year=latest_year,
            )
        )

    if not metrics:
        raise HistoryDataError("The historical record for this location is too sparse to compare")

    first_year, start, end = windows[0]
    window_label = f"{start:%d %b} – {end:%d %b}"

    notes = [
        "ORCA holds no catch or landing records. These are measurements of the "
        "water itself, not of how much fish was caught.",
    ]
    if sst_point and sst_point[2] > 1.0:
        notes.append(
            f"Sea surface temperature is sampled about {sst_point[2]:.0f} km offshore — the "
            "satellite analysis has no reading in the coastal cell at this position."
        )
    sst_metric = next((m for m in metrics if m.key == "sst"), None)
    if sst_metric and sst_metric.first_year and sst_metric.first_year > first_year:
        notes.append(
            f"Sea surface temperature only goes back to {sst_metric.first_year} here — the "
            "blended satellite analysis begins in July 2019, so its baseline is shorter "
            "than the wind and rainfall ones."
        )

    return SeasonHistory(
        latitude=latitude,
        longitude=longitude,
        window_label=window_label,
        metrics=metrics,
        notes=notes,
    )
