"""The web console's contract, served from orca-core's own data.

Why this file exists
--------------------
The web console (the HackHeritage frontend) called ten endpoints on an Express
process that then called two Python services. Express is being removed, so the
console has to talk to this backend directly — and its components read specific
field names off specific shapes.

There were two ways to close that gap. Rewrite the console's ten call sites to
orca-core's own routes, or serve the console's existing contract from here. The
second was chosen: the shapes are validated by the console rendering, which is
testable, whereas rewriting call sites means changing UI code whose correctness
is much harder to check. It also means Express can be switched off without the
console changing at all.

This is a compatibility surface, and it says so. Every figure in it comes from
the same tools the app's own routes use — there is no second implementation of
anything, only a second shape.

What is deliberately not carried across
---------------------------------------
**Vessel traffic.** The console asks for live vessels. HackHeritage's service
answered with ten hardcoded ocean-buoy stations relabelled as vessel targets,
each given an ``mmsi`` of ``INCOIS-<station>`` and a type of
``OCEANOGRAPHIC_BUOY`` — with ``darkVessels`` left as a literal empty array and
a comment stating that fictitious vessels are not synthesised. That comment is
honest; the endpoint's name is not. There is no AIS feed behind ORCA, so this
returns an empty target list and says why. A map showing no vessels is correct.
A map showing buoys drawn as vessels is not.

**Coast Guard dispatch.** The console has a button that "transmits an
interception request to Coast Guard Command Control". The Express handler
logged a line to the server console and returned ``status: DISPATCHED``. Nothing
was transmitted. Returning a success status for a message that was never sent is
the kind of thing that gets believed in a demo and relied on afterwards, so this
returns ``NOT_TRANSMITTED`` with the reason. The console still renders it.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

import asyncio
import base64

from ..dependencies import get_orchestrator, get_sarvam
from ..language.detect import to_sarvam_code
from ..providers.sarvam import SarvamClient, SarvamError
from ..tools import events as events_tool
from ..tools import seagrid as seagrid_tool
from ..tools import evidence as evidence_tool
from ..tools import closures as closures_tool
from ..tools import geofence as geofence_tool
from ..tools import ocean as ocean_tool
from ..tools import pfz as pfz_tool
from ..tools import routing as routing_tool
from ..agents.weather import assess_point, trip_outlook
from ..tools.marine import MarineDataError, compass, fetch_marine_conditions

router = APIRouter(tags=["console"])

KM_PER_NM = 1.852
MS_TO_KTS = 1.94384
KMH_TO_KTS = 0.539957

# How far from the boat a boundary or protected area is still worth drawing.
# Wide enough to hold the whole of a day's steaming and the neighbouring
# maritime line, narrow enough that the console is not sent the Andaman Sea
# while its user is off Bengal.
BOUNDARY_RADIUS_KM = 600.0
CRITICAL_KM = geofence_tool.CRITICAL_KM
WARNING_KM = geofence_tool.WARNING_KM
WATCH_KM = geofence_tool.WATCH_KM
MPA_RADIUS_KM = 150.0

DISCLAIMER = (
    "ORCA supports a decision; it does not replace an official advisory. "
    "Every figure traces to the agency that issued it."
)


# --- shared helpers ----------------------------------------------------------


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0


def _box_distance_km(lat: float, lon: float, box: tuple) -> float:
    """Roughly how far a point is from a bounding box, in kilometres."""
    lat_min, lat_max, lon_min, lon_max = box
    dlat = max(lat_min - lat, 0.0, lat - lat_max)
    dlon = max(lon_min - lon, 0.0, lon - lon_max)
    return math.hypot(dlat * 111.0, dlon * 111.0 * math.cos(math.radians(lat)))


def _circle(lat: float, lon: float, radius_km: float, points: int = 36) -> list[list[float]]:
    """A closed ring approximating a circle of this radius, in GeoJSON order.

    Used for the caution margins, and an approximation in two ways worth naming:
    the margin around an irregular treaty line or coastline is not really
    circular, and the ring is drawn on a flat lon/lat grid rather than a
    geodesic. Both are recorded in LIMITATIONS.md. At 20 km off the Indian coast
    the error is small next to the margin itself, which is a caution band rather
    than a legal line.
    """
    ring: list[list[float]] = []
    lat_deg = radius_km / 111.0
    lon_deg = radius_km / (111.0 * max(0.2, math.cos(math.radians(lat))))
    for index in range(points + 1):
        angle = 2 * math.pi * index / points
        ring.append([
            round(lon + lon_deg * math.cos(angle), 5),
            round(lat + lat_deg * math.sin(angle), 5),
        ])
    return ring


def _nearest_mpa_vertex(lat: float, lon: float) -> tuple[float, float, str] | None:
    """The closest protected area, and the point on it nearest the boat."""
    best = None
    try:
        for properties, polygon in closures_tool._load_mpas():
            if not polygon:
                continue
            ring = polygon[0] if isinstance(polygon[0][0], (list, tuple)) else polygon
            distance = closures_tool._ring_min_distance_km(lat, lon, ring)
            if distance > WATCH_KM:
                continue
            if best is not None and distance >= best[0]:
                continue
            name = properties.get("NAME") or properties.get("name") or "Protected area"
            vertex = min(ring, key=lambda pt: (pt[1] - lat) ** 2 + (pt[0] - lon) ** 2)
            best = (distance, vertex[1], vertex[0], name)
    except Exception:  # noqa: BLE001
        return None
    return (best[1], best[2], best[3]) if best else None


def _current_point(conditions) -> Any:
    """The forecast hour containing now, not the first hour of the day."""
    if not conditions.hourly:
        return None
    now = datetime.now().replace(minute=0, second=0, microsecond=0, tzinfo=None)
    best = conditions.hourly[0]
    for point in conditions.hourly:
        stamp = point.time.replace(tzinfo=None)
        if stamp <= now:
            best = point
        else:
            break
    return best


def _sea_state(wave_m: float | None) -> tuple[int, str]:
    """Douglas sea state from significant wave height."""
    if wave_m is None:
        return 0, "Unknown"
    for index, (limit, label) in enumerate(
        [
            (0.1, "Calm (glassy)"),
            (0.5, "Calm (rippled)"),
            (1.25, "Smooth"),
            (2.5, "Slight"),
            (4.0, "Moderate"),
            (6.0, "Rough"),
            (9.0, "Very rough"),
            (14.0, "High"),
        ]
    ):
        if wave_m < limit:
            return index, label
    return 8, "Very high"


def _weather_block(point, conditions) -> dict:
    """orca-core's forecast in the console's WeatherData shape."""
    return {
        "airTemperatureC": point.air_temperature_c,
        "windSpeedKts": round((point.wind_speed_kmh or 0) * KMH_TO_KTS, 1),
        "windGustKts": round((point.wind_gusts_kmh or 0) * KMH_TO_KTS, 1),
        "windDirectionDeg": point.wind_direction_deg,
        "windDirectionCompass": compass(point.wind_direction_deg) or "—",
        "precipitationMm": point.precipitation_mm or 0.0,
        "cloudCoverPct": None,
        "visibilityKm": (
            None if point.visibility_m is None else round(point.visibility_m / 1000.0, 1)
        ),
        "pressureHpa": None,
        "weatherCode": point.weather_code,
        "weatherDescription": _weather_word(point.weather_code),
        "source": "Open-Meteo Forecast API",
        "sourceUrl": "https://open-meteo.com/",
        "observedAt": point.time.isoformat(),
        "retrievedAt": conditions.fetched_at.isoformat(),
    }


def _ocean_block(point, conditions) -> dict:
    index, label = _sea_state(point.wave_height_m)
    return {
        "waveHeightMeters": point.wave_height_m,
        "maxWaveHeightMeters": point.wave_height_m,
        "wavePeriodSec": point.wave_period_s,
        "waveDirectionDeg": point.wave_direction_deg,
        "swellHeightMeters": point.swell_height_m,
        "swellPeriodSec": point.swell_period_s,
        "swellDirectionDeg": point.swell_direction_deg,
        "seaSurfaceTemperatureC": point.sea_temperature_c,
        "currentSpeedKts": (
            None if point.current_speed_ms is None else round(point.current_speed_ms * MS_TO_KTS, 2)
        ),
        "currentDirectionDeg": point.current_direction_deg,
        "seaStateIndex": index,
        "seaStateDescription": label,
        "tidePhase": "Unknown",
        "tideHeightMeters": point.tide_height_m,
        "source": "Open-Meteo Marine API",
        "sourceUrl": "https://open-meteo.com/",
        "observedAt": point.time.isoformat(),
        "retrievedAt": conditions.fetched_at.isoformat(),
    }


_WEATHER_WORDS = {
    0: "Clear", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Depositing rime fog",
    51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain",
    80: "Rain showers", 81: "Heavy showers", 82: "Violent showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Severe thunderstorm",
}


def _weather_word(code: int | None) -> str:
    return _WEATHER_WORDS.get(code or -1, "Unknown")


# --- requests ----------------------------------------------------------------


class PointRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class QueryRequest(BaseModel):
    query: str = ""
    language: str = "en"
    sessionId: str | None = None
    # The console sends this as a *string*, in two shapes: a coastal-port key
    # such as "digha" from the port buttons, or "21.6272,87.5079" from a map
    # click. Typing it as an object rejected both with a 422, which is why
    # changing position silently did nothing — only the first load, which sends
    # no override at all, ever worked. A dict is still accepted so a caller can
    # be explicit.
    locationOverride: str | dict | None = None
    timeOverride: str | dict | None = None


class DispatchRequest(BaseModel):
    targetType: str | None = None
    mmsi: str | None = None
    name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    reason: str | None = None
    recipient: str | None = None


class RoutePoint(BaseModel):
    latitude: float
    longitude: float


class SafeRouteRequest(BaseModel):
    origin: RoutePoint
    destination: RoutePoint
    riskLevel: str | None = None
    maxNodes: int | None = None


# --- marine hazard events (the console calls this "oil spills") ---------------


@router.post("/gis/oil-spills")
async def gis_marine_events(request: PointRequest) -> dict:
    """Open marine hazard events near a position, with their drift.

    Backed by NASA EONET, which is the source HackHeritage used and one of the
    few in that stack that was genuinely live. Drift is added here from ORCA's
    own current grid — the console's type asked for it and never had it.
    """
    report = await events_tool.fetch_marine_events(request.latitude, request.longitude)
    report = await events_tool.attach_drift(report)
    return report.to_dict()


# --- vessels: an honest refusal ----------------------------------------------


@router.get("/vessels/live")
async def vessels_live(lat: float = 21.6272, lon: float = 87.5079) -> dict:
    """No AIS feed is configured, so no vessels are reported.

    The shape is preserved so the console renders an empty layer rather than
    erroring. See this module's docstring for why buoys are not returned here
    dressed as vessels.
    """
    return {
        "timestamp": _now(),
        "totalTrackedVessels": 0,
        "activeAisVessels": 0,
        "darkVesselCount": 0,
        "targetVessels": [],
        "alerts": [],
        "dataSource": "none configured",
        "warnings": [
            "ORCA has no AIS feed. Vessel positions require a live AIS source "
            "(AISStream, MarineTraffic or an equivalent), which is not wired in.",
            "No substitute targets are shown. An empty layer is the accurate one.",
        ],
    }


# --- Coast Guard dispatch: honest about not transmitting ----------------------


@router.post("/alerts/dispatch")
async def alerts_dispatch(request: DispatchRequest) -> dict:
    """Records the request. Nothing is transmitted, and it says so."""
    return {
        "status": "NOT_TRANSMITTED",
        "dispatchId": f"orca-dispatch-{int(datetime.now(timezone.utc).timestamp())}",
        "target": {
            "mmsi": request.mmsi,
            "name": request.name,
            "latitude": request.latitude,
            "longitude": request.longitude,
            "reason": request.reason,
        },
        "recipient": request.recipient or "INDIAN_COAST_GUARD_ICGS_PATROL",
        "timestamp": _now(),
        "message": (
            "ORCA has no link to Coast Guard Command Control, so nothing was sent. "
            "Use VHF Channel 16 or the Coast Guard emergency number. This entry is "
            "a local record of the request only."
        ),
    }


# --- fishing zones -----------------------------------------------------------


@router.post("/pfz/analyze")
async def pfz_analyze(request: PointRequest) -> dict:
    """Advised fishing grounds, ranked by distance, with the legal status of each.

    Every zone is a real row from today's INCOIS advisory. When INCOIS issued
    nothing for that coast, the list is empty and the reason is stated — the
    console then shows no zones, which is the truth of that day.
    """
    lat, lon = request.latitude, request.longitude
    sector = pfz_tool.sector_for_location(lat, lon)
    advisory = await pfz_tool.get_sector_advisory(sector.secid, "en")

    zones: list[dict] = []
    for index, point in enumerate(advisory.points):
        distance = ocean_tool.distance_km(lat, lon, point.latitude, point.longitude)
        fence = geofence_tool.locate(point.latitude, point.longitude)
        zones.append(
            {
                "id": f"{advisory.secid}-{index}",
                "incoisUid": f"{advisory.secid}-{point.landing_centre}-{index}",
                "latitude": point.latitude,
                "longitude": point.longitude,
                "rank": index + 1,
                # Nearer is better, and that is the whole of it. No composite
                # score is invented: INCOIS ranks nothing, and a number that
                # looks like a model output but is a distance in disguise is
                # worse than the distance itself.
                "score": max(0.0, round(100.0 - distance, 1)),
                "distanceKm": round(distance, 1),
                "distanceNm": round(distance / KM_PER_NM, 1),
                "bearingDeg": round(_bearing_deg(lat, lon, point.latitude, point.longitude)),
                "sstC": None,
                "frontLengthKm": None,
                "suitability": "HIGH" if distance < 40 else "MEDIUM" if distance < 90 else "LOW",
                "geofenceStatus": (
                    "RESTRICTED" if fence.level in ("critical", "outside") else "CLEAR"
                ),
                "explanations": [
                    f"Advised by INCOIS for {advisory.sector_name}"
                    + (f", forecast {advisory.forecast_date}" if advisory.forecast_date else ""),
                    f"{point.landing_centre}: {point.direction}"
                    + (f", {point.distance_km_from:.0f} km out" if point.distance_km_from else ""),
                    fence.message,
                ],
            }
        )

    return {
        "status": "READY" if zones else "UNAVAILABLE",
        "sector": advisory.sector_name,
        "forecastDate": advisory.forecast_date,
        "zones": zones,
        "bestZone": zones[0] if zones else None,
        "source": "INCOIS Potential Fishing Zone advisory",
        "warnings": (
            []
            if zones
            else [
                f"INCOIS issued no fishing zones for {advisory.sector_name} today. "
                "Nothing has been estimated in their place."
            ]
        ),
    }


@router.get("/pfz/frontlines")
async def pfz_frontlines() -> dict:
    """The INCOIS PFZ line geometry, as published."""
    try:
        return await pfz_tool.fetch_pfz_lines()
    except pfz_tool.PfzDataError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


# --- routing -----------------------------------------------------------------


@router.post("/routing/safe-route")
async def routing_safe_route(request: SafeRouteRequest) -> dict:
    """A passage that stays in water and steers around lightning."""
    try:
        route = await routing_tool.plan_route(
            (request.origin.latitude, request.origin.longitude),
            (request.destination.latitude, request.destination.longitude),
        )
    except Exception as exc:  # noqa: BLE001 - the console needs a shape, not a stack trace
        return {
            "status": "ROUTE_UNAVAILABLE",
            "waypointCount": 0,
            "waypoints": [],
            "warnings": [str(exc)],
            "rationale": "No passage could be planned.",
            "source": "ORCA routing over its own sea grid",
        }

    waypoints = [
        {
            "latitude": leg.to_lat,
            "longitude": leg.to_lon,
            "headingDeg": round(leg.heading_deg),
            "hazard": leg.hazard,
        }
        for leg in route.legs
    ]
    if waypoints:
        waypoints.insert(
            0,
            {
                "latitude": request.origin.latitude,
                "longitude": request.origin.longitude,
                "headingDeg": None,
                "hazard": None,
            },
        )

    return {
        "status": "ROUTE_FOUND" if waypoints else "ROUTE_UNAVAILABLE",
        "waypointCount": len(waypoints),
        "waypoints": waypoints,
        "origin": {"latitude": request.origin.latitude, "longitude": request.origin.longitude},
        "destination": {
            "latitude": request.destination.latitude,
            "longitude": request.destination.longitude,
        },
        "distanceKm": round(route.total_distance_km, 1),
        "directDistanceKm": round(route.direct_km, 1),
        "routeEfficiencyPct": (
            round(100.0 * route.direct_km / route.total_distance_km)
            if route.total_distance_km
            else None
        ),
        "avoidedConstraints": route.avoided,
        "warnings": [],
        "rationale": (
            f"{route.total_distance_km:.0f} km at {route.boat_speed_kmh:.0f} km/h, "
            f"about {route.total_hours:.1f} h"
            + (f", avoiding {', '.join(route.avoided)}" if route.avoided else "")
        ),
        "source": "ORCA routing over its own sea grid",
    }


# --- satellite ---------------------------------------------------------------


@router.post("/satellite/analysis")
async def satellite_analysis(request: PointRequest) -> dict:
    """Sea-surface temperature and chlorophyll, from the satellite records ORCA reads.

    NOAA CoastWatch, which is the source the app already uses. Its products are
    gap-filled and several days behind, and the age is reported rather than
    smoothed over — a stale observation presented as current is the failure this
    project keeps guarding against.
    """
    lat, lon = request.latitude, request.longitude
    warnings: list[str] = []
    sst_c: float | None = None
    chlorophyll: float | None = None
    observed_at: str | None = None

    try:
        sst_points = await ocean_tool.fetch_sst_points([(lat, lon)])
        nearest = ocean_tool.nearest(sst_points, lat, lon)
        if nearest is not None:
            sst_c = nearest.value
            observed_at = getattr(nearest, "observed_at", None)
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"Sea-surface temperature unavailable: {exc}")

    try:
        # A small box around the point; the grid is subsampled server-side.
        grid = await ocean_tool.fetch_chlorophyll_grid(
            lat + 0.25, lat - 0.25, lon - 0.25, lon + 0.25
        )
        nearest_chl = ocean_tool.nearest(grid, lat, lon)
        if nearest_chl is not None:
            chlorophyll = nearest_chl.value
            observed_at = observed_at or getattr(nearest_chl, "observed_at", None)
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"Chlorophyll unavailable: {exc}")

    have = sst_c is not None or chlorophyll is not None
    age_hours: float | None = None
    if isinstance(observed_at, datetime):
        seen = observed_at if observed_at.tzinfo else observed_at.replace(tzinfo=timezone.utc)
        age_hours = round((datetime.now(timezone.utc) - seen).total_seconds() / 3600.0, 1)
        observed_at = seen.isoformat()

    return {
        "status": "LIVE" if have else "UNAVAILABLE",
        "satelliteName": "NOAA CoastWatch (Geo-Polar Blended SST, VIIRS chlorophyll)",
        "processingTime": _now(),
        "latitude": lat,
        "longitude": lon,
        "sstC": sst_c,
        "chlorophyllConcentrationMgM3": chlorophyll,
        "cloudCoverPct": None,
        "confidenceScore": 80 if have else 0,
        "observationAgeHours": age_hours,
        "latestObservationAgeHours": age_hours,
        "source": "NOAA CoastWatch ERDDAP",
        "sourceUrl": "https://coastwatch.noaa.gov/erddap/",
        "observationType": "OBSERVATION" if have else "NO_OBSERVATION",
        "warnings": warnings
        + (
            []
            if age_hours is None
            else [
                f"Latest usable observation is about {age_hours:.0f} h old. "
                "These products are gap-filled for cloud and are not a nowcast."
            ]
        ),
        "observations": [],
    }


async def _resolve_override(
    override: str | dict | None,
) -> tuple[float, float, str]:
    """Turn whatever the console sent into a position.

    Three accepted forms, because the console genuinely sends three: nothing, a
    "lat,lon" pair, and a place key. The key is resolved through ORCA's own
    geocoding rather than by copying the console's hardcoded coastal table —
    two copies of a list of ports drift apart, and only one of them would be
    the one anybody edits.
    """
    default = (21.6272, 87.5079, "Digha")
    if not override:
        return default

    if isinstance(override, dict):
        try:
            return (
                float(override["latitude"]),
                float(override["longitude"]),
                str(override.get("name") or "Selected position"),
            )
        except (KeyError, TypeError, ValueError):
            return default

    text = override.strip()
    if "," in text:
        head, _, tail = text.partition(",")
        try:
            return float(head), float(tail), "Selected position"
        except ValueError:
            pass

    from .location import search_places

    try:
        places = await search_places(q=text.replace("_", " "), limit=1)
        results = places.get("results") if isinstance(places, dict) else None
        if results:
            first = results[0]
            return (
                float(first["latitude"]),
                float(first["longitude"]),
                str(first.get("name") or text.title()),
            )
    except Exception:  # noqa: BLE001 - an unresolvable name falls back, never fails
        pass
    return default


# ORCA's geofence levels, in the vocabulary the console's audio controller
# listens for. It fires the siren on CRITICAL_BREACH and speaks a warning on
# PROXIMITY_WARNING, reading `activeAlerts` first and falling back to
# `nearestImbl`/`nearestMpa`. All three were absent from the response, so the
# siren had nothing to fire on — the layer existed, worked, and was never asked.
_SEVERITY_BY_LEVEL = {
    "critical": "CRITICAL_BREACH",
    "outside": "CRITICAL_BREACH",
    "warning": "PROXIMITY_WARNING",
    "watch": "ADVISORY",
    "clear": "SAFE",
    "beyond_eez": "ADVISORY",
    "not_at_sea": "SAFE",
}


def _evidence_for(query: str) -> list[dict]:
    """Rule documents behind the answer, in the console's EvidenceItem shape.

    Reads the same corpus the app's retrieval agent uses. That corpus is small
    on purpose — a document only enters it through a fetch that returned 200 —
    so this list is often empty, and an empty list here means ORCA holds no
    rule covering the question rather than that retrieval is broken.
    """
    try:
        hits = evidence_tool.search(query or "marine safety", top_k=4)
    except Exception:  # noqa: BLE001 - evidence enriches an answer, never gates it
        return []

    items: list[dict] = []
    for hit in hits:
        document = hit.document
        items.append(
            {
                "id": document.id,
                "title": document.title,
                "sourceAuthority": document.authority,
                "documentType": "Maritime Regulation",
                "publicationDate": document.published or "",
                "excerpt": document.text[:400],
                "relevanceScore": round(min(1.0, hit.score / 10.0), 2),
                "officialUrl": document.url,
                "complianceRule": document.rule,
                # Whether this module witnessed the fetch that produced the text.
                "verified": document.verified,
            }
        )
    return items


async def _safe_route_summary(lat: float, lon: float) -> dict:
    """A passage to today's nearest advised ground, if there is one.

    The console draws this when `status` is ROUTE_FOUND and `waypoints` is
    non-empty. On a day INCOIS issues nothing for the coast there is nowhere to
    plan to, and saying so is the answer — not an empty route object that reads
    as a routing failure.
    """
    try:
        from .route import plan_default_route  # type: ignore[attr-defined]
    except ImportError:
        plan_default_route = None  # noqa: N806

    try:
        sector = pfz_tool.sector_for_location(lat, lon)
        advisory = await pfz_tool.get_sector_advisory(sector.secid, "en")
        if not advisory.points:
            return {
                "status": "ROUTE_UNAVAILABLE",
                "waypointCount": 0,
                "waypoints": [],
                "warnings": [],
                "rationale": (
                    f"INCOIS issued no fishing zones for {advisory.sector_name} today, "
                    "so there is nowhere to plan a route to."
                ),
                "source": "INCOIS Potential Fishing Zone advisory",
            }
        target = min(
            advisory.points,
            key=lambda pt: ocean_tool.distance_km(lat, lon, pt.latitude, pt.longitude),
        )
        route = await routing_tool.plan_route((lat, lon), (target.latitude, target.longitude))
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "ROUTE_UNAVAILABLE",
            "waypointCount": 0,
            "waypoints": [],
            "warnings": [str(exc)],
            "rationale": "No passage could be planned.",
            "source": "ORCA routing over its own sea grid",
        }

    waypoints = [{"latitude": lat, "longitude": lon}] + [
        {
            "latitude": leg.to_lat,
            "longitude": leg.to_lon,
            "headingDeg": round(leg.heading_deg),
            "hazard": leg.hazard,
        }
        for leg in route.legs
    ]
    return {
        "status": "ROUTE_FOUND" if route.legs else "ROUTE_UNAVAILABLE",
        "destinationLabel": target.landing_centre,
        "waypointCount": len(waypoints),
        "waypoints": waypoints,
        "origin": {"latitude": lat, "longitude": lon},
        "destination": {"latitude": target.latitude, "longitude": target.longitude},
        "distanceKm": round(route.total_distance_km, 1),
        "directDistanceKm": round(route.direct_km, 1),
        "avoidedConstraints": route.avoided,
        "warnings": [],
        "rationale": (
            f"{route.total_distance_km:.0f} km, about {route.total_hours:.1f} h"
            + (f", avoiding {', '.join(route.avoided)}" if route.avoided else "")
        ),
        "source": "ORCA routing over its own sea grid",
    }


def _geofence_analysis(lat: float, lon: float, fence) -> dict:
    """Boundary and protected-area alerts, in the console's shape.

    Every distance here is the geofence's own measurement against Marine
    Regions treaty lines and the MoEFCC polygons — the same numbers the app
    shows. The margins (5 km critical, 20 km warning, 50 km watch) are ORCA's
    stated caution bands, not a legal limit, and the message says so.
    """
    alerts: list[dict] = []
    nearest_imbl: dict | None = None
    nearest_mpa: dict | None = None

    boundary = fence.nearest_boundary
    if boundary is not None:
        severity = _SEVERITY_BY_LEVEL.get(fence.level, "SAFE")
        nearest_imbl = {
            "boundaryId": f"imbl-{boundary.line_name}",
            "boundaryName": boundary.line_name,
            "type": "IMBL",
            "distanceKm": round(boundary.distance_km, 1),
            "distanceNm": round(boundary.distance_km / KM_PER_NM, 1),
            "severity": severity,
            "warningMessage": fence.message,
            "treatyOrAuthority": geofence_tool.SOURCE,
            "isInside": fence.level in ("critical", "outside"),
            "hasCrossedBorder": fence.level == "outside",
        }
        if severity in ("CRITICAL_BREACH", "PROXIMITY_WARNING", "ADVISORY"):
            alerts.append(nearest_imbl)

    try:
        areas = closures_tool.protected_areas_near(lat, lon, within_km=WATCH_KM)
    except Exception:  # noqa: BLE001
        areas = []
    if areas:
        closest = min(areas, key=lambda a: (0.0 if a.inside else a.distance_km))
        if closest.inside:
            mpa_severity = "CRITICAL_BREACH"
            message = (
                f"You are inside {closest.name}. Fishing here may be an offence — "
                "leave the area and check the local notification."
            )
        elif closest.distance_km <= CRITICAL_KM:
            mpa_severity = "CRITICAL_BREACH"
            message = f"{closest.name} is {closest.distance_km:.1f} km away. Do not drift into it."
        elif closest.distance_km <= WARNING_KM:
            mpa_severity = "PROXIMITY_WARNING"
            message = f"{closest.name} is {closest.distance_km:.0f} km away. Keep clear."
        else:
            mpa_severity = "ADVISORY"
            message = f"{closest.name} is {closest.distance_km:.0f} km away."

        nearest_mpa = {
            "boundaryId": f"mpa-{closest.name}",
            "boundaryName": closest.name,
            "type": "MPA",
            "distanceKm": round(closest.distance_km, 1),
            "distanceNm": round(closest.distance_km / KM_PER_NM, 1),
            "severity": mpa_severity,
            "warningMessage": message,
            "treatyOrAuthority": closures_tool.MPA_SOURCE,
            "isInside": closest.inside,
        }
        if mpa_severity != "SAFE":
            alerts.append(nearest_mpa)

    return {
        "operatingCoordinates": {"latitude": lat, "longitude": lon},
        "nearestImbl": nearest_imbl,
        "nearestMpa": nearest_mpa,
        "activeAlerts": alerts,
        "inRestrictedWaters": fence.level in ("critical", "outside")
        or bool(nearest_mpa and nearest_mpa["isInside"]),
        "status": (
            "RESTRICTED_BREACH"
            if any(a["severity"] == "CRITICAL_BREACH" for a in alerts)
            else "CAUTION"
            if alerts
            else "CLEAR"
        ),
        "timestamp": _now(),
        "thresholds": {
            "criticalKm": CRITICAL_KM,
            "warningKm": WARNING_KM,
            "watchKm": WATCH_KM,
            "note": "ORCA caution margins, not a legal limit",
        },
    }


async def _gis_layers(lat: float, lon: float, fence, safe_route: dict | None = None) -> dict:
    """The map's boundary and protected-area geometry, from ORCA's own files.

    This was an empty FeatureCollection, which returned 200 and drew nothing —
    so the international boundaries, the protected areas and the safe-corridor
    layer were all simply absent from the map while every endpoint reported
    healthy. An empty list is valid JSON and renders as nothing, which is the
    hardest kind of bug to notice from a status code.

    Sources are the same files the geofence and closure checks use: Marine
    Regions EEZ v12 treaty lines, and the MoEFCC protected-area polygons.

    Buoy stations are **not** included. The console has a layer for them and
    ORCA has no buoy source — INCOIS's open ERDDAP carries ARGO floats and
    gridded satellite products but no moored wave buoys, and their positions
    are not something to copy from another repository unverified.
    """
    features: list[dict] = []

    # Boundaries and protected areas are NOT sent from here any more.
    #
    # They are fixed geometry — a treaty line and a gazetted sanctuary are the
    # same on every request — so the console now carries them in its own bundle
    # (`src/data/orcaMaritimeGeometry.ts`, generated from the same Marine Regions
    # and MoEFCC files this server reads). Sending them per query meant a few
    # hundred kilobytes of identical coordinates on every request, and the map
    # could not draw a line it already knew until the round trip returned.
    #
    # What stays here is only what actually changes with position and time:
    # hazard cells, caution margins and the planned passage.
    #
    # The authoritative containment check is unaffected and still runs on this
    # server against the unsimplified geometry — the client copy is for drawing,
    # not for deciding.

    # --- hazard zones: where the weather actually is -------------------------
    #
    # The console's original drew this as a fixed pentagon of offsets from the
    # boat, so the "hazard" followed the vessel wherever it went. ORCA already
    # computes real ones: the sea grid classifies thunderstorm and rain cells at
    # about 10 km from Open-Meteo, and a cell is where the weather is rather
    # than where the boat is.
    try:
        cells = await seagrid_tool.fetch_area(lat, lon, span_deg=1.0, side=10)
        half = (2.0 / 9.0) / 2.0  # half a cell of the grid above, in degrees
        for cell in cells:
            if not cell.is_sea or cell.hazard == "clear":
                continue
            severe = cell.hazard in ("thunderstorm", "heavy_rain")
            west, east = round(cell.longitude - half, 5), round(cell.longitude + half, 5)
            south, north = round(cell.latitude - half, 5), round(cell.latitude + half, 5)
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [west, south], [east, south], [east, north], [west, north], [west, south],
                    ]],
                },
                "properties": {
                    "name": cell.hazard.replace("_", " ").title(),
                    "category": "hazard_zone",
                    "riskLevel": "HIGH" if severe else "MODERATE",
                    "description": (
                        cell.hazard.replace("_", " ") + " forecast here"
                        + (f", {cell.precipitation_mm} mm/h" if cell.precipitation_mm else "")
                        + ". Lightning outranks rain of any intensity for an open boat."
                    ),
                    "color": "#c4372f" if severe else "#de9a1f",
                    "details": {
                        "source": "Open-Meteo forecast via ORCA sea grid",
                        "resolutionKm": 10,
                        "worstAhead48h": cell.worst_ahead,
                    },
                },
            })
    except Exception:  # noqa: BLE001 - a layer must never sink the query
        pass

    # --- precaution zones: ORCA's own caution margins -------------------------
    #
    # Not shoals. ORCA holds no bathymetry, so the "shallow shoaling zone with
    # tidal sandbar variations" the console's original drew — carrying a depth
    # that defaulted to 12 m whenever it was unknown, which was always — has no
    # basis here and is not reproduced. What is real is the margin the geofence
    # already applies: stay this far from a line that carries a consequence.
    margins: list[tuple[float, float, str]] = []
    boundary = fence.nearest_boundary
    if boundary is not None and boundary.distance_km <= WATCH_KM:
        margins.append((boundary.latitude, boundary.longitude, boundary.line_name))
    mpa_vertex = _nearest_mpa_vertex(lat, lon)
    if mpa_vertex is not None:
        margins.append(mpa_vertex)

    for m_lat, m_lon, label in margins:
        features.append({
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [_circle(m_lat, m_lon, WARNING_KM)]},
            "properties": {
                "name": "Caution margin - " + label,
                "category": "precaution_zone",
                "riskLevel": "MODERATE",
                "description": (
                    f"Within {WARNING_KM:.0f} km of {label}. This is ORCA's caution "
                    "band, not a legal limit - the limit is the line itself."
                ),
                "color": "#2c7a97",
                "details": {
                    "marginKm": WARNING_KM,
                    "source": "ORCA caution margin over Marine Regions / MoEFCC geometry",
                    "approximation": "circular; no bathymetry involved",
                },
            },
        })

    # --- safe corridor: the passage ORCA actually planned ---------------------
    #
    # Explicitly not a dredged fairway. The console's original labelled four
    # fixed offsets "Designated Fairway Channel" with an invented dredged depth
    # and channel width, which is an instruction to steer somewhere nobody
    # surveyed. This is the A* passage the router computed over the sea grid: it
    # stays in water and goes around lightning, and it says that is all it does.
    if safe_route and safe_route.get("status") == "ROUTE_FOUND":
        coords = [
            [round(w["longitude"], 5), round(w["latitude"], 5)]
            for w in (safe_route.get("waypoints") or [])
            if w.get("longitude") is not None and w.get("latitude") is not None
        ]
        if len(coords) >= 2:
            destination = safe_route.get("destinationLabel") or "the advised ground"
            features.append({
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": coords},
                "properties": {
                    "name": "ORCA suggested passage to " + str(destination),
                    "category": "safe_corridor",
                    "description": (
                        "Computed passage that stays in water and routes around "
                        "lightning. NOT a surveyed or dredged channel, and it knows "
                        "nothing about depth - sound your own water."
                    ),
                    "color": "#45bb90",
                    "details": {
                        "source": "ORCA A* routing over its own sea grid",
                        "distanceKm": safe_route.get("distanceKm"),
                        "avoided": safe_route.get("avoidedConstraints"),
                        "surveyed": False,
                        "bathymetry": "none",
                    },
                },
            })

    return {"type": "FeatureCollection", "features": features}


# --- the console's main query ------------------------------------------------


@router.post("/orca/query")
async def orca_query(request: QueryRequest) -> dict:
    """One analysis: conditions, risk, geofence, zones and a grounded answer.

    The console refuses to render unless weather, ocean and risk are all
    present, and that refusal is right — so this fails loudly with a 502 rather
    than returning a partial object the console would have to reject anyway.
    """
    lat, lon, place = await _resolve_override(request.locationOverride)

    # The forecast, the satellite record and the model's answer are three
    # independent reads. Run sequentially the console waited over a minute on a
    # spinner, most of it on a NOAA request that nothing else was waiting for.
    orchestrator = get_orchestrator()
    conditions_task = fetch_marine_conditions(lat, lon)
    satellite_task = satellite_analysis(PointRequest(latitude=lat, longitude=lon))
    answer_task = orchestrator.handle(
        question=request.query or "What are the conditions and is it safe?",
        latitude=lat,
        longitude=lon,
        ui_language=request.language or "en",
        session_id=request.sessionId,
    )
    route_task = _safe_route_summary(lat, lon)
    conditions, satellite, result, safe_route = await asyncio.gather(
        conditions_task, satellite_task, answer_task, route_task, return_exceptions=True
    )
    if isinstance(safe_route, BaseException):
        safe_route = {
            "status": "ROUTE_UNAVAILABLE",
            "waypointCount": 0,
            "waypoints": [],
            "warnings": [str(safe_route)],
            "rationale": "No passage could be planned.",
            "source": "ORCA routing over its own sea grid",
        }

    if isinstance(conditions, BaseException):
        # Without conditions there is no analysis, and the console is right to
        # refuse a partial one — so this fails loudly rather than returning an
        # object it would reject.
        raise HTTPException(status_code=502, detail=str(conditions))

    point = _current_point(conditions)
    if point is None:
        raise HTTPException(status_code=502, detail="No forecast hours were returned.")

    fence = geofence_tool.locate(lat, lon)

    if isinstance(satellite, BaseException):
        satellite = {
            "status": "UNAVAILABLE",
            "satelliteName": "NOAA CoastWatch",
            "latitude": lat,
            "longitude": lon,
            "observationType": "NO_OBSERVATION",
            "warnings": [f"Satellite record unavailable: {satellite}"],
            "observations": [],
            "source": "NOAA CoastWatch ERDDAP",
            "sourceUrl": "https://coastwatch.noaa.gov/erddap/",
            "processingTime": _now(),
        }

    payload: dict = {}
    answer = ""
    if not isinstance(result, BaseException):
        payload = result.to_dict() if hasattr(result, "to_dict") else dict(result)
        answer = payload.get("answer") or ""

    wave = point.wave_height_m or 0.0
    wind_kts = (point.wind_speed_kmh or 0.0) * KMH_TO_KTS
    storm = (point.weather_code or 0) in (95, 96, 99)

    # The verdict comes from the same reasoning that writes the answer, over the
    # same window.
    #
    # This was briefly a rule of its own reading only the current hour, and the
    # console put the two side by side: a headline of SAFE TO SAIL above a
    # paragraph saying thunderstorms were forecast and to stay in harbour. Two
    # numbers derived two ways will disagree eventually, and on a safety screen
    # the disagreement is the whole problem — a reader believes whichever one
    # they saw first. There is one assessment now, and both the badge and the
    # sentence are rendered from it.
    outlook = trip_outlook(conditions.hourly, point.time, horizon_hours=12)
    now_level, now_reasons = assess_point(point)

    if now_level == "unsafe":
        level, score = ("EXTREME" if storm else "HIGH"), 88
    elif outlook["level"] == "stop":
        level, score = "HIGH", 78
    elif outlook["level"] == "leaving_soon":
        level, score = "MODERATE", 58
    elif now_level == "caution" or outlook["level"] == "go":
        level, score = "MODERATE", 42
    else:
        level, score = "LOW", 18

    return {
        "queryId": f"orca-{int(datetime.now(timezone.utc).timestamp())}",
        "originalQuery": request.query,
        "language": request.language or "en",
        "detectedIntent": "marine_safety_advisory",
        "location": {
            "name": place,
            "country": "India",
            "latitude": lat,
            "longitude": lon,
            "regionType": "open_sea",
        },
        "timeWindow": {
            "start": point.time.isoformat(),
            "end": (point.time + timedelta(hours=12)).isoformat(),
        },
        "weather": _weather_block(point, conditions),
        "ocean": _ocean_block(point, conditions),
        "satellite": satellite,
        "risk": {
            "riskScore": score,
            "riskLevel": level,
            "confidenceScore": 85,
            # Named honestly. This is the published-threshold rule the weather
            # agent applies and cites, not a trained model — the model that used
            # to sit here had learned the same thresholds from a label computed
            # out of its own features.
            "modelVersion": "orca-thresholds-imd-incois",
            "predictionTarget": "Current sea safety at this position",
            "primaryRecommendation": outlook["headline"],
            # Both lines of the directive come from the outlook, not from the
            # model. The console renders this immediately under the headline,
            # and while they were different sources it showed "Good to go"
            # above "It is not safe now" — the deterministic reading had found
            # seven clear hours before the storms, the model had rounded that
            # to "don't". Neither is wrong; showing both as one directive is.
            # The model's answer is still returned, as groundedSummary, where
            # it belongs: it is the reply to the question that was typed.
            "safetySummary": outlook["detail"],
            "actionableAdvisories": [
                t for t in (outlook["detail"], fence.message, *now_reasons) if t
            ],
            "restrictedCraftTypes": ["Small mechanised", "Traditional craft"]
            if level in ("HIGH", "EXTREME")
            else [],
            "safeCraftTypes": [] if level in ("HIGH", "EXTREME") else ["All craft"],
            "featureContributions": [
                {
                    "featureName": "Significant wave height",
                    "featureValue": wave,
                    "unit": "m",
                    "riskWeight": 0.4,
                    "impactLevel": "HIGH" if wave >= 2.0 else "LOW",
                    "description": "INCOIS High Wave Alert triggers around 2.0 m.",
                },
                {
                    "featureName": "Sustained wind",
                    "featureValue": round(wind_kts, 1),
                    "unit": "kt",
                    "riskWeight": 0.4,
                    "impactLevel": "HIGH" if wind_kts >= 19 else "LOW",
                    "description": "IMD advises not to venture from 35 km/h (about 19 kt).",
                },
                {
                    "featureName": "Thunderstorm",
                    "featureValue": "yes" if storm else "no",
                    "unit": "",
                    "riskWeight": 0.2,
                    "impactLevel": "CRITICAL" if storm else "LOW",
                    "description": "Lightning outranks sea state for open boats.",
                },
            ],
            "validUntil": (datetime.now(timezone.utc) + timedelta(hours=6)).isoformat(),
            "generatedAt": _now(),
        },
        "gisLayers": await _gis_layers(lat, lon, fence, safe_route),
        "geofenceAnalysis": _geofence_analysis(lat, lon, fence),
        "evidence": _evidence_for(request.query),
        "agentTraces": [
            {
                "agentName": step.get("stage", "Planner"),
                "status": "completed",
                "startedAt": _now(),
                "inputSummary": request.query,
                "outputSummary": step.get("detail", ""),
                "logs": [],
            }
            for step in (payload.get("trace") or payload.get("reasoning") or [])
        ],
        "safeRoute": safe_route,
        "groundedSummary": answer,
        "operationalDecision": {
            # Named from the same outlook, so the console's decision chip and
            # its risk badge cannot tell different stories.
            "decision": {
                "EXTREME": "AVOID", "HIGH": "AVOID",
                "MODERATE": "CAUTION", "LOW": "PROCEED",
            }[level],
            "confidence": "HIGH",
            "score": 100 - score,
            "rationale": outlook["detail"],
            "factors": list(now_reasons) or ["No warning level is crossed at this hour."],
            "warnings": [w["reasons"][0] for w in outlook["hazardWindows"][:2] if w["reasons"]],
        },
        "freshnessTimestamp": conditions.fetched_at.isoformat(),
        "officialDisclaimer": DISCLAIMER,
        "sessionId": request.sessionId,
        "warnings": [],
    }


# --- speech -------------------------------------------------------------------


class SpeakRequest(BaseModel):
    text: str
    language: str = "hi"
    engine: str | None = None


@router.post("/indic-voice/tts")
async def indic_voice_tts(
    request: SpeakRequest,
    sarvam: SarvamClient = Depends(get_sarvam),
) -> dict:
    """Speech, base64 in JSON — the shape the console's audio service reads.

    The app's own route returns raw WAV bytes, which is the better transport and
    is left alone. This is the same Sarvam call with the console's envelope
    around it, rather than a second speech implementation.

    Any API keys the console sends in its body are ignored. Credentials belong
    in the server's environment, not in a request originating from a browser
    where they would be visible to anyone with developer tools open.
    """
    try:
        audio = await sarvam.text_to_speech(
            text=request.text,
            language_code=to_sarvam_code(request.language),
        )
    except SarvamError as exc:
        return {"success": False, "error": str(exc), "audioBase64": None}

    return {
        "success": True,
        "audioBase64": base64.b64encode(audio).decode("ascii"),
        "mimeType": "audio/wav",
        "engine": "sarvam",
        "language": request.language,
    }
