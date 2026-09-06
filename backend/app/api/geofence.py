"""Maritime boundary endpoint — is this position inside Indian waters?

Backs the boundary badge on the map and anything else that needs to know how
close a boat is to a foreign maritime line. The geometry lives on disk
(Marine Regions v12), so unlike the forecast endpoints this one keeps working
with no internet connection — which is precisely when a boat is at sea.
"""

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
