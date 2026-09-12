"""Where a boat is, relative to India's maritime limits.

Two questions matter to a fisherman and neither is answered by a forecast:

1. Am I still inside India's Exclusive Economic Zone?
2. How close is the nearest *foreign* maritime boundary, and whose is it?

The second is not academic. Crossing into Sri Lankan or Pakistani waters is one
of the most common ways Indian fishermen are arrested, and it happens by drift
and by chasing a shoal, not by intent. A boat that knows it is 6 km from the
Sri Lankan line can turn before it becomes an international incident.

Both answers come from Marine Regions v12 (the same authority behind the EEZ
already drawn on the map), held in ``data/geo``:

- ``india_eez.geojson`` — the EEZ polygons, used for containment.
- ``india_eez_boundaries.geojson`` — 32 treaty boundary lines, each naming the
  two territories it separates, used for proximity.

Distances are great-circle to the nearest point on a boundary *segment*, not to
the nearest vertex, so a long straight treaty line does not read as far away
just because its endpoints are.

The proximity thresholds are ORCA's own caution margins, not a legal standard.
They are stated as such wherever they are surfaced.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "geo"
EEZ_PATH = DATA_DIR / "india_eez.geojson"
BOUNDARIES_PATH = DATA_DIR / "india_eez_boundaries.geojson"

SOURCE = "Marine Regions EEZ v12"

EARTH_RADIUS_KM = 6371.0

# How close to a foreign maritime boundary before ORCA speaks up. These are
# ORCA's own margins — deliberately generous, because a drifting boat closes a
# few kilometres without anyone noticing — not a legal limit.
CRITICAL_KM = 5.0
WARNING_KM = 20.0
WATCH_KM = 50.0

_COMPASS = (
    "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
)


class GeofenceDataError(RuntimeError):
    """Raised when the boundary data cannot be loaded."""


@dataclass
class NearestBoundary:
    """The closest stretch of an international maritime boundary."""

    line_name: str
    neighbour: str
    line_type: str
    distance_km: float
    bearing: str
    latitude: float
    longitude: float


@dataclass
class GeofenceResult:
    latitude: float
    longitude: float
    inside_eez: bool
    zone: str | None
    nearest_boundary: NearestBoundary | None
    # "clear" | "watch" | "warning" | "critical" | "outside"
    level: str
    message: str

    def to_dict(self) -> dict:
        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "insideEez": self.inside_eez,
            "zone": self.zone,
            "level": self.level,
            "message": self.message,
            "source": SOURCE,
            "thresholds": {
                "criticalKm": CRITICAL_KM,
                "warningKm": WARNING_KM,
                "watchKm": WATCH_KM,
                "note": "ORCA caution margins, not a legal limit",
            },
            "nearestBoundary": None
            if self.nearest_boundary is None
            else {
                "lineName": self.nearest_boundary.line_name,
                "neighbour": self.nearest_boundary.neighbour,
                "lineType": self.nearest_boundary.line_type,
                "distanceKm": round(self.nearest_boundary.distance_km, 1),
                "bearing": self.nearest_boundary.bearing,
                "latitude": round(self.nearest_boundary.latitude, 5),
                "longitude": round(self.nearest_boundary.longitude, 5),
            },
        }


# --- Geometry ---------------------------------------------------------------


def _bearing_compass(lat1: float, lon1: float, lat2: float, lon2: float) -> str:
    dlon = math.radians(lon2 - lon1)
    y = math.sin(dlon) * math.cos(math.radians(lat2))
    x = math.cos(math.radians(lat1)) * math.sin(math.radians(lat2)) - math.sin(
        math.radians(lat1)
    ) * math.cos(math.radians(lat2)) * math.cos(dlon)
    degrees = (math.degrees(math.atan2(y, x)) + 360) % 360
    return _COMPASS[int(degrees / 22.5 + 0.5) % 16]


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _closest_point_on_segment(
    lat: float, lon: float, lat1: float, lon1: float, lat2: float, lon2: float
) -> tuple[float, float]:
    """Nearest point on a segment, in a local flat projection.

    Longitude is scaled by cos(latitude) so a degree east is worth the same as a
    degree north near the point of interest. Over a boundary segment — tens of
    kilometres — that approximation is accurate to a few metres, far finer than
    any decision made from it.
    """
    scale = math.cos(math.radians(lat)) or 1e-9
    px, py = lon * scale, lat
    ax, ay = lon1 * scale, lat1
    bx, by = lon2 * scale, lat2

    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return lat1, lon1

    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    return ay + t * dy, (ax + t * dx) / scale


def _point_in_ring(lat: float, lon: float, ring: list) -> bool:
    """Ray-casting test. `ring` is GeoJSON [lon, lat] pairs."""
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > lat) != (yj > lat):
            x_cross = (xj - xi) * (lat - yi) / (yj - yi) + xi
            if lon < x_cross:
                inside = not inside
        j = i
    return inside


def _point_in_polygon(lat: float, lon: float, polygon: list) -> bool:
    """A GeoJSON polygon: first ring is the outer edge, the rest are holes."""
    if not polygon or not _point_in_ring(lat, lon, polygon[0]):
        return False
    return not any(_point_in_ring(lat, lon, hole) for hole in polygon[1:])


# --- Data loading -----------------------------------------------------------


@lru_cache(maxsize=1)
def _load_zones() -> list[tuple[str, list, tuple[float, float, float, float]]]:
    """EEZ polygons with a bounding box each, so most are skipped instantly."""
    if not EEZ_PATH.exists():
        raise GeofenceDataError(f"EEZ data missing at {EEZ_PATH}")

    with EEZ_PATH.open(encoding="utf-8") as handle:
        data = json.load(handle)

    zones: list[tuple[str, list, tuple[float, float, float, float]]] = []
    for feature in data.get("features", []):
        props = feature.get("properties") or {}
        name = props.get("GEONAME") or props.get("geoname") or "Indian EEZ"
        geometry = feature.get("geometry") or {}
        polygons = (
            [geometry.get("coordinates")]
            if geometry.get("type") == "Polygon"
            else geometry.get("coordinates") or []
        )
        for polygon in polygons:
            if not polygon:
                continue
            outer = polygon[0]
            lons = [p[0] for p in outer]
            lats = [p[1] for p in outer]
            zones.append((name, polygon, (min(lats), max(lats), min(lons), max(lons))))
    return zones


@lru_cache(maxsize=1)
def _load_boundaries() -> list[dict]:
    """International boundary lines, each flattened to its segments."""
    if not BOUNDARIES_PATH.exists():
        raise GeofenceDataError(f"Boundary data missing at {BOUNDARIES_PATH}")

    with BOUNDARIES_PATH.open(encoding="utf-8") as handle:
        data = json.load(handle)

    lines: list[dict] = []
    for feature in data.get("features", []):
        props = feature.get("properties") or {}
        geometry = feature.get("geometry") or {}
        parts = (
            [geometry.get("coordinates")]
            if geometry.get("type") == "LineString"
            else geometry.get("coordinates") or []
        )

        # Only a line with two different sovereigns is a *foreign* boundary. The
        # dataset also carries India's own straight baselines and its 200 NM
        # outer limit, which have no second sovereign — naming those as "the
        # nearest foreign boundary (India)" would be nonsense, so they are
        # classified separately.
        t1 = (props.get("TERRITORY1") or "").strip()
        t2 = (props.get("TERRITORY2") or "").strip()
        s1 = (props.get("SOVEREIGN1") or "").strip()
        s2 = (props.get("SOVEREIGN2") or "").strip()
        line_type = props.get("LINE_TYPE") or "Boundary"

        is_foreign = bool(s1 and s2 and s1.lower() != s2.lower())
        if is_foreign:
            neighbour = t1 if s1.lower() != "india" else t2
        else:
            neighbour = ""

        for coords in parts:
            if not coords or len(coords) < 2:
                continue
            lats = [p[1] for p in coords]
            lons = [p[0] for p in coords]
            lines.append(
                {
                    "line_name": props.get("LINE_NAME") or "Maritime boundary",
                    "line_type": line_type,
                    "neighbour": neighbour,
                    "is_foreign": is_foreign,
                    "is_outer_limit": line_type.strip().upper() == "200 NM",
                    "coords": coords,
                    "bbox": (min(lats), max(lats), min(lons), max(lons)),
                }
            )
    return lines


def preload() -> dict:
    """Parse both datasets up front so the first request is not the slow one."""
    zones = _load_zones()
    lines = _load_boundaries()
    return {"polygons": len(zones), "boundaryLines": len(lines)}


# --- Public API -------------------------------------------------------------


def _inside(lat: float, lon: float) -> tuple[bool, str | None]:
    for name, polygon, (min_lat, max_lat, min_lon, max_lon) in _load_zones():
        if not (min_lat <= lat <= max_lat and min_lon <= lon <= max_lon):
            continue
        if _point_in_polygon(lat, lon, polygon):
            return True, name
    return False, None


_BAND_DEG = 0.05


@lru_cache(maxsize=1)
def _edge_bands() -> list[tuple[tuple[float, float, float, float], dict[int, list[tuple[float, float, float, float]]]]]:
    """Each polygon's edges bucketed by latitude band, so a point only tests the edges beside it."""
    indexed = []
    for _name, polygon, bbox in _load_zones():
        bands: dict[int, list[tuple[float, float, float, float]]] = {}
        for ring in polygon:
            for i in range(len(ring)):
                x1, y1 = ring[i - 1][0], ring[i - 1][1]
                x2, y2 = ring[i][0], ring[i][1]
                if y1 == y2:
                    continue
                for band in range(int(min(y1, y2) // _BAND_DEG), int(max(y1, y2) // _BAND_DEG) + 1):
                    bands.setdefault(band, []).append((x1, y1, x2, y2))
        indexed.append((bbox, bands))
    return indexed


def in_indian_waters(latitude: float, longitude: float) -> bool:
    """Same answer as `inside_eez`, from the banded index: fast enough to test every route leg."""
    for (min_lat, max_lat, min_lon, max_lon), bands in _edge_bands():
        if not (min_lat <= latitude <= max_lat and min_lon <= longitude <= max_lon):
            continue
        inside = False
        for x1, y1, x2, y2 in bands.get(int(latitude // _BAND_DEG), ()):
            if (y1 > latitude) != (y2 > latitude) and longitude < (x2 - x1) * (latitude - y1) / (y2 - y1) + x1:
                inside = not inside
        if inside:
            return True
    return False


def is_navigable(latitude: float, longitude: float) -> bool:
    """Water a boat may use: inside India's EEZ. Assumed so when the boundary data is missing."""
    try:
        return in_indian_waters(latitude, longitude)
    except GeofenceDataError:
        return True


def inside_eez(latitude: float, longitude: float) -> bool:
    """Whether a position lies inside India's EEZ.

    Exposed for layers that should stop at the national limit — current arrows
    drawn across a neighbour's water are clutter at best and a claim ORCA has no
    business making at worst.
    """
    try:
        return _inside(latitude, longitude)[0]
    except GeofenceDataError:
        # Without the boundary file, do not silently erase the whole layer.
        return True


def is_at_sea(latitude: float, longitude: float) -> bool:
    """Is this coordinate on water, by ORCA's own geometry?

    Added because the map hazard grid used to decide this by asking whether the
    ocean-current model returned a velocity, and that model goes null nearshore.
    The coastline — the only part of the map an artisanal fisherman is ever in —
    was therefore the exact part being deleted. A single measurement on the grid
    around Digha discarded 44 of 81 cells, 29 of which were raining.

    Two cases count as water:

      - inside the EEZ polygon, which is unambiguous;
      - outside it but seaward of India's own straight baselines, which is
        another country's water or the high seas. Rain there is still worth
        drawing, because weather arrives from somewhere.

    A harbour, a river mouth or anywhere inland is nearer the baseline than the
    200 NM limit and is excluded. This is the same geometry ``locate`` already
    uses to tell someone they are not at sea, so the map and the advisory now
    agree about where the water is.
    """
    if inside_eez(latitude, longitude):
        return True
    return _is_seaward(latitude, longitude)


def _nearest_line(lat: float, lon: float, predicate) -> NearestBoundary | None:
    """Nearest boundary line matching `predicate`, by distance to its segments."""
    best: NearestBoundary | None = None
    best_km = float("inf")

    # A degree of latitude is ~111 km, so this window comfortably contains any
    # boundary that could be the nearest without scanning the whole Indian Ocean.
    for line in _load_boundaries():
        if not predicate(line):
            continue
        min_lat, max_lat, min_lon, max_lon = line["bbox"]
        # Cheap rejection: if the line's box is further than the best distance
        # found so far, it cannot win.
        if best_km < float("inf"):
            margin = best_km / 111.0 + 0.5
            if (
                lat < min_lat - margin
                or lat > max_lat + margin
                or lon < min_lon - margin
                or lon > max_lon + margin
            ):
                continue

        coords = line["coords"]
        for i in range(len(coords) - 1):
            lon1, lat1 = coords[i][0], coords[i][1]
            lon2, lat2 = coords[i + 1][0], coords[i + 1][1]
            near_lat, near_lon = _closest_point_on_segment(lat, lon, lat1, lon1, lat2, lon2)
            km = _haversine_km(lat, lon, near_lat, near_lon)
            if km < best_km:
                best_km = km
                best = NearestBoundary(
                    line_name=line["line_name"],
                    neighbour=line["neighbour"],
                    line_type=line["line_type"],
                    distance_km=km,
                    bearing=_bearing_compass(lat, lon, near_lat, near_lon),
                    latitude=near_lat,
                    longitude=near_lon,
                )
    return best


def _nearest_foreign(lat: float, lon: float) -> NearestBoundary | None:
    return _nearest_line(lat, lon, lambda line: line["is_foreign"])


def _nearest_outer_limit(lat: float, lon: float) -> NearestBoundary | None:
    return _nearest_line(lat, lon, lambda line: line["is_outer_limit"])


def _nearest_baseline(lat: float, lon: float) -> NearestBoundary | None:
    return _nearest_line(
        lat, lon, lambda line: line["line_type"].strip().lower() == "straight baseline"
    )


def _is_seaward(lat: float, lon: float) -> bool:
    """For a point outside the EEZ: is it out past the 200 NM limit, or inland?

    India's own straight baselines hug the coast and its 200 NM line marks the
    outer edge of the EEZ, so whichever of the two is nearer says which side the
    point fell off. A harbour is nearer the baseline; open ocean beyond the zone
    is nearer the 200 NM limit. This is a real geometric test rather than a
    guess about the coastline.
    """
    outer = _nearest_outer_limit(lat, lon)
    baseline = _nearest_baseline(lat, lon)
    if outer is None:
        return False
    if baseline is None:
        return True
    return outer.distance_km < baseline.distance_km


# Outside the EEZ polygon but with no foreign boundary within this range, a
# position is far more likely to be on land or in internal waters (a harbour,
# a river mouth, Palk Bay) than adrift in another country's sea. Telling someone
# standing on the beach at Digha to "head back to Indian waters" would be both
# wrong and alarming, so those two cases are reported differently.
FOREIGN_WATER_RANGE_KM = 150.0


@lru_cache(maxsize=2048)
def _locate_cached(lat_key: float, lon_key: float) -> GeofenceResult:
    lat, lon = lat_key, lon_key
    inside, zone = _inside(lat, lon)
    nearest = _nearest_foreign(lat, lon)

    if not inside:
        if nearest is not None and nearest.distance_km <= FOREIGN_WATER_RANGE_KM:
            level = "outside"
            message = (
                f"This position is outside India's EEZ, near the {nearest.neighbour} "
                f"boundary ({nearest.distance_km:.0f} km to the {nearest.bearing}). "
                "Head back towards Indian waters."
            )
        elif _is_seaward(lat, lon):
            level = "beyond_eez"
            outer = _nearest_outer_limit(lat, lon)
            how_far = (
                f" You are about {outer.distance_km:.0f} km past the 200 nautical mile "
                f"limit, which lies to the {outer.bearing}."
                if outer
                else ""
            )
            message = (
                "This position is beyond the outer edge of India's EEZ, in international "
                f"waters.{how_far} Indian rules and rescue cover do not extend here."
            )
        else:
            # Landward of the baseline: a harbour, the coast, or inland.
            level = "not_at_sea"
            message = (
                "This position is not inside India's sea area — it is most likely on "
                "land or in internal waters such as a harbour or bay."
            )
    elif nearest is None:
        level = "clear"
        message = "You are inside India's EEZ."
    elif nearest.distance_km <= CRITICAL_KM:
        level = "critical"
        message = (
            f"You are very close to the {nearest.neighbour} maritime boundary — "
            f"{nearest.distance_km:.1f} km to the {nearest.bearing}. Turn away now."
        )
    elif nearest.distance_km <= WARNING_KM:
        level = "warning"
        message = (
            f"The {nearest.neighbour} maritime boundary is {nearest.distance_km:.0f} km "
            f"to the {nearest.bearing}. Do not drift further that way."
        )
    elif nearest.distance_km <= WATCH_KM:
        level = "watch"
        message = (
            f"You are inside India's EEZ. The {nearest.neighbour} boundary is "
            f"{nearest.distance_km:.0f} km to the {nearest.bearing}."
        )
    else:
        level = "clear"
        message = (
            f"You are well inside India's EEZ. The nearest foreign boundary "
            f"({nearest.neighbour}) is {nearest.distance_km:.0f} km to the {nearest.bearing}."
        )

    return GeofenceResult(
        latitude=lat,
        longitude=lon,
        inside_eez=inside,
        zone=zone,
        nearest_boundary=nearest,
        level=level,
        message=message,
    )


def locate(latitude: float, longitude: float) -> GeofenceResult:
    """Where this position stands relative to India's maritime limits.

    Results are cached on a ~100 m grid: a boat reporting its position
    repeatedly does not re-scan the boundary set for every metre it moves.
    """
    return _locate_cached(round(latitude, 3), round(longitude, 3))
