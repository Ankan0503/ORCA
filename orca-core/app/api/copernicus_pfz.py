"""Copernicus Marine PFZ endpoints — daily cloud-bypass PFZ predictions for India's EEZ.

This wraps the pre-computed JSON from the daily pipeline (run at 02:00 IST).
The endpoint filters by bbox for map viewport efficiency.
"""

from fastapi import APIRouter, HTTPException, Query, Response
from ..config import get_settings

router = APIRouter(prefix="/copernicus-pfz", tags=["copernicus-pfz"])


@router.get("")
async def get_copernicus_pfz(
    response: Response,
    min_lon: float = Query(..., ge=-180, le=180),
    min_lat: float = Query(..., ge=-90, le=90),
    max_lon: float = Query(..., ge=-180, le=180),
    max_lat: float = Query(..., ge=-90, le=90),
) -> dict:
    """Return PFZ points within bbox as GeoJSON FeatureCollection.

    The source JSON is generated daily by the 02:00 IST pipeline.
    Returns cached file filtered to the requested bounding box.
    """
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"

    settings = get_settings()
    import json
    from pathlib import Path

    output_path = Path(settings.copernicus_pfz_output)
    if not output_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Copernicus PFZ data not yet generated. Pipeline runs daily at 02:00 IST."
        )

    try:
        with open(output_path) as f:
            data = json.load(f)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load PFZ data: {exc}") from exc

    # Filter features by bbox
    features = data.get("features", [])
    filtered = []
    for feat in features:
        coords = feat.get("geometry", {}).get("coordinates", [])
        if len(coords) >= 2:
            lon, lat = coords[0], coords[1]
            if min_lon <= lon <= max_lon and min_lat <= lat <= max_lat:
                filtered.append(feat)

    return {
        "type": "FeatureCollection",
        "features": filtered,
        "metadata": data.get("metadata", {}),
    }


@router.get("/status")
async def copernicus_pfz_status(response: Response) -> dict:
    """Status of the latest Copernicus PFZ generation."""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"

    settings = get_settings()
    import json
    from pathlib import Path

    output_path = Path(settings.copernicus_pfz_output)
    if not output_path.exists():
        return {
            "status": "NOT_GENERATED",
            "message": "Pipeline has not run yet. Runs daily at 02:00 IST.",
        }

    try:
        with open(output_path) as f:
            data = json.load(f)
        meta = data.get("metadata", {})
        return {
            "status": "READY",
            "generated_at_ist": meta.get("generated_at_ist"),
            "forecast_date": meta.get("forecast_date"),
            "tier": meta.get("tier"),
            "cloud_bypass_active": meta.get("cloud_bypass_active"),
            "sources_used": meta.get("sources_used"),
            "points_count": meta.get("points_count"),
        }
    except Exception as exc:
        return {
            "status": "ERROR",
            "message": f"Failed to read status: {exc}",
        }