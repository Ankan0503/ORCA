"""Potential Fishing Zone advisories, scraped from INCOIS.

INCOIS (the Indian National Centre for Ocean Information Services, under the
Ministry of Earth Sciences) derives Potential Fishing Zones from satellite sea
surface temperature and chlorophyll and publishes them daily. There is no API —
but the WebGIS behind their site is a standard GeoServer, and the human-readable
advisory is a plain server-rendered table. This module reads both, so ORCA can
show the *real government advisory* instead of a derived guess:

- The **line geometry** the WebGIS draws comes from a GeoServer WFS layer as
  GeoJSON (``fetch_pfz_lines``).
- The **per-sector table** — landing centre, direction, bearing, depth range,
  distance range and the position in degrees-minutes-seconds — is scraped from
  the Marine Fisheries "TextData" page (``fetch_sector_advisory``), which INCOIS
  serves in all ten coastal languages.
- The **forecast date and validity** come from the TextData home page
  (``fetch_forecast_status``).

Everything is stamped with the forecast date read from INCOIS, never with the
machine's clock, and never with the WFS ``Year`` attribute — that field is stuck
at 2021 on their server (a bug in their automation) while the geometry itself is
current. If INCOIS is unreachable, the last good advisory is served with its own
date visible, so the map never shows a fresh-looking answer that is really stale.

No third-party HTML library is used: the table is small and its shape is fixed,
so a tiny :class:`html.parser.HTMLParser` subclass extracts it. That keeps the
backend's dependency list to what is already installed.
"""

from __future__ import annotations

import asyncio
import re
import time
from dataclasses import dataclass, field, replace
from datetime import date, datetime
from html.parser import HTMLParser

import httpx

from ..config import get_settings

# --- INCOIS endpoints -------------------------------------------------------
# Endpoints are loaded dynamically from Settings / .env (see app.config).


# A government portal answers unidentified clients unpredictably; identify ORCA.
USER_AGENT = "ORCA-Marine/0.1 (SIH 26176 marine advisory prototype)"


@dataclass(frozen=True)
class Sector:
    """One INCOIS coastal advisory sector.

    ``centroid`` is an approximate point on that stretch of coast, used only to
    route a user's position to the sector nearest them — it is not shown.
    """

    secid: str
    name: str
    centroid: tuple[float, float]


# The 14 sectors INCOIS divides the Indian coastline and islands into, in the
# order their dropdown lists them. Centroids are rough coastal points, good
# enough to pick the nearest sector to a fisherman's location.
SECTORS: tuple[Sector, ...] = (
    Sector("SEC001", "Gujarat", (21.0, 69.5)),
    Sector("SEC002", "Maharashtra", (18.5, 72.8)),
    Sector("SEC003", "Goa", (15.3, 73.8)),
    Sector("SEC004", "Karnataka", (13.8, 74.5)),
    Sector("SEC005", "Kerala", (10.0, 76.0)),
    Sector("SEC006", "South Tamil Nadu", (8.5, 77.8)),
    Sector("SEC007", "North Tamil Nadu", (12.0, 80.1)),
    Sector("SEC008", "South Andhra Pradesh", (15.5, 80.3)),
    Sector("SEC009", "North Andhra Pradesh", (17.7, 83.3)),
    Sector("SEC010", "Odisha", (20.0, 86.5)),
    Sector("SEC011", "West Bengal", (21.6, 88.0)),
    Sector("SEC012", "Andaman", (12.0, 92.8)),
    Sector("SEC013", "Nicobar", (8.0, 93.5)),
    Sector("SEC014", "Lakshadweep", (10.5, 72.6)),
)

_SECTOR_BY_ID = {s.secid: s for s in SECTORS}

# INCOIS's request_locale codes. ORCA's own language codes match one-to-one for
# the coastal languages; anything else falls back to English.
_SUPPORTED_LOCALES = {"en", "hi", "te", "ta", "kn", "or", "bn", "ml", "gu", "mr"}


class PfzDataError(RuntimeError):
    """Raised when INCOIS cannot be reached or returns nothing usable."""


# --- Data shapes ------------------------------------------------------------


@dataclass
class PfzPoint:
    """One row of an INCOIS advisory: a fishing ground and how to reach it."""

    landing_centre: str
    direction: str
    bearing_deg: int | None
    distance_km_from: float | None
    distance_km_to: float | None
    depth_m_from: float | None
    depth_m_to: float | None
    latitude: float
    longitude: float
    # The original DMS strings, kept so the exact government wording can be shown.
    latitude_dms: str
    longitude_dms: str

    def to_dict(self) -> dict:
        return {
            "landing_centre": self.landing_centre,
            "direction": self.direction,
            "bearing_deg": self.bearing_deg,
            "distance_km_from": self.distance_km_from,
            "distance_km_to": self.distance_km_to,
            "depth_m_from": self.depth_m_from,
            "depth_m_to": self.depth_m_to,
            "latitude": round(self.latitude, 5),
            "longitude": round(self.longitude, 5),
            "latitude_dms": self.latitude_dms,
            "longitude_dms": self.longitude_dms,
        }


@dataclass
class ForecastStatus:
    """When the current advisory is for, as INCOIS states it."""

    forecast_date: str | None  # e.g. "5 SEP 2026"
    valid_upto: str | None  # e.g. "6 SEP 2026"

    def to_dict(self) -> dict:
        return {"forecast_date": self.forecast_date, "valid_upto": self.valid_upto}


@dataclass
class SectorAdvisory:
    """A whole sector's advisory for one forecast day."""

    secid: str
    sector_name: str
    language: str
    forecast_date: str | None
    valid_upto: str | None
    points: list[PfzPoint] = field(default_factory=list)
    # True when INCOIS returned the page but it held no fishing rows — a real
    # "no PFZ issued for this sector today", not a fetch failure.
    empty: bool = False
    # True when INCOIS could not be reached and this is the last good advisory
    # served in its place. The forecast_date still shows which day it is really
    # for, so a stale answer can never masquerade as today's.
    stale: bool = False

    def to_dict(self) -> dict:
        return {
            "secid": self.secid,
            "sector_name": self.sector_name,
            "language": self.language,
            "forecast_date": self.forecast_date,
            "valid_upto": self.valid_upto,
            "empty": self.empty,
            "stale": self.stale,
            "points": [p.to_dict() for p in self.points],
        }


# --- Parsing helpers --------------------------------------------------------


class _TableCollector(HTMLParser):
    """Collect every HTML table as a list of rows of plain-text cells.

    Deliberately small: INCOIS's page is simple and its PFZ table has a fixed
    shape, so the right table is found later by its header rather than by any
    fragile positional assumption.
    """

    def __init__(self) -> None:
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self._in_table = 0
        self._rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag == "table":
            self._in_table += 1
            self._rows = []
        elif tag == "tr" and self._in_table:
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = []

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in ("td", "th") and self._cell is not None and self._row is not None:
            text = re.sub(r"\s+", " ", "".join(self._cell)).strip()
            self._row.append(text)
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if any(c for c in self._row):
                self._rows.append(self._row)
            self._row = None
        elif tag == "table" and self._in_table:
            self._in_table -= 1
            if self._rows:
                self.tables.append(self._rows)
            self._rows = []


def _dms_to_decimal(text: str) -> float | None:
    """Turn "20 58 18 N" — or "20 58 18 উত্তর" — into signed decimal degrees.

    INCOIS localises the hemisphere word into each language (North becomes
    উত্তর, वटर, and so on), so it cannot be matched by letter. Indian waters are
    always north and east, so the default is positive; a value is only made
    negative when the hemisphere is written as a plain Latin ``S`` or ``W``. The
    three numbers (degrees, minutes, seconds) are always in Latin digits.
    """
    nums = re.findall(r"\d+(?:\.\d+)?", text or "")
    if len(nums) < 3:
        return None
    degrees, minutes, seconds = (float(n) for n in nums[:3])
    value = degrees + minutes / 60 + seconds / 3600
    if re.search(r"\b[SW]\b", text or "", re.IGNORECASE):
        value = -value
    return value


def _looks_like_dms(text: str) -> bool:
    """A coordinate cell has three whitespace-separated numbers up front."""
    return re.match(r"\s*\d+\s+\d+\s+\d+", text or "") is not None


def _range_pair(text: str) -> tuple[float | None, float | None]:
    """Split a "from-to" cell like "85-90" or "20-25" into two numbers."""
    nums = re.findall(r"\d+(?:\.\d+)?", text or "")
    if not nums:
        return None, None
    if len(nums) == 1:
        return float(nums[0]), float(nums[0])
    return float(nums[0]), float(nums[1])


def _int_or_none(text: str) -> int | None:
    match = re.search(r"-?\d+", text or "")
    return int(match.group()) if match else None


def parse_advisory_table(html: str) -> list[PfzPoint]:
    """Extract the PFZ rows from a TextData page's HTML.

    The advisory table is found by its shape, not its header text: it is the
    table whose data rows carry seven columns ending in two coordinate cells.
    Keying on the header would break in every language but English, since INCOIS
    translates the column titles; the DMS shape is the same in all ten.
    """
    collector = _TableCollector()
    collector.feed(html)

    def coordinate_rows(table: list[list[str]]) -> int:
        return sum(
            1
            for row in table
            if len(row) >= 7 and _looks_like_dms(row[5]) and _looks_like_dms(row[6])
        )

    candidates = [(coordinate_rows(t), t) for t in collector.tables]
    best = max(candidates, key=lambda pair: pair[0], default=(0, None))
    if best[0] == 0 or best[1] is None:
        return []
    table = best[1]

    points: list[PfzPoint] = []
    for row in table:
        if len(row) < 7 or not (_looks_like_dms(row[5]) and _looks_like_dms(row[6])):
            continue
        centre, direction, bearing, distance, depth, lat_dms, lon_dms = row[:7]
        latitude = _dms_to_decimal(lat_dms)
        longitude = _dms_to_decimal(lon_dms)
        if latitude is None or longitude is None:
            continue
        dist_from, dist_to = _range_pair(distance)
        depth_from, depth_to = _range_pair(depth)
        points.append(
            PfzPoint(
                landing_centre=centre,
                direction=direction,
                bearing_deg=_int_or_none(bearing),
                distance_km_from=dist_from,
                distance_km_to=dist_to,
                depth_m_from=depth_from,
                depth_m_to=depth_to,
                latitude=latitude,
                longitude=longitude,
                latitude_dms=lat_dms.strip(),
                longitude_dms=lon_dms.strip(),
            )
        )

    return points


def parse_forecast_status(html: str) -> ForecastStatus:
    """Read the forecast date and validity from the TextData home page.

    The page shows them as a two-row table: labels "Forecast Date" / "Valid
    upto" beside dates like "5 SEP 2026". Rather than depend on the exact table
    shape, the two dates are pulled by pattern and assigned in order.
    """
    dates = re.findall(r"\b\d{1,2}\s+[A-Za-z]{3,}\s+\d{4}\b", html)
    forecast_date = dates[0] if len(dates) >= 1 else None
    valid_upto = dates[1] if len(dates) >= 2 else None
    return ForecastStatus(forecast_date=forecast_date, valid_upto=valid_upto)


# --- Location routing -------------------------------------------------------


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    from math import atan2, cos, radians, sin, sqrt

    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * 6371.0 * atan2(sqrt(a), sqrt(1 - a))


def sector_for_location(latitude: float, longitude: float) -> Sector:
    """Pick the coastal sector nearest a position, so a user is routed to theirs."""
    return min(
        SECTORS,
        key=lambda s: _haversine_km(latitude, longitude, s.centroid[0], s.centroid[1]),
    )


def normalise_locale(language: str | None) -> str:
    code = (language or "en").split("-")[0].lower()
    return code if code in _SUPPORTED_LOCALES else "en"


# --- Fetching, with a per-day cache -----------------------------------------

# Advisories change once a day, so the cache is keyed to the calendar date. The
# first request on a new date re-fetches; everything after is served from memory.
# This is what makes the daily refresh automatic even without the scheduler.
_advisory_cache: dict[str, SectorAdvisory] = {}
_status_cache: dict[str, ForecastStatus] = {}
_lines_cache: dict[str, dict] = {}

# The most recent successful fetch, kept across days so a day when INCOIS is
# unreachable can still show the last real advisory (flagged stale) rather than
# nothing. Keyed by "secid|locale" for advisories.
_last_good_advisory: dict[str, SectorAdvisory] = {}
_last_good_lines: dict | None = None


def _today_key() -> str:
    return date.today().isoformat()


def _purge_old_days() -> None:
    """Drop every cached entry that is not for today.

    A new day's advisory replaces the previous one rather than accumulating
    beside it: these caches are keyed by date, so without this the dictionaries
    would grow without bound in a long-running server. The "last good" copies are
    deliberately *not* purged — they are the offline fallback.
    """
    today = _today_key()
    for cache in (_advisory_cache, _status_cache, _lines_cache):
        for key in [k for k in cache if not k.startswith(today)]:
            del cache[key]


async def _get(client: httpx.AsyncClient, url: str, **params) -> httpx.Response:
    response = await client.get(url, params=params or None, headers={"User-Agent": USER_AGENT})
    if response.status_code >= 400:
        raise PfzDataError(f"INCOIS request failed ({response.status_code}) for {url}")
    return response


async def fetch_forecast_status(
    *, timeout: float = 30.0, force: bool = False
) -> ForecastStatus:
    """The current advisory's forecast date and validity."""
    key = _today_key()
    _purge_old_days()
    if not force and key in _status_cache:
        return _status_cache[key]
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await _get(
                client, get_settings().incois_textdata_home_url, mfid=1, request_locale="en"
            )
    except httpx.HTTPError as exc:
        raise PfzDataError(f"Could not reach INCOIS: {exc}") from exc

    status = parse_forecast_status(response.text)
    _status_cache[key] = status
    return status


async def fetch_sector_advisory(
    secid: str,
    language: str = "en",
    *,
    timeout: float = 30.0,
    force: bool = False,
) -> SectorAdvisory:
    """The full advisory table for one sector, in one language.

    Cached per sector, per language, per day. The forecast date is fetched
    alongside so the advisory can always state which day it is for.
    """
    sector = _SECTOR_BY_ID.get(secid)
    if sector is None:
        raise PfzDataError(f"Unknown sector {secid!r}")

    locale = normalise_locale(language)
    key = f"{_today_key()}|{secid}|{locale}"
    _purge_old_days()
    if not force and key in _advisory_cache:
        return _advisory_cache[key]

    # INCOIS only fills the advisory table once a JSESSIONID exists: the home
    # page must be fetched first, on the *same* client, or TextData returns an
    # empty skeleton. The home is fetched in the requested language so the sector
    # table (landing-centre names and column titles) comes back localised. The
    # forecast dates are read separately in English (fetch_forecast_status),
    # because other languages localise the month names and would not parse.
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            await _get(client, get_settings().incois_textdata_home_url, mfid=1, request_locale=locale)
            response = await _get(
                client, get_settings().incois_textdata_url, secid=secid, request_locale=locale
            )
        status = await fetch_forecast_status(timeout=timeout, force=force)
    except httpx.HTTPError as exc:
        raise PfzDataError(f"Could not reach INCOIS: {exc}") from exc

    points = parse_advisory_table(response.text)
    advisory = SectorAdvisory(
        secid=secid,
        sector_name=sector.name,
        language=locale,
        forecast_date=status.forecast_date,
        valid_upto=status.valid_upto,
        points=points,
        empty=not points,
    )
    _advisory_cache[key] = advisory
    _last_good_advisory[f"{secid}|{locale}"] = advisory
    return advisory


async def get_sector_advisory(
    secid: str, language: str = "en", *, timeout: float = 30.0
) -> SectorAdvisory:
    """Like :func:`fetch_sector_advisory`, but never raises on a network fault.

    If INCOIS is unreachable and a previous advisory for this sector and
    language is on hand, it is returned with ``stale=True``. Only when there is
    nothing cached at all does the error propagate.
    """
    locale = normalise_locale(language)
    try:
        return await fetch_sector_advisory(secid, locale, timeout=timeout)
    except PfzDataError:
        last = _last_good_advisory.get(f"{secid}|{locale}")
        if last is None:
            raise
        return replace(last, stale=True)


async def fetch_pfz_lines(*, timeout: float = 60.0, force: bool = False) -> dict:
    """The PFZ line geometry the WebGIS draws, as a GeoJSON FeatureCollection.

    Returned verbatim from the WFS except that the collection is tagged with the
    forecast date read from the TextData home page — the per-feature ``Year`` on
    INCOIS's server is stuck at 2021 and must not be trusted for the date.
    """
    key = _today_key()
    _purge_old_days()
    if not force and key in _lines_cache:
        return _lines_cache[key]

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(
                get_settings().incois_pfz_lines_wfs_url, headers={"User-Agent": USER_AGENT}
            )
            if response.status_code >= 400:
                raise PfzDataError(f"PFZ line request failed ({response.status_code})")
            geojson = response.json()
            status = await fetch_forecast_status(timeout=timeout, force=force)
    except (httpx.HTTPError, ValueError) as exc:
        raise PfzDataError(f"Could not fetch PFZ lines: {exc}") from exc

    geojson["orca_forecast_date"] = status.forecast_date
    geojson["orca_valid_upto"] = status.valid_upto
    geojson["orca_stale"] = False
    _lines_cache[key] = geojson
    global _last_good_lines
    _last_good_lines = geojson
    return geojson


async def get_pfz_lines(*, timeout: float = 60.0) -> dict:
    """Like :func:`fetch_pfz_lines`, but falls back to the last good lines.

    Returns the previous day's geometry flagged ``orca_stale`` when INCOIS is
    down, so the map still draws something real with its own date attached.
    """
    try:
        return await fetch_pfz_lines(timeout=timeout)
    except PfzDataError:
        if _last_good_lines is None:
            raise
        return {**_last_good_lines, "orca_stale": True}


# INCOIS is a public government server, so requests are run concurrently but
# capped — fast enough to refresh the whole coastline in seconds without
# hammering them with 14 simultaneous sessions.
_MAX_CONCURRENT_SECTORS = 5


async def fetch_all_advisories(
    language: str = "en", *, force: bool = False, timeout: float = 30.0
) -> list[SectorAdvisory]:
    """Every sector's advisory, fetched concurrently.

    A sector that fails is skipped rather than failing the whole coastline: a
    fisherman in Kerala should not lose their advisory because the Andaman page
    timed out.
    """
    semaphore = asyncio.Semaphore(_MAX_CONCURRENT_SECTORS)

    async def one(sector: Sector) -> SectorAdvisory | None:
        async with semaphore:
            try:
                return await fetch_sector_advisory(
                    sector.secid, language, force=force, timeout=timeout
                )
            except PfzDataError:
                # Fall back to the last good copy for this sector if we have one.
                return _last_good_advisory.get(f"{sector.secid}|{normalise_locale(language)}")

    results = await asyncio.gather(*(one(s) for s in SECTORS))
    return [r for r in results if r is not None]


def build_points_geojson(advisories: list[SectorAdvisory]) -> dict:
    """Turn every sector's advisory rows into one GeoJSON point layer for the map.

    This is what puts the scraped table on the map: each INCOIS row becomes a
    point carrying the details a fisherman needs — which landing centre it is
    off, how far out, how deep, and on what bearing.
    """
    features = []
    forecast_date = None
    valid_upto = None
    stale = False

    for advisory in advisories:
        forecast_date = forecast_date or advisory.forecast_date
        valid_upto = valid_upto or advisory.valid_upto
        stale = stale or advisory.stale
        for point in advisory.points:
            features.append(
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [
                            round(point.longitude, 5),
                            round(point.latitude, 5),
                        ],
                    },
                    "properties": {
                        "sector": advisory.sector_name,
                        "secid": advisory.secid,
                        "forecast_date": advisory.forecast_date,
                        "valid_upto": advisory.valid_upto,
                        **point.to_dict(),
                    },
                }
            )

    return {
        "type": "FeatureCollection",
        "features": features,
        "orca_forecast_date": forecast_date,
        "orca_valid_upto": valid_upto,
        "orca_stale": stale,
        "orca_sector_count": len(advisories),
    }


async def refresh_all(force: bool = True) -> dict:
    """Re-scrape the whole coastline — what the daily scheduler calls.

    Every sector is refreshed, concurrently, and the previous day's cache is
    dropped in the process (see :func:`_purge_old_days`). Failures are reported
    rather than raised so one bad sector cannot stop the rest.
    """
    _purge_old_days()
    report: dict = {"date": _today_key(), "sectors": {}, "lines": None, "errors": []}

    lines_task = asyncio.create_task(_safe_lines(force))
    advisories = await fetch_all_advisories("en", force=force)
    report["lines"] = await lines_task

    found = {a.secid for a in advisories}
    for advisory in advisories:
        report["sectors"][advisory.secid] = (
            "empty" if advisory.empty else f"{len(advisory.points)} points"
        )
    for sector in SECTORS:
        if sector.secid not in found:
            report["sectors"][sector.secid] = "failed"
            report["errors"].append(f"{sector.secid}: unavailable")

    report["total_points"] = sum(len(a.points) for a in advisories)
    return report


async def _safe_lines(force: bool) -> str:
    try:
        await fetch_pfz_lines(force=force)
        return "ok"
    except PfzDataError:
        return "failed"
