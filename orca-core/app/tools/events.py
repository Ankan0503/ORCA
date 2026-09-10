"""Marine hazard events from NASA EONET, and their drift.

The web console shows an oil-spill and marine-event layer. HackHeritage's
version of this reached for two genuinely real sources — NASA's Earth
Observatory Natural Event Tracker and the Copernicus STAC catalogue — and both
were verified live while porting: EONET returned named storms with real
coordinates and dates, Copernicus answered on its collections endpoint.

So this is a straight port of a good idea, unlike the vessel layer beside it.

What is added here rather than carried across: **drift**. An event's position is
where it was last observed, and for anything floating that is not where it is
now. ORCA already knows the surface current at any point from its own sea grid,
so each event carries the direction and speed the water there is setting — which
is the number that decides whether a slick is coming towards a fishing ground or
away from it. HackHeritage's version left those fields on the type and never
filled them.

EONET has no "oil spill" category of its own. It tracks severe storms, sea and
lake ice, volcanoes, wildfires and water colour — the last of which is where
algal blooms and discolouration events appear. Calling the layer "oil spills" is
therefore already a slight overclaim, and the honest framing kept here is
**marine hazard events**: real, dated, positioned, from an agency that publishes
them, with ORCA saying which category each one actually is rather than implying
every marker is a spill.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx

log = logging.getLogger("orca.events")

EONET_URL = "https://eonet.gsfc.nasa.gov/api/v3/events"

# The categories that mean anything at sea. Wildfires and volcanoes are tracked
# by EONET too and are not a fisherman's problem, so they are not requested.
MARINE_CATEGORIES = "seaLakeIce,severeStorms,waterColor"

SOURCE = "NASA EONET (Earth Observatory Natural Event Tracker)"

# Beyond this an event is real but not this trip's concern. Chosen to cover a
# day's steaming plus a wide margin, so nothing relevant is filtered out.
DEFAULT_RADIUS_KM = 600.0

EARTH_RADIUS_KM = 6371.0
KM_PER_NM = 1.852


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


@dataclass
class MarineEvent:
    """One dated, positioned hazard, as an agency published it."""

    id: str
    title: str
    category: str
    latitude: float
    longitude: float
    detected_at: str
    source_authority: str = SOURCE
    link_url: str | None = None
    distance_km: float | None = None
    # Where the water at this position is setting, and how fast. Filled from
    # ORCA's own current grid rather than guessed.
    drift_direction_deg: float | None = None
    drift_speed_kts: float | None = None
    closed: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "latitude": round(self.latitude, 4),
            "longitude": round(self.longitude, 4),
            "detectedAt": self.detected_at,
            "sourceAuthority": self.source_authority,
            "linkUrl": self.link_url,
            "distanceKm": None if self.distance_km is None else round(self.distance_km, 1),
            "distanceNm": (
                None if self.distance_km is None else round(self.distance_km / KM_PER_NM, 1)
            ),
            "driftDirectionDeg": self.drift_direction_deg,
            "driftSpeedKts": (
                None if self.drift_speed_kts is None else round(self.drift_speed_kts, 2)
            ),
            # The console's type carries these; EONET publishes point events
            # rather than footprints, so they stay null instead of being
            # invented as a circle around the point.
            "areaKm2": None,
            "polygon": None,
            "isClosed": self.closed,
        }


@dataclass
class MarineEventReport:
    latitude: float
    longitude: float
    events: list[MarineEvent] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    degraded: bool = False

    def to_dict(self) -> dict:
        status = (
            "SERVICE_DEGRADED"
            if self.degraded
            else "ACTIVE_SPILLS_DETECTED"
            if self.events
            else "NO_ACTIVE_SPILLS_DETECTED"
        )
        return {
            "status": status,
            "activeSpillsCount": len(self.events),
            "events": [e.to_dict() for e in self.events],
            "queriedAt": datetime.now(timezone.utc).isoformat(),
            "source": SOURCE,
            "warnings": self.warnings,
            "note": (
                "EONET publishes severe storms, sea and lake ice, and water-colour "
                "events — it has no oil-spill category. Each marker states its own "
                "category rather than being presented as a confirmed spill."
            ),
        }


class MarineEventError(RuntimeError):
    """Raised when EONET cannot be reached."""


async def fetch_marine_events(
    latitude: float,
    longitude: float,
    radius_km: float = DEFAULT_RADIUS_KM,
    limit: int = 40,
    timeout: float = 30.0,
) -> MarineEventReport:
    """Open marine events near a position, nearest first.

    A failure here degrades the layer rather than the request: the console can
    show everything else without knowing whether a storm is being tracked three
    hundred kilometres away.
    """
    report = MarineEventReport(latitude=latitude, longitude=longitude)

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(
                EONET_URL,
                params={
                    "category": MARINE_CATEGORIES,
                    "status": "open",
                    "limit": limit,
                },
            )
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        log.warning("EONET unavailable: %s", exc)
        report.degraded = True
        report.warnings.append(f"NASA EONET could not be reached: {exc}")
        return report

    for entry in payload.get("events") or []:
        geometry = entry.get("geometry") or []
        if not geometry:
            continue
        # The last geometry is the most recent fix; a tracked storm has many.
        latest = geometry[-1]
        coords = latest.get("coordinates")
        if not isinstance(coords, list) or len(coords) < 2:
            continue
        try:
            lon, lat = float(coords[0]), float(coords[1])
        except (TypeError, ValueError):
            continue

        distance = _haversine_km(latitude, longitude, lat, lon)
        if distance > radius_km:
            continue

        categories = entry.get("categories") or []
        category = (categories[0].get("title") if categories else None) or "Marine event"
        sources = entry.get("sources") or []
        link = entry.get("link") or (sources[0].get("url") if sources else None)

        report.events.append(
            MarineEvent(
                id=str(entry.get("id") or f"eonet-{lat:.3f}-{lon:.3f}"),
                title=str(entry.get("title") or "Unnamed event"),
                category=str(category),
                latitude=lat,
                longitude=lon,
                detected_at=str(latest.get("date") or ""),
                link_url=link,
                distance_km=distance,
                closed=bool(entry.get("closed")),
            )
        )

    report.events.sort(key=lambda e: e.distance_km or 0.0)
    if not report.events:
        report.warnings.append(
            f"No open marine events within {radius_km:.0f} km. EONET was reached; "
            "there is simply nothing being tracked nearby."
        )
    return report


async def attach_drift(report: MarineEventReport) -> MarineEventReport:
    """Fill each event's drift from ORCA's own surface-current grid.

    Where an event *is* matters less than where the water is taking it, and this
    is the one thing the console's own type asked for and never had. Imported
    here rather than at module scope because the sea grid imports geofence,
    which loads several megabytes of polygons — a cost this module should not
    impose on anything that only wants the event list.
    """
    if not report.events:
        return report

    from .seagrid import fetch_sea_grid

    points = [(e.latitude, e.longitude) for e in report.events]
    try:
        cells = await fetch_sea_grid(points)
    except Exception as exc:  # noqa: BLE001 - drift is an enrichment, not the answer
        log.warning("drift lookup failed: %s", exc)
        report.warnings.append("Surface current unavailable, so drift is not shown.")
        return report

    for event, cell in zip(report.events, cells):
        speed_ms = cell.current_speed_trusted_ms
        if speed_ms is None:
            continue
        event.drift_speed_kts = speed_ms * 1.94384
        event.drift_direction_deg = cell.current_direction_deg
    return report
