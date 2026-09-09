"""Potential Fishing Zone endpoints — the real INCOIS advisory, served daily.

These wrap :mod:`app.tools.pfz`. The heavy lifting (scraping, parsing, caching,
staleness) lives there; this layer only shapes HTTP responses and turns a
fisherman's coordinate into the right coastal sector.

Nothing here fabricates data. When INCOIS is unreachable and there is a previous
advisory to fall back on, it is returned with ``stale: true`` and its real
forecast date, so the map is never blank and never pretends to be current.
"""

from fastapi import APIRouter, HTTPException, Query, Response

from ..tools import pfz

router = APIRouter(prefix="/pfz", tags=["pfz"])


@router.get("/status")
async def pfz_status(response: Response) -> dict:
    """Which forecast day the current INCOIS advisory is for."""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    try:
        status = await pfz.fetch_forecast_status()
    except pfz.PfzDataError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return status.to_dict()


@router.get("/sectors")
async def pfz_sectors() -> dict:
    """The 14 INCOIS coastal sectors, for a sector picker."""
    return {
        "sectors": [
            {"secid": s.secid, "name": s.name, "centroid": list(s.centroid)}
            for s in pfz.SECTORS
        ]
    }


@router.get("/lines")
async def pfz_lines(response: Response) -> dict:
    """The PFZ line geometry the INCOIS WebGIS draws, as GeoJSON.

    Tagged with ``orca_forecast_date`` and ``orca_stale`` so the map can show
    the advisory date and warn when the geometry is a fallback.
    """
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    try:
        return await pfz.get_pfz_lines()
    except pfz.PfzDataError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/points")
async def pfz_points(response: Response, lang: str = Query("en")) -> dict:
    """Every sector's advisory rows as a GeoJSON point layer.

    This is the map's fishing-zone data: all 14 coastal sectors, scraped daily,
    each INCOIS row a point carrying its landing centre, offshore distance,
    depth band and bearing. Nothing here is invented — if INCOIS issued no zones
    for a stretch of coast, that coast simply has no points.
    """
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    advisories = await pfz.fetch_all_advisories(lang)
    if not advisories:
        raise HTTPException(status_code=502, detail="Could not reach INCOIS")
    return pfz.build_points_geojson(advisories)


@router.get("/sector/{secid}")
async def pfz_sector(secid: str, lang: str = Query("en")) -> dict:
    """The full advisory table for one named sector, in one language."""
    try:
        advisory = await pfz.get_sector_advisory(secid, lang)
    except pfz.PfzDataError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return advisory.to_dict()


@router.get("/advisory")
async def pfz_advisory(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    lang: str = Query("en"),
) -> dict:
    """The advisory for whichever sector is nearest a fisherman's position.

    This is the endpoint the Find Fish screen calls: it hands over a location
    and gets back the government's own fishing-zone list for that coast, with
    each zone already converted to a map coordinate.
    """
    sector = pfz.sector_for_location(lat, lon)
    try:
        advisory = await pfz.get_sector_advisory(sector.secid, lang)
    except pfz.PfzDataError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    result = advisory.to_dict()
    # Order the zones by distance from the user so the nearest ground is first —
    # the same "closest is best, all else equal" a fisherman would apply.
    for point in result["points"]:
        point["range_km"] = round(
            pfz._haversine_km(lat, lon, point["latitude"], point["longitude"]), 1
        )
    result["points"].sort(key=lambda p: p["range_km"])
    result["origin"] = {"latitude": lat, "longitude": lon}
    return result


@router.post("/refresh")
async def pfz_refresh() -> dict:
    """Force a re-scrape of every sector now. Backs the daily scheduler."""
    return await pfz.refresh_all(force=True)
