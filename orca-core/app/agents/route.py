"""Route Planning — the safest passage to the nearest fishing ground, and when to be back."""

from datetime import datetime, timedelta

from ..tools import routing
from ..tools.marine import MarineDataError, fetch_marine_conditions
from . import timeframe
from .base import Agent, AgentResult, Evidence, QueryContext
from .ocean import OceanAnalyticsAgent
from .risk import FISHING_HOURS
from .weather import safe_until

_DEFAULT_LAT = 21.6272
_DEFAULT_LON = 87.5079
SOURCE = "ORCA routing over the Open-Meteo sea grid, kept inside Indian waters"


class RoutePlanningAgent(Agent):
    name = "route_planning"
    description = (
        "Plans the safest sea route from the user's position to the nearest fishing zone (or a "
        "chosen point): around thunderstorms and heavy rain, never across land or the maritime "
        "border, with the time to leave and the time to be back before the weather turns."
    )
    handles = (
        "route", "path", "way to", "road", "navigat", "direction", "how to reach", "how do i get",
        "passage", "reach the",
    )
    is_stub = False
    parameters = {
        "type": "object",
        "properties": {
            "when": {
                "type": "string",
                "enum": list(timeframe.WINDOW_KEYS),
                "description": timeframe.WINDOW_DESCRIPTION,
            },
            "latitude": {
                "type": "number",
                "description": "Only if starting somewhere other than the user's position.",
            },
            "longitude": {
                "type": "number",
                "description": "Only if starting somewhere other than the user's position.",
            },
            "destination_latitude": {
                "type": "number",
                "description": "Only if the user names a destination; otherwise the nearest fishing zone.",
            },
            "destination_longitude": {
                "type": "number",
                "description": "Only if the user names a destination; otherwise the nearest fishing zone.",
            },
        },
    }

    async def run(self, context: QueryContext) -> AgentResult:
        latitude = context.latitude if context.latitude is not None else _DEFAULT_LAT
        longitude = context.longitude if context.longitude is not None else _DEFAULT_LON
        params = context.params or {}

        destination, label, estimate = await self._destination(context, params)
        if destination is None:
            return AgentResult(agent=self.name, summary="", confidence=0.0, error=label)

        try:
            route = await routing.plan_route((latitude, longitude), destination)
        except routing.RoutingError as exc:
            return AgentResult(agent=self.name, summary="", confidence=0.0, error=str(exc))

        depart, turns_at, reasons = await self._window(latitude, longitude, params.get("when"))
        each_way = route.total_hours
        round_trip = 2 * each_way + FISHING_HOURS
        back_by = depart + timedelta(hours=round_trip) if depart else None

        sentences = [
            f"Safest route to the {label}: {route.total_distance_km:.0f} km, about {each_way:.1f} h "
            f"each way at {route.boat_speed_kmh:.0f} km/h"
            + (f", steering around {', '.join(route.avoided)}" if route.avoided else "")
            + "."
        ]
        fits: bool | None = None
        if depart is not None and back_by is not None:
            why = ", ".join(reasons)
            if turns_at is None:
                fits = True
                sentences.append(
                    f"Leave at {depart:%H:%M} and be back by {back_by:%H:%M} "
                    f"(including {FISHING_HOURS:.1f} h fishing); no worsening is forecast before then."
                )
            elif turns_at <= depart:
                fits = False
                sentences.append(
                    f"Do not set out: the sea is already unsafe at {depart:%H:%M} ({why}). "
                    "The route is shown for planning only."
                )
            elif turns_at >= back_by:
                fits = True
                sentences.append(
                    f"Leave at {depart:%H:%M} and be back by {back_by:%H:%M} (including "
                    f"{FISHING_HOURS:.1f} h fishing); the weather holds until {turns_at:%H:%M}."
                )
            else:
                fits = False
                turn_home = turns_at - timedelta(hours=each_way)
                sentences.append(
                    f"The weather turns at {turns_at:%H:%M} ({why}), before a full trip would be back "
                    f"({back_by:%H:%M}). "
                    + (
                        f"If you go at {depart:%H:%M}, turn for home by {turn_home:%H:%M}."
                        if turn_home > depart + timedelta(hours=each_way)
                        else "There is not enough time to reach the zone and return safely."
                    )
                )

        evidence = [
            Evidence(
                source=SOURCE,
                label="Route to fishing zone",
                value=f"{route.total_distance_km:.1f}",
                unit="km",
                note=f"{each_way:.1f} h each way; straight line {route.direct_km:.1f} km",
            ),
            Evidence(
                source=SOURCE,
                label="Destination",
                value=f"{destination[0]:.3f}, {destination[1]:.3f}",
                note=label,
            ),
        ]
        if depart is not None and back_by is not None:
            evidence.append(
                Evidence(
                    source=SOURCE,
                    label="Leave / back by",
                    value=f"{depart:%H:%M} / {back_by:%H:%M}",
                    note=f"round trip {round_trip:.1f} h including {FISHING_HOURS:.1f} h fishing",
                )
            )
        if turns_at is not None:
            evidence.append(
                Evidence(
                    source="Open-Meteo Marine + Forecast API",
                    label="Weather turns",
                    value=f"{turns_at:%H:%M}",
                    note=", ".join(reasons),
                )
            )

        return AgentResult(
            agent=self.name,
            summary=" ".join(sentences),
            evidence=evidence,
            confidence=0.6 if estimate else 0.8,
            is_stub=False,
            data={
                "route": route.to_dict(),
                "origin": {"latitude": latitude, "longitude": longitude},
                "destination": {"latitude": destination[0], "longitude": destination[1], "label": label},
                "departure": depart.isoformat() if depart else None,
                "backBy": back_by.isoformat() if back_by else None,
                "weatherTurnsAt": turns_at.isoformat() if turns_at else None,
                "weatherTurnReasons": reasons,
                "fitsSafeWindow": fits,
                "estimate": estimate,
            },
        )

    async def _destination(
        self, context: QueryContext, params: dict
    ) -> tuple[tuple[float, float] | None, str, bool]:
        """The chosen point, else the zone the ocean agent ranks first; with a label and estimate flag."""
        dest_lat, dest_lon = params.get("destination_latitude"), params.get("destination_longitude")
        if dest_lat is not None and dest_lon is not None:
            return (float(dest_lat), float(dest_lon)), "chosen point", False

        zones = await OceanAnalyticsAgent().run(context)
        found = (zones.data or {}).get("zones") or []
        if not found:
            return None, zones.error or "No fishing zone was found to plan a route to.", False
        top = found[0]
        return (top["latitude"], top["longitude"]), top["label"], bool(zones.data.get("estimate"))

    async def _window(
        self, latitude: float, longitude: float, requested: str | None
    ) -> tuple[datetime | None, datetime | None, list[str]]:
        """Departure time, when conditions first turn after it, and why."""
        provisional = timeframe.resolve(requested, datetime.now())
        try:
            conditions = await fetch_marine_conditions(
                latitude, longitude, forecast_days=provisional.forecast_days_needed
            )
        except MarineDataError:
            return None, None, []
        depart = timeframe.resolve(requested, conditions.local_now).start
        turning = safe_until(conditions.hourly, depart)
        return depart, (turning[0] if turning else None), (turning[1] if turning else [])
