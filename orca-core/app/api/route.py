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

from datetime import timedelta

from fastapi import APIRouter, HTTPException, Query, Response

from ..agents.weather import safe_until
from ..tools import geofence, pfz, routing
from ..tools.marine import MarineDataError, fetch_marine_conditions
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


# --- Chaining grounds --------------------------------------------------------
#
# A real trip is rarely one hop. A boat works a ground, moves to a second and
# comes home, and the question that decides the day is not "can I reach ground
# B" but "can I reach ground B *and still get back* before the sea turns".
#
# Routing to a single destination could never answer that, because the return
# passage — usually the longest single leg — was never in the arithmetic.

#: Beyond this it stops being a day trip, and the forecast window it is checked
#: against stops being meaningful.
MAX_STOPS = 4


def _parse_stop(raw: str, index: int) -> tuple[float, float]:
    parts = raw.split(",")
    if len(parts) != 2:
        raise HTTPException(
            status_code=422,
            detail=f"Stop {index + 1} should be given as 'lat,lon' — got {raw!r}.",
        )
    try:
        lat, lon = float(parts[0]), float(parts[1])
    except ValueError:
        raise HTTPException(
            status_code=422, detail=f"Stop {index + 1} is not a pair of numbers: {raw!r}."
        ) from None
    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        raise HTTPException(status_code=422, detail=f"Stop {index + 1} is not on Earth: {raw!r}.")
    return lat, lon


@router.get("/chain")
async def plan_chain(
    response: Response,
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    stop: list[str] = Query(..., description="Each stop as 'lat,lon', in the order worked."),
    home: bool = Query(True, description="Include the passage back to where you started."),
    speed: float = Query(routing.DEFAULT_BOAT_SPEED_KMH, gt=1, le=60),
    lang: str = Query("en"),
) -> dict:
    """Plan a trip across several grounds and back, against the safe window.

    Every leg is routed the way a single passage is — around lightning, with the
    current — and the arrival times are then laid against the hour the weather
    turns. The useful answer is rarely yes or no but *how many of these grounds
    fit*, so that is what the verdict names.
    """
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"

    if len(stop) > MAX_STOPS:
        raise HTTPException(
            status_code=422,
            detail=(
                f"{len(stop)} stops is beyond a day's fishing. Plan at most {MAX_STOPS} — "
                "a forecast window does not stretch far enough to be worth checking against."
            ),
        )

    stops = [_parse_stop(raw, i) for i, raw in enumerate(stop)]
    origin_info = await _resolve_origin(lat, lon, lang)

    # The safe window, and the clock the whole trip is measured from. Taken at
    # the origin: it is where the boat is now, and the one position whose
    # forecast is certain to exist.
    try:
        conditions = await fetch_marine_conditions(lat, lon)
    except MarineDataError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if not conditions.hourly:
        raise HTTPException(status_code=502, detail="Forecast contained no hourly data")

    departure = conditions.local_now
    turning = safe_until(conditions.hourly, departure)
    turns_at, turn_reasons = turning if turning else (None, [])

    legs_out: list[dict] = []
    cumulative_hours = 0.0
    cumulative_km = 0.0
    position = (lat, lon)
    last_fitting: int | None = None

    async def run_leg(start, end, label, kind, index):
        nonlocal cumulative_hours, cumulative_km, last_fitting, position
        try:
            plan_result = await routing.plan_route(start, end, boat_speed_kmh=speed)
        except routing.RoutingError as exc:
            raise HTTPException(status_code=409, detail=f"{label}: {exc}") from exc

        cumulative_hours += plan_result.total_hours
        cumulative_km += plan_result.total_distance_km
        arrival = departure + timedelta(hours=cumulative_hours)
        fits = turns_at is None or arrival <= turns_at
        if fits and index is not None:
            last_fitting = index

        return {
            "kind": kind,
            "index": index,
            "label": label,
            "latitude": round(end[0], 4),
            "longitude": round(end[1], 4),
            "arrivalAt": arrival.isoformat(),
            "cumulativeHours": round(cumulative_hours, 2),
            "cumulativeDistanceKm": round(cumulative_km, 1),
            "withinSafeWindow": fits,
            "route": plan_result.to_dict(),
        }

    for index, target in enumerate(stops):
        legs_out.append(await run_leg(position, target, f"Ground {index + 1}", "ground", index))
        position = target

    if home:
        legs_out.append(await run_leg(position, (lat, lon), "Home", "home", None))

    home_arrival = legs_out[-1]["arrivalAt"][11:16] if legs_out else None
    whole_trip_fits = all(entry["withinSafeWindow"] for entry in legs_out)
    plural = "s" if len(stops) != 1 else ""
    because = f" — {', '.join(turn_reasons)}" if turn_reasons else ""

    if turns_at is None:
        verdict = "fits"
        message = (
            f"Nothing in the forecast turns against you, so all {len(stops)} "
            f"ground{plural} fit with time to spare."
        )
    elif whole_trip_fits:
        verdict = "fits"
        spare = (turns_at - (departure + timedelta(hours=cumulative_hours))).total_seconds() / 3600
        where = "lands you back home" if home else "reaches the last ground"
        message = (
            f"The whole trip {where} at {home_arrival}, {spare:.1f} h before the "
            f"sea turns at {turns_at:%H:%M}."
            + ("" if home else " The passage back is not counted — add it before you go.")
        )
    elif last_fitting is None:
        verdict = "does_not_fit"
        message = (
            f"Not even the first ground fits. The sea turns at {turns_at:%H:%M}{because}, "
            "and you would still be on your way out."
        )
    else:
        verdict = "partly_fits"
        message = (
            f"Ground {last_fitting + 1} fits; the rest does not. The sea turns at "
            f"{turns_at:%H:%M}{because}, and the full trip does not get you home until "
            f"{home_arrival}."
        )

    return {
        "origin": origin_info,
        "departureAt": departure.isoformat(),
        "boatSpeedKmh": speed,
        "stops": legs_out,
        "totals": {
            "distanceKm": round(cumulative_km, 1),
            "hours": round(cumulative_hours, 2),
            "arrivalHomeAt": legs_out[-1]["arrivalAt"] if home and legs_out else None,
            "includesReturn": home,
        },
        "safety": {
            "safeUntil": turns_at.isoformat() if turns_at else None,
            "reasons": turn_reasons,
            "verdict": verdict,
            "lastStopThatFits": last_fitting,
            "message": message,
            # Said out loud because it is the honest limit of this arithmetic: a
            # window measured at the harbour is not the window fifty kilometres
            # offshore.
            "basis": (
                "The safe window is read from the forecast at your starting position. "
                "Conditions further out can turn earlier."
            ),
        },
    }
