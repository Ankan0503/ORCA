"""The passage: how to actually get to the fishing ground.

Combines four things ORCA already knows and one it did not: where the advised
grounds are (INCOIS), where the weather is (the sea grid), which way the water
is setting (the same grid), whether the position is legal (the geofence) — and
now the route between them, with the heading to steer on each leg.

The origin question is answered here rather than assumed. A boat cannot put to
sea from a city street, so a position that is not at sea is snapped to the
nearest landing centre and the response says so plainly, instead of drawing a
sea route out of somebody's living room.
"""

from fastapi import APIRouter, HTTPException, Query, Response

from ..tools import geofence, pfz, routing
from ..tools.ocean import distance_km

router = APIRouter(prefix="/route", tags=["route"])


async def _resolve_origin(lat: float, lon: float, lang: str) -> dict:
    """Where the passage really starts, and whether that is where the user is.

    If the position is at sea or on the coast, it is used as-is. If it is
    inland, the nearest INCOIS landing centre is used instead and flagged, so
    the map never implies a boat can sail from an inland town.
    """
    try:
        fence = geofence.locate(lat, lon)
        at_sea = fence.inside_eez or fence.level == "not_at_sea"
    except geofence.GeofenceDataError:
        fence = None
        at_sea = True

    # "not_at_sea" covers both a harbour and somewhere well inland, so the
    # distinction is made on how far the nearest landing centre actually is.
    sector = pfz.sector_for_location(lat, lon)
    try:
        advisory = await pfz.get_sector_advisory(sector.secid, lang)
    except pfz.PfzDataError:
        advisory = None

    if advisory and advisory.points:
        nearest = min(
            advisory.points,
            key=lambda p: distance_km(lat, lon, p.latitude, p.longitude),
        )
        # The advisory rows are given "from the coast of <landing centre>", so
        # the row's own start point is the harbour this boat would leave from.
        harbour_km = distance_km(lat, lon, nearest.latitude, nearest.longitude)
    else:
        nearest = None
        harbour_km = None

    inside = fence.inside_eez if fence else True
    return {
        "requested": {"latitude": lat, "longitude": lon},
        "insideEez": inside,
        "atSea": at_sea and inside,
        "sector": sector.name,
        "nearestLandingCentre": nearest.landing_centre if nearest else None,
        "distanceToGroundKm": round(harbour_km, 1) if harbour_km is not None else None,
    }


@router.get("")
async def plan(
    response: Response,
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    dest_lat: float | None = Query(None, ge=-90, le=90),
    dest_lon: float | None = Query(None, ge=-180, le=180),
    speed: float = Query(routing.DEFAULT_BOAT_SPEED_KMH, gt=1, le=60),
    lang: str = Query("en"),
) -> dict:
    """Plan a passage to a fishing ground, around the weather and with the current.

    With no destination given, the nearest INCOIS-advised ground is used — the
    trip a fisherman is actually most likely to make.
    """
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"

    origin_info = await _resolve_origin(lat, lon, lang)
    destination_note = None

    if dest_lat is None or dest_lon is None:
        sector = pfz.sector_for_location(lat, lon)
        try:
            advisory = await pfz.get_sector_advisory(sector.secid, lang)
        except pfz.PfzDataError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        if not advisory.points:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"INCOIS issued no fishing zones for {advisory.sector_name} today, "
                    "so there is nowhere to plan a route to."
                ),
            )
        target = min(
            advisory.points,
            key=lambda p: distance_km(lat, lon, p.latitude, p.longitude),
        )
        dest_lat, dest_lon = target.latitude, target.longitude
        destination_note = {
            "landingCentre": target.landing_centre,
            "forecastDate": advisory.forecast_date,
            "validUpto": advisory.valid_upto,
            "sector": advisory.sector_name,
            "depthFromM": target.depth_m_from,
            "depthToM": target.depth_m_to,
            "source": "INCOIS Potential Fishing Zone Advisory",
        }

    try:
        plan_result = await routing.plan_route(
            (lat, lon), (dest_lat, dest_lon), boat_speed_kmh=speed
        )
    except routing.RoutingError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return {
        "origin": origin_info,
        "destination": {
            "latitude": dest_lat,
            "longitude": dest_lon,
            **(destination_note or {}),
        },
        "route": plan_result.to_dict(),
    }
