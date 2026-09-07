"""Cyclone endpoint — IMD's official outlook for the North Indian Ocean.

Wraps :mod:`app.tools.cyclone`. Nothing here judges whether a cyclone exists;
that is RSMC's call, and this only reports what they published, with the
bulletin's own issue time attached so a stale outlook is visible.
"""

from fastapi import APIRouter, HTTPException, Query, Response

from ..tools import cyclone

router = APIRouter(prefix="/cyclone", tags=["cyclone"])


@router.get("")
async def cyclone_outlook(
    response: Response,
    lon: float | None = Query(None, ge=-180, le=180,
                              description="Longitude, to pick the relevant basin"),
) -> dict:
    """Current systems and the 7-day chance of a new one forming."""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    try:
        outlook = await cyclone.fetch_outlook()
    except cyclone.CycloneDataError as exc:
        # An unreachable bulletin is never reported as "no cyclone".
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    payload = outlook.to_dict()
    if lon is not None:
        basin = outlook.basin_for(lon)
        payload["yourBasin"] = basin.to_dict() if basin else None
    return payload
