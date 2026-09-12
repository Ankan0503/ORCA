"""The satellite fishing zones, as published — readable without the pipeline.

The Copernicus pipeline detects thermal and biological fronts across India's EEZ
and writes them to disk once a day. ``copernicus_pfz.py`` does that work and
imports numpy and xarray to do it; **this module deliberately does not import
it.** It reads the published file with nothing but ``json``.

That separation is not stylistic. The deployed host installs neither numpy nor
xarray, and an agent that reached the pipeline module would take the whole
service down at import — which is exactly what happened once already, and why the
API endpoint reads the same file the same plain way.

What this adds over the INCOIS advisory in ``pfz.py``: INCOIS publishes one
bulletin per coastal sector, daily, and misses when the sky is cloudy. These
zones are derived independently, survive cloud through sea-surface-height
advection, and cover the whole EEZ. They are an **estimate** and are labelled so
wherever they surface — an official advisory they are not.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

from ..config import get_settings

EARTH_RADIUS_KM = 6371.0

#: Confidence as the pipeline grades it, best first.
_CONFIDENCE_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}

SOURCE = "Copernicus Marine (CMEMS) thermal and biological fronts — ORCA estimate"


@dataclass(frozen=True)
class SatelliteZone:
    latitude: float
    longitude: float
    distance_km: float
    bearing: str
    confidence: str
    source: str
    sst_c: float | None = None
    chlorophyll_mg_m3: float | None = None
    front_strength_c: float | None = None
    cloud_bypass: bool = False
    advection_hours: float | None = None

    @property
    def is_estimate(self) -> bool:
        """Always. Nothing here is a government advisory."""
        return True


_COMPASS = (
    "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
)


def _distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def _bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> str:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    degrees = (math.degrees(math.atan2(y, x)) + 360) % 360
    return _COMPASS[int((degrees + 11.25) % 360 / 22.5)]


_cache: tuple[float, dict] | None = None


def _published() -> dict:
    """The published file, re-read when it changes on disk.

    An absent or unreadable file is an empty result, never an exception: the
    pipeline is a daily background job and the answer must survive it not having
    run.
    """
    global _cache
    path = Path(get_settings().copernicus_pfz_output)
    try:
        stamp = path.stat().st_mtime
    except OSError:
        return {}
    if _cache is not None and _cache[0] == stamp:
        return _cache[1]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    _cache = (stamp, data)
    return data


def metadata() -> dict:
    """Which satellite passes went into the published zones, and when."""
    return _published().get("metadata", {})


def nearest_zones(
    latitude: float,
    longitude: float,
    limit: int = 3,
    max_km: float = 200.0,
) -> list[SatelliteZone]:
    """The closest published zones to a position, nearest first.

    Ranked by distance, then by confidence, so a HIGH zone a kilometre further
    out is not buried under a LOW one. Anything beyond `max_km` is dropped rather
    than offered — a front three hundred kilometres away is not a fishing
    suggestion for a day boat.
    """
    features = _published().get("features") or []
    zones: list[SatelliteZone] = []

    for feature in features:
        props = feature.get("properties") or {}
        lat, lon = props.get("latitude"), props.get("longitude")
        if lat is None or lon is None:
            coords = (feature.get("geometry") or {}).get("coordinates") or []
            if len(coords) < 2:
                continue
            lon, lat = coords[0], coords[1]

        km = _distance_km(latitude, longitude, float(lat), float(lon))
        if km > max_km:
            continue

        zones.append(
            SatelliteZone(
                latitude=float(lat),
                longitude=float(lon),
                distance_km=round(km, 1),
                bearing=_bearing(latitude, longitude, float(lat), float(lon)),
                confidence=str(props.get("confidence") or "UNKNOWN"),
                source=str(props.get("source") or "front"),
                sst_c=props.get("sst_c"),
                chlorophyll_mg_m3=props.get("chlorophyll_mg_m3"),
                front_strength_c=props.get("front_strength_c"),
                cloud_bypass=bool(props.get("cloud_bypass")),
                advection_hours=props.get("advection_hours"),
            )
        )

    zones.sort(key=lambda z: (z.distance_km, _CONFIDENCE_ORDER.get(z.confidence, 9)))
    return zones[:limit]
