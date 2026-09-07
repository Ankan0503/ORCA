"""Live sea conditions for the Safety, Sea Today and Alerts screens.

Those three screens were the last places in ORCA showing invented numbers, while
the Weather Intelligence agent was already fetching real wave, wind, tide,
visibility and storm data for the same coordinate. This endpoint closes that gap:
one call returns everything the three screens need, already reduced to the shape
they render.

Nothing here is generated or padded. Every figure comes from the Open-Meteo
marine and forecast APIs via :mod:`app.tools.marine`, and every verdict comes
from the same thresholds the agent uses (:mod:`app.agents.weather`), so the
safety banner, the spoken answer and the map can never disagree with each other.

Alerts are *derived from the forecast*, not authored: a thunderstorm alert exists
only if the forecast actually contains a thunderstorm code, and it names the hour
it starts. When the sea is calm there are simply no alerts, which is the honest
answer rather than a reassuring fake one.
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Query, Response

from ..agents.weather import (
    GUST_DANGER_KMH,
    VISIBILITY_CAUTION_M,
    VISIBILITY_DANGER_M,
    WAVE_CAUTION_M,
    WAVE_DANGER_M,
    WIND_CAUTION_KMH,
    WIND_DANGER_KMH,
    assess,
    assess_point,
    safe_until,
)
from ..tools import cyclone as cyclone_tool
from ..tools.marine import (
    HourlyPoint,
    MarineConditions,
    MarineDataError,
    compass,
    fetch_marine_conditions,
    summarise_window,
)

router = APIRouter(prefix="/conditions", tags=["conditions"])

SOURCE = "Open-Meteo Marine + Forecast API"

# How the four headline conditions are graded. Kept beside the agent's
# thresholds so a "caution" on the Safety screen means exactly what a "caution"
# means in a spoken answer.
_STATUS_GOOD = "good"
_STATUS_CAUTION = "caution"
_STATUS_ALERT = "alert"


def _grade(value: float | None, caution: float, danger: float, higher_is_worse: bool = True) -> str:
    """Grade one measurement against the agent's caution/danger thresholds."""
    if value is None:
        return _STATUS_GOOD
    if higher_is_worse:
        if value >= danger:
            return _STATUS_ALERT
        if value >= caution:
            return _STATUS_CAUTION
    else:
        if value <= danger:
            return _STATUS_ALERT
        if value <= caution:
            return _STATUS_CAUTION
    return _STATUS_GOOD


def _describe_sky(point: HourlyPoint) -> str:
    """A plain-language sky description from the WMO weather code."""
    code = point.weather_code
    if code is None:
        return "Unknown"
    if code in (95, 96, 99):
        return "Thunderstorm"
    if code in (45, 48):
        return "Fog"
    if code >= 80:
        return "Heavy showers"
    if code >= 60:
        return "Rain"
    if code >= 51:
        return "Drizzle"
    if code >= 3:
        return "Cloudy"
    if code >= 1:
        return "Partly cloudy"
    return "Clear"


def _conditions_block(current: HourlyPoint, window) -> list[dict]:
    """The four headline readings both Safety and Sea Today show."""
    wind = current.wind_speed_kmh
    wave = current.wave_height_m
    rain = window.total_precipitation_mm
    visibility = current.visibility_m

    return [
        {
            "id": "wind",
            "name": "Wind",
            "value": None if wind is None else round(wind),
            "unit": "km/h",
            "statusType": _grade(wind, WIND_CAUTION_KMH, WIND_DANGER_KMH),
            "icon": "wind",
            "note": f"from the {compass(current.wind_direction_deg)}"
            if current.wind_direction_deg is not None
            else None,
        },
        {
            "id": "waves",
            "name": "Waves",
            "value": None if wave is None else round(wave, 1),
            "unit": "m",
            "statusType": _grade(wave, WAVE_CAUTION_M, WAVE_DANGER_M),
            "icon": "waves",
            "note": f"{round(current.wave_period_s)} s period"
            if current.wave_period_s is not None
            else None,
        },
        {
            "id": "rain",
            "name": "Rain",
            "value": None if rain is None else round(rain, 1),
            "unit": "mm",
            # Rain alone rarely decides a trip; it is graded gently on purpose.
            "statusType": _grade(rain, 5.0, 20.0),
            "icon": "rain",
            "note": "next 12 hours",
        },
        {
            "id": "visibility",
            "name": "Visibility",
            "value": None if visibility is None else round(visibility / 1000, 1),
            "unit": "km",
            "statusType": _grade(
                visibility, VISIBILITY_CAUTION_M, VISIBILITY_DANGER_M, higher_is_worse=False
            ),
            "icon": "visibility",
            "note": None,
        },
    ]


def _sea_status(window) -> tuple[str, str]:
    """Reduce the sea state to calm / moderate / rough with a reason."""
    wave = window.max_wave_height_m
    wind = window.max_wind_speed_kmh

    if wave is None and wind is None:
        return "moderate", "No wave or wind data is available for this area right now."
    if (wave is not None and wave >= WAVE_DANGER_M) or (
        wind is not None and wind >= WIND_DANGER_KMH
    ):
        return "rough", "The sea is rough. Small boats should stay ashore."
    if (wave is not None and wave >= WAVE_CAUTION_M) or (
        wind is not None and wind >= WIND_CAUTION_KMH
    ):
        return "moderate", "The sea is choppy. Stay close to shore and watch the weather."
    return "calm", "The sea is calm and settled."


def _build_alerts(conditions: MarineConditions, now: datetime) -> list[dict]:
    """Derive alerts from what the forecast actually contains.

    An alert is only produced when a real threshold is crossed in a real
    forecast hour, and it names that hour. A calm forecast yields an empty list.
    """
    upcoming = [p for p in conditions.hourly if now <= p.time <= now + timedelta(hours=24)]
    alerts: list[dict] = []

    def first(predicate) -> HourlyPoint | None:
        return next((p for p in upcoming if predicate(p)), None)

    storm = first(lambda p: p.is_thunderstorm)
    if storm:
        alerts.append(
            {
                "id": "thunderstorm",
                "severity": "high",
                "badgeLabel": "Storm warning",
                "title": "Thunderstorms expected",
                "message": (
                    f"Lightning is forecast from {storm.time:%H:%M}. An open boat has no "
                    "shelter — do not go out, and return to shore if you are at sea."
                ),
                "startsAt": storm.time.isoformat(),
                "actionRequired": "Stay ashore until the storm passes.",
            }
        )

    gust = first(lambda p: p.wind_gusts_kmh is not None and p.wind_gusts_kmh >= GUST_DANGER_KMH)
    if gust:
        alerts.append(
            {
                "id": "gusts",
                "severity": "high",
                "badgeLabel": "Wind warning",
                "title": f"Gusts up to {round(gust.wind_gusts_kmh)} km/h",
                "message": (
                    f"Strong gusts are forecast from {gust.time:%H:%M}. Small craft can be "
                    "swamped or capsized in sudden gusts."
                ),
                "startsAt": gust.time.isoformat(),
                "actionRequired": "Postpone the trip or return early.",
            }
        )

    wave = first(lambda p: p.wave_height_m is not None and p.wave_height_m >= WAVE_DANGER_M)
    if wave:
        alerts.append(
            {
                "id": "waves",
                "severity": "high",
                "badgeLabel": "High waves",
                "title": f"Waves reaching {round(wave.wave_height_m, 1)} m",
                "message": f"Dangerous wave height is forecast from {wave.time:%H:%M}.",
                "startsAt": wave.time.isoformat(),
                "actionRequired": "Do not put out in a small boat.",
            }
        )
    elif (
        caution_wave := first(
            lambda p: p.wave_height_m is not None and p.wave_height_m >= WAVE_CAUTION_M
        )
    ) is not None:
        alerts.append(
            {
                "id": "waves-caution",
                "severity": "caution",
                "badgeLabel": "Choppy sea",
                "title": f"Waves building to {round(caution_wave.wave_height_m, 1)} m",
                "message": f"The sea gets choppy from {caution_wave.time:%H:%M}.",
                "startsAt": caution_wave.time.isoformat(),
                "actionRequired": "Stay close to shore.",
            }
        )

    fog = first(
        lambda p: p.is_fog
        or (p.visibility_m is not None and p.visibility_m <= VISIBILITY_DANGER_M)
    )
    if fog:
        alerts.append(
            {
                "id": "visibility",
                "severity": "caution",
                "badgeLabel": "Poor visibility",
                "title": "Fog and low visibility",
                "message": (
                    f"Visibility drops sharply from {fog.time:%H:%M}. It is easy to lose "
                    "your bearings and hard for other boats to see you."
                ),
                "startsAt": fog.time.isoformat(),
                "actionRequired": "Carry lights and a compass, or stay in.",
            }
        )

    return alerts


async def _alerts_with_cyclone(
    conditions: MarineConditions, now: datetime, longitude: float
) -> list[dict]:
    """Forecast-derived alerts, plus anything IMD says about cyclones.

    The cyclone entry comes first when present: it is the only warning here that
    can be days ahead of the weather, and it outranks a squall.

    A cyclone alert is raised only when IMD has actually said something — a
    declared system, or a non-nil chance of one forming. On a quiet day this
    adds nothing, which is the honest outcome. If the outlook cannot be reached
    the marine alerts are still returned rather than the whole screen failing,
    because an unreachable bulletin must not take out the lightning warning.
    """
    alerts = _build_alerts(conditions, now)

    try:
        outlook = await cyclone_tool.fetch_outlook()
    except cyclone_tool.CycloneDataError:
        return alerts

    entry = cyclone_alert(outlook, longitude, now)
    if entry is not None:
        alerts.insert(0, entry)
    return alerts


def cyclone_alert(outlook, longitude: float, now: datetime) -> dict | None:
    """The cyclone entry for the alert list, or None when IMD says nothing.

    Pure and separate from fetching so the decision can be tested without a live
    cyclone — one existed nowhere in the North Indian Ocean while this was
    written, and an untested warning path is not a warning path.

    Three outcomes: a declared storm is a warning, a non-nil chance of formation
    is a *watch* (said in those words, so the two are never confused), and a
    quiet outlook produces nothing at all.
    """
    active = outlook.active_cyclone
    if active is not None:
        return {
            "id": "cyclone",
            "severity": "high",
            "badgeLabel": "Cyclone warning",
            "title": f"IMD reports a {active.kind}",
            "message": f"{active.sentence} (IMD/RSMC outlook, {outlook.issued_text}).",
            "startsAt": now.isoformat(),
            "actionRequired": "Do not put out. Follow IMD and local authority instructions.",
        }

    basin = outlook.basin_for(longitude)
    if basin is not None and basin.peak_probability in ("LOW", "MODERATE", "HIGH"):
        return {
            "id": "cyclogenesis",
            "severity": "high" if basin.peak_probability == "HIGH" else "caution",
            "badgeLabel": "Cyclone watch",
            "title": f"{basin.peak_probability.capitalize()} chance of a system forming",
            "message": (
                f"IMD puts the chance of a new system forming over the {basin.basin} at "
                f"{basin.peak_probability.lower()}, first from {basin.first_risk_step}. "
                "No cyclone yet — this is a watch, not a warning."
            ),
            "startsAt": now.isoformat(),
            "actionRequired": "Plan shorter trips and check again before leaving.",
        }

    return None


@router.get("")
async def get_conditions(
    response: Response,
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
) -> dict:
    """Everything the Safety, Sea Today and Alerts screens display.

    Served from one forecast fetch so the three screens are always consistent
    with each other and with what the agent would say.
    """
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"

    try:
        conditions = await fetch_marine_conditions(lat, lon)
    except MarineDataError as exc:
        # A failed fetch is reported. It is never replaced with a cheerful
        # default, because "looks fine" is the one wrong answer that gets
        # somebody killed.
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if not conditions.hourly:
        raise HTTPException(status_code=502, detail="Forecast contained no hourly data")

    now = conditions.hourly[0].time
    current = conditions.hourly[0]

    next_12h = summarise_window(conditions, now, now + timedelta(hours=12), "next 12 hours")
    verdict = assess(next_12h)
    turning = safe_until(conditions.hourly, now)
    sea_status, sea_description = _sea_status(next_12h)

    # The next hours, for the forecast strip on Sea Today.
    forecast = [
        {
            "time": point.time.isoformat(),
            "temp": None if point.air_temperature_c is None else round(point.air_temperature_c),
            "waveHeight": None if point.wave_height_m is None else round(point.wave_height_m, 1),
            "windSpeed": None if point.wind_speed_kmh is None else round(point.wind_speed_kmh),
            "condition": _describe_sky(point),
            "status": assess_point(point)[0],
        }
        for point in conditions.hourly[:24]
    ]

    advice_steps: list[str] = []
    if verdict.level in ("unsafe", "unknown"):
        advice_steps = [
            "Do not put out to sea.",
            "Move boats and gear above the tide line.",
            "Wait for the next update before deciding.",
        ]
    elif verdict.level == "caution":
        advice_steps = [
            "Stay within sight of the shore.",
            "Carry a life jacket and a charged phone.",
            "Turn back as soon as conditions worsen.",
        ]
    else:
        advice_steps = [
            "Conditions are within safe limits for a day trip.",
            "Tell someone ashore when you expect to return.",
            "Check again before you leave.",
        ]

    return {
        "location": {
            "latitude": conditions.latitude,
            "longitude": conditions.longitude,
            "timezone": conditions.timezone,
        },
        "source": SOURCE,
        "observedAt": now.isoformat(),
        "fetchedAt": conditions.fetched_at.isoformat(),
        "safety": {
            "status": verdict.level,
            "reasons": verdict.reasons,
            "safeUntil": turning[0].isoformat() if turning else None,
            "safeUntilReasons": turning[1] if turning else [],
            "conditions": _conditions_block(current, next_12h),
            "adviceSteps": advice_steps,
            "maxWaveHeightM": next_12h.max_wave_height_m,
            "maxWindKmh": next_12h.max_wind_speed_kmh,
            "maxGustKmh": next_12h.max_wind_gusts_kmh,
        },
        "seaToday": {
            "seaStatus": sea_status,
            "description": sea_description,
            "conditions": _conditions_block(current, next_12h),
            "forecast": forecast,
            "seaTemperatureC": next_12h.avg_sea_temperature_c,
            "airTemperatureC": next_12h.avg_air_temperature_c,
        },
        "alerts": await _alerts_with_cyclone(conditions, now, lon),
        "tides": [
            {"time": t.time.isoformat(), "heightM": t.height_m, "kind": t.kind}
            for t in next_12h.tides
        ],
        "sun": {
            "sunrise": conditions.sunrise[0].isoformat() if conditions.sunrise else None,
            "sunset": conditions.sunset[0].isoformat() if conditions.sunset else None,
        },
    }
