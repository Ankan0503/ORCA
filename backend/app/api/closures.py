"""Fishing closures — the annual ban and protected areas, for the map.

Serves the two things a boat can break without the weather being any warning at
all: sailing during the 61-day ban, and entering a marine protected area.

The protected-area layer reports its own size. It is only as complete as the
MoEFCC dataset behind it, and a geofence that quietly knows about a handful of
sanctuaries must not be mistaken for one that knows them all.
"""

import json

from fastapi import APIRouter, Query, Response

from ..tools import closures

router = APIRouter(prefix="/closures", tags=["closures"])


@router.get("/ban")
async def fishing_ban(
    response: Response,
    lon: float = Query(..., ge=-180, le=180, description="Longitude picks the coast"),
) -> dict:
    """Whether the annual fishing ban applies today at this coast."""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return closures.ban_status(lon).to_dict()


@router.get("/protected-areas")
async def protected_areas(response: Response) -> dict:
    """Marine protected areas as GeoJSON, for drawing on the map."""
    response.headers["Cache-Control"] = "public, max-age=3600"
    if not closures.MPA_PATH.exists():
        return {
            "type": "FeatureCollection",
            "features": [],
            "orca_count": 0,
            "orca_note": "No protected-area layer is installed.",
        }

    with closures.MPA_PATH.open(encoding="utf-8") as handle:
        data = json.load(handle)
    data["orca_count"] = len(data.get("features", []))
    data["orca_source"] = closures.MPA_SOURCE
    return data


@router.get("/check")
async def check_position(
    response: Response,
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    within_km: float = Query(25.0, ge=0, le=200),
) -> dict:
    """Is this position inside — or close to — a protected area, and is the ban on?"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    areas = closures.protected_areas_near(lat, lon, within_km=within_km)
    return {
        "fishingBan": closures.ban_status(lon).to_dict(),
        "insideProtectedArea": any(a.inside for a in areas),
        "areas": [a.to_dict() for a in areas],
        "layerCount": closures.protected_area_count(),
        "coverageNote": (
            "India has roughly 130 marine protected areas; this layer holds "
            f"{closures.protected_area_count()}. No warning here is not proof of open water."
        ),
    }
