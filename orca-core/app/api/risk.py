"""Overall trip risk — the combined verdict.

Wraps :class:`~app.agents.risk.RiskAssessmentAgent` so a screen can ask "should
I go?" directly, without going through the conversational orchestrator. The
agent does the combining; this layer only shapes the response.
"""

from fastapi import APIRouter, Query, Response

from ..agents.base import QueryContext
from ..agents.risk import RiskAssessmentAgent

router = APIRouter(prefix="/risk", tags=["risk"])

_agent = RiskAssessmentAgent()


@router.get("")
async def assess_risk(
    response: Response,
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    lang: str = Query("en"),
) -> dict:
    """Sea safety, boundary proximity and trip reachability as one verdict."""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    result = await _agent.run(
        QueryContext(
            question="What is the overall risk of going out?",
            language=lang,
            latitude=lat,
            longitude=lon,
        )
    )
    return result.to_dict()
