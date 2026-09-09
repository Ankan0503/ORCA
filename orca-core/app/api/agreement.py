"""Where the forecasts disagree, and whether the disagreement matters.

Exposed as its own route rather than folded into `/conditions` because it
answers a different question. `/conditions` says what the sea is doing;
this says how much to trust that answer.
"""

from fastapi import APIRouter, HTTPException, Query, Response

from ..tools import agreement

router = APIRouter(prefix="/agreement", tags=["agreement"])


@router.get("")
async def forecast_agreement(
    response: Response,
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    hoursAhead: int = Query(0, ge=0, le=47, description="Lead time, in hours from now"),
) -> dict:
    """Compare independent forecast models at one point and one lead time."""
    # Model runs land on their own schedules, so a cached comparison can be
    # stale in a way a single forecast is not.
    response.headers["Cache-Control"] = "public, max-age=900"
    try:
        report = await agreement.compare_forecasts(lat, lon, hours_ahead=hoursAhead)
    except agreement.AgreementError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return report.to_dict()
