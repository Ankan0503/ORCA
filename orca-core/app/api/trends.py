"""Ten years of the sea at one place, for the trend chart and the agent.

Kept as its own endpoint rather than folded into /conditions: this fetches
roughly thirty upstream requests across three archives and takes seconds, where
/conditions must stay fast enough for the safety banner.
"""

from fastapi import APIRouter, HTTPException, Query, Response

from ..tools.history import DEFAULT_YEARS, HistoryDataError, fetch_season_history

router = APIRouter(prefix="/trends", tags=["trends"])


@router.get("")
async def get_trends(
    response: Response,
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    years: int = Query(DEFAULT_YEARS, ge=3, le=20),
) -> dict:
    """Seasonal means for the same weeks of every year, with the trend through them.

    Cached for an hour: the underlying archives publish daily at best, and a
    decade of reanalysis does not change between two page loads.
    """
    response.headers["Cache-Control"] = "public, max-age=3600"

    try:
        history = await fetch_season_history(lat, lon, years=years)
    except HistoryDataError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return history.to_dict()
