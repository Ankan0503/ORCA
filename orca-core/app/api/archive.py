"""What the scrapers have kept.

Read-only. Nothing here fetches, and nothing writes — records appear because
the advisory and bulletin scrapers already ran, not because this was called.
"""

from fastapi import APIRouter, Query, Response

from .. import archive as store

router = APIRouter(prefix="/archive", tags=["archive"])


@router.get("/stats")
async def archive_stats(response: Response) -> dict:
    """How much history exists, and how many distinct days it spans.

    The day count is the number that matters. A hundred rows across two days is
    not a time series, and the difference decides whether anything can yet be
    learned from what has accumulated.
    """
    response.headers["Cache-Control"] = "no-store"
    return store.stats()


@router.get("/history")
async def archive_history(
    response: Response,
    kind: str = Query(..., description="pfz_advisory | pfz_status | cyclone_outlook"),
    key: str | None = Query(None, description="Sector id for PFZ records"),
    since: str | None = Query(None, description="ISO date, inclusive"),
    limit: int = Query(50, ge=1, le=1000),
) -> dict:
    """Records of one kind, newest day first."""
    response.headers["Cache-Control"] = "no-store"
    records = store.history(kind, key=key, since=since, limit=limit)
    return {"kind": kind, "key": key, "count": len(records), "records": records}


@router.get("/export")
async def archive_export(response: Response, kind: str | None = None) -> dict:
    """Everything, for pulling out before an ephemeral host discards it.

    The backend's current host does not keep files across a restart or a
    redeploy, so this is the escape hatch: collect for a while, export, keep the
    JSON somewhere that survives.
    """
    response.headers["Cache-Control"] = "no-store"
    records = store.export(kind)
    return {
        "count": len(records),
        "records": records,
        "note": (
            "Filed under the day each record describes. Export before a redeploy "
            "on a host with an ephemeral filesystem."
        ),
    }
