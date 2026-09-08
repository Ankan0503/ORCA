"""Data discovery — what ORCA can actually reach, checked rather than claimed.

The problem statement asks for agents that autonomously *discover, retrieve and
integrate* datasets. The honest position is that ORCA's sources are chosen
deliberately and written down: INCOIS for the fishing advisory, IMD for wind
warnings and cyclones, Marine Regions for the EEZ, MoEFCC for protected areas,
NOAA and ERA5 for history, Open-Meteo for the forecast. Each was investigated,
several were tested and rejected, and the reasons live in the module that uses
them. Pretending a model picks them at runtime would be a worse system
described more grandly.

What is genuinely useful — and is what this agent does — is answer the questions
that catalogue makes possible, from live checks rather than from the catalogue's
own claims:

- *What data does ORCA have for this place?* The catalogue, filtered by whether
  each source actually covers the position.
- *Is it current?* Every source is probed now, and reports its own latency and
  whether it answered.
- *Where did this number come from?* Provenance, resolution and update cadence
  for the source behind any figure.

The distinction that keeps it honest: a catalogue entry says what a source is
*for*, and the probe says whether it is *there*. A source that is listed and
unreachable is reported as unreachable, because the failure mode this guards
against is a screen that quietly falls back and looks fine — which is the exact
failure this project has spent its time removing.

It also carries the negative results. `E06OCM_L3_LAC_CQ` from ISRO's MOSDAC is
catalogued with yesterday's date and returns `404 NOT_RELEASED` on download for
at least twelve days; Open-Meteo advertises historical sea-surface temperature
and returns arrays of nulls. Both were measured. Recording a rejected source
beside an accepted one is what stops the next person repeating the search.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from .base import Agent, AgentResult, Evidence, QueryContext

_DEFAULT_LAT = 21.6272
_DEFAULT_LON = 87.5079

USER_AGENT = "ORCA/0.1 (marine advisory; contact via project repository)"


@dataclass
class Source:
    """One dataset ORCA can read, and how to check it is still there."""

    key: str
    name: str
    provider: str
    used_for: str
    resolution: str
    cadence: str
    #: A cheap request that proves the service is answering. Kept small on
    #: purpose: this is a liveness check, not a download.
    probe_url: str | None = None
    #: Geographic limit, as (min_lat, min_lon, max_lat, max_lon). None = global.
    covers: tuple[float, float, float, float] | None = None
    #: Set when a source was investigated and turned down, with the reason.
    rejected: str | None = None
    notes: str = ""


#: India's waters, for the sources that only cover them.
_INDIA = (5.0, 66.0, 25.0, 95.0)

CATALOGUE: list[Source] = [
    Source(
        key="incois_pfz",
        name="Potential Fishing Zone advisories",
        provider="INCOIS (Indian National Centre for Ocean Information Services)",
        used_for="Where the fish are advised to be, per landing centre, per sector",
        resolution="Advisory rows per landing centre, 14 sectors",
        cadence="Daily, published the afternoon before the forecast day",
        probe_url="https://incois.gov.in/MarineFisheries/TextDataHome?mfid=1&request_locale=en",
        covers=_INDIA,
        notes="Scraped: there is no API. Needs a session cookie from the home page first.",
    ),
    Source(
        key="incois_pfz_lines",
        name="PFZ advisory lines (GeoServer WFS)",
        provider="INCOIS",
        used_for="The frontal boundaries drawn on the map",
        resolution="Vector lines",
        cadence="Daily",
        probe_url=(
            "https://incois.gov.in/geoserver/PFZ_Automation/ows?service=WFS&version=1.1.0"
            "&request=GetCapabilities"
        ),
        covers=_INDIA,
    ),
    Source(
        key="imd_cyclone",
        name="Tropical Weather Outlook",
        provider="IMD / RSMC Tropical Cyclones, New Delhi",
        used_for="Declared systems and 7-day cyclogenesis probability per basin",
        resolution="Basin-level",
        cadence="Daily bulletins",
        probe_url="https://rsmcnewdelhi.imd.gov.in/",
        covers=_INDIA,
        notes="Parsed from the published PDF; ORCA never declares a cyclone itself.",
    ),
    Source(
        key="open_meteo_marine",
        name="Marine forecast (waves, swell, currents, SST)",
        provider="Open-Meteo, from ECMWF WAM / MFWAM and MeteoFrance SMOC",
        used_for="Wave height and period, swell, surface currents, sea temperature",
        resolution="8-9 km",
        cadence="Hourly, refreshed through the day",
        probe_url="https://marine-api.open-meteo.com/v1/marine?latitude=21.6&longitude=87.5&hourly=wave_height&forecast_days=1",
        notes=(
            "Open-Meteo's own documentation warns the current data is not suitable for "
            "coastal navigation; ORCA carries that caveat into the route card."
        ),
    ),
    Source(
        key="open_meteo_forecast",
        name="Weather forecast (wind, rain, storms, visibility)",
        provider="Open-Meteo, from national weather models",
        used_for="Wind and gusts, precipitation, thunderstorm codes, visibility",
        resolution="~2-11 km depending on model",
        cadence="Hourly",
        probe_url="https://api.open-meteo.com/v1/forecast?latitude=21.6&longitude=87.5&hourly=wind_speed_10m&forecast_days=1",
    ),
    Source(
        key="era5_archive",
        name="ERA5 reanalysis archive",
        provider="ECMWF via Open-Meteo",
        used_for="Wind and rainfall for the same weeks of every past year",
        resolution="~11 km",
        cadence="Published with about 5 days' lag",
        probe_url="https://archive-api.open-meteo.com/v1/archive?latitude=21.6&longitude=87.5&start_date=2024-09-01&end_date=2024-09-02&daily=wind_speed_10m_mean",
    ),
    Source(
        key="noaa_blended_sst",
        name="Geo-Polar Blended SST Analysis",
        provider="NOAA CoastWatch (ERDDAP)",
        used_for="Sea surface temperature back to July 2019, for the trend",
        resolution="5 km daily",
        cadence="Daily",
        probe_url="https://coastwatch.noaa.gov/erddap/griddap/noaacwBLENDEDsstDNDaily.das",
        notes="Coastal cells are empty; ORCA samples the nearest covered water and says so.",
    ),
    Source(
        key="marine_regions_eez",
        name="Exclusive Economic Zone boundaries v12",
        provider="Marine Regions / Flanders Marine Institute",
        used_for="Whether a position is in Indian waters, and how far the nearest border is",
        resolution="Vector polygons",
        cadence="Static, versioned",
        probe_url=None,
        covers=_INDIA,
        notes="Held on the server, so the geofence works without any third party being up.",
    ),
    Source(
        key="moefcc_pa",
        name="Wildlife sanctuaries and national parks",
        provider="MoEFCC via PM GatiShakti National Master Plan",
        used_for="Marine protected areas a boat may not enter",
        resolution="Vector polygons, 121 coastal and island areas",
        cadence="Static, updated on notification",
        probe_url=None,
        covers=_INDIA,
    ),
    # --- Investigated and turned down ---------------------------------------
    Source(
        key="mosdac_ocm3",
        name="Oceansat-3 OCM-3 daily coastal water quality (E06OCM_L3_LAC_CQ)",
        provider="ISRO / MOSDAC",
        used_for="Would have been chlorophyll, India's own instrument, 1 km",
        resolution="1 km",
        cadence="Catalogued daily",
        covers=_INDIA,
        rejected=(
            "Measured: every one of the twelve most recent granules returns "
            "404 NOT_RELEASED on download. The catalogue lists yesterday, the archive "
            "releases at least twelve days later."
        ),
        notes="A catalogue end-date is not a download date. Worth revisiting for validation.",
    ),
    Source(
        key="open_meteo_sst_history",
        name="Historical sea surface temperature",
        provider="Open-Meteo archive and marine APIs",
        used_for="Would have been the SST baseline for the trend",
        resolution="—",
        cadence="—",
        rejected=(
            "The variable is advertised for historical dates and returns a full array of "
            "nulls, in both the archive and marine APIs, everywhere tested."
        ),
    ),
    Source(
        key="noaa_oisst",
        name="OISST v2.1 daily SST, 1981-present",
        provider="NOAA (coastwatch.pfeg)",
        used_for="Would have been a 40-year SST baseline instead of 7",
        resolution="0.25 degrees",
        cadence="Daily",
        rejected="The host refuses connections from here; the request times out at 21 s.",
    ),
]


@dataclass
class ProbeResult:
    source: Source
    reachable: bool | None  # None = nothing to probe
    latency_ms: int | None = None
    detail: str = ""
    covers_position: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.source.key,
            "name": self.source.name,
            "provider": self.source.provider,
            "usedFor": self.source.used_for,
            "resolution": self.source.resolution,
            "cadence": self.source.cadence,
            "notes": self.source.notes or None,
            "rejected": self.source.rejected,
            "coversPosition": self.covers_position,
            "reachable": self.reachable,
            "latencyMs": self.latency_ms,
            "detail": self.detail or None,
        }


def _covers(source: Source, latitude: float, longitude: float) -> bool:
    if source.covers is None:
        return True
    min_lat, min_lon, max_lat, max_lon = source.covers
    return min_lat <= latitude <= max_lat and min_lon <= longitude <= max_lon


async def probe_catalogue(
    latitude: float, longitude: float, timeout: float = 12.0
) -> list[ProbeResult]:
    """Check every live source now, concurrently, and report what answered."""
    results: dict[str, ProbeResult] = {}

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        async def check(source: Source) -> None:
            covers = _covers(source, latitude, longitude)
            if source.rejected is not None:
                results[source.key] = ProbeResult(source, None, detail="not in use",
                                                  covers_position=covers)
                return
            if source.probe_url is None:
                results[source.key] = ProbeResult(
                    source, True, detail="held on the server", covers_position=covers
                )
                return

            started = time.perf_counter()
            try:
                response = await client.get(
                    source.probe_url, headers={"User-Agent": USER_AGENT}
                )
                elapsed = int((time.perf_counter() - started) * 1000)
                ok = response.status_code < 400
                results[source.key] = ProbeResult(
                    source,
                    ok,
                    latency_ms=elapsed,
                    detail=f"HTTP {response.status_code}",
                    covers_position=covers,
                )
            except httpx.HTTPError as exc:
                elapsed = int((time.perf_counter() - started) * 1000)
                results[source.key] = ProbeResult(
                    source,
                    False,
                    latency_ms=elapsed,
                    detail=type(exc).__name__,
                    covers_position=covers,
                )

        await asyncio.gather(*(check(s) for s in CATALOGUE))

    return [results[s.key] for s in CATALOGUE if s.key in results]


class DataDiscoveryAgent(Agent):
    name = "data_discovery"
    description = (
        "What data ORCA holds for a place, where each figure comes from, how fresh and how "
        "detailed it is, and whether each source is answering right now. Also reports the "
        "sources that were investigated and rejected, and why. Use for questions about "
        "provenance, coverage, accuracy, staleness, 'how do you know', 'what data do you "
        "use', or when something appears to be missing."
    )
    handles = (
        "data", "source", "where from", "how do you know", "provenance", "reliable",
        "accurate", "stale", "old", "coverage", "satellite", "which api", "trust",
        "why don't you", "missing",
    )
    is_stub = False

    parameters = {
        "type": "object",
        "properties": {
            "latitude": {"type": "number", "description": "Only if not the user's position."},
            "longitude": {"type": "number", "description": "Only if not the user's position."},
            "probe": {
                "type": "boolean",
                "description": (
                    "Check each source is answering right now. Default true. Set false for "
                    "a catalogue listing only, which is instant."
                ),
            },
        },
    }

    async def run(self, context: QueryContext) -> AgentResult:
        latitude = context.latitude if context.latitude is not None else _DEFAULT_LAT
        longitude = context.longitude if context.longitude is not None else _DEFAULT_LON
        probe = context.params.get("probe")
        probe = True if probe is None else bool(probe)

        if probe:
            results = await probe_catalogue(latitude, longitude)
        else:
            results = [
                ProbeResult(s, None, detail="not checked",
                            covers_position=_covers(s, latitude, longitude))
                for s in CATALOGUE
            ]

        live = [r for r in results if r.source.rejected is None]
        up = [r for r in live if r.reachable]
        down = [r for r in live if r.reachable is False]
        rejected = [r for r in results if r.source.rejected is not None]
        out_of_area = [r for r in live if not r.covers_position]

        if probe:
            summary = (
                f"{len(up)} of {len(live)} data sources answered just now"
                + (f"; {len(down)} did not ({', '.join(r.source.name for r in down)})"
                   if down else "")
                + f". {len(rejected)} more were investigated and turned down."
            )
        else:
            summary = (
                f"ORCA reads {len(live)} data sources, and records {len(rejected)} it "
                "investigated and turned down."
            )
        if out_of_area:
            summary += (
                f" {len(out_of_area)} of them cover only Indian waters and not this position."
            )

        evidence = [
            Evidence(
                source=r.source.provider,
                label=r.source.name,
                value=(
                    "rejected"
                    if r.source.rejected
                    else "reachable" if r.reachable else "unreachable" if r.reachable is False
                    else "not checked"
                ),
                unit=None,
                observed_at=None,
                note=r.source.rejected or f"{r.source.resolution}, {r.source.cadence}",
            )
            for r in results
        ]

        return AgentResult(
            agent=self.name,
            summary=summary,
            evidence=evidence,
            confidence=0.85 if probe else 0.6,
            data={
                "catalogue": [r.to_dict() for r in results],
                "checkedLive": probe,
                "position": {"latitude": latitude, "longitude": longitude},
            },
        )
