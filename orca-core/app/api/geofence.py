"""Maritime boundary endpoints — location checks and map geometry.

Backs the boundary badge on the map and anything else that needs to know how
close a boat is to a foreign maritime line. The geometry lives on disk
(Marine Regions v12), so unlike the forecast endpoints this one keeps working
with no internet connection — which is precisely when a boat is at sea.
"""

import json

from fastapi import APIRouter, HTTPException, Query, Response

from ..tools import geofence

router = APIRouter(prefix="/geofence", tags=["geofence"])


@router.get("")
async def where_am_i(
    response: Response,
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
) -> dict:
    """Where a position stands relative to India's EEZ and its neighbours."""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    try:
        return geofence.locate(lat, lon).to_dict()
    except geofence.GeofenceDataError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/boundaries")
async def boundary_geometry(response: Response) -> dict:
    """Treaty/IMBL line GeoJSON for the map, loaded from ORCA's source file."""
    response.headers["Cache-Control"] = "public, max-age=3600"
    if not geofence.BOUNDARIES_PATH.exists():
        raise HTTPException(status_code=503, detail="Maritime boundary layer is not installed")
    with geofence.BOUNDARIES_PATH.open(encoding="utf-8") as handle:
        data = json.load(handle)
    data["orca_source"] = geofence.SOURCE
    data["orca_count"] = len(data.get("features", []))
    return data
