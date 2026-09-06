"""Risk Assessment — the one answer that needs all the others.

The other three agents each know one thing well: the weather agent knows when
the sea turns, the ocean agent knows where the fish are, and the geospatial
agent knows where the border is. None of them can answer the question a
fisherman actually asks, which is *should I go, and can I get back?*

This agent combines them, and adds the piece that only exists in the
combination: **reachability**. INCOIS may advise a ground 60 km offshore while
the forecast says conditions hold for three more hours. At the speed of a small
mechanised boat that is a trip you cannot complete — and neither the fishing
advisory nor the forecast says so on its own.

Two rules govern how the pieces combine:

- The worst factor decides. Risk is not averaged, because a calm sea does not
  offset a thunderstorm, and good fishing does not offset a border 2 km away.
- Missing data never reads as safe. An absent forecast produces "unknown",
  never "low", for the same reason the weather agent refuses to.

Boat speed is an assumption, not a measurement, and is reported as one.
"""

from datetime import datetime, timedelta

from ..tools import geofence as geofence_tool
from ..tools.geofence import GeofenceDataError
from ..tools.marine import MarineDataError, fetch_marine_conditions, summarise_window
from ..tools.ocean import distance_km
from ..tools import pfz as pfz_tool
from .base import Agent, AgentResult, Evidence, QueryContext
from .weather import assess, safe_until

_DEFAULT_LAT = 21.6272
_DEFAULT_LON = 87.5079

# A typical small mechanised fishing boat makes about 8 knots. This is an
# assumption about the vessel, not an observation, and every figure derived from
# it is labelled accordingly. A faster or slower boat changes the arithmetic,
# which is why the assumed speed is reported alongside the conclusion.
BOAT_SPEED_KMH = 15.0

# Time ashore working the nets, added to the round trip when judging whether a
# ground is reachable inside the safe window.
FISHING_HOURS = 1.5

# Ordered worst-first; the highest one reached decides the overall verdict.
_LEVELS = ("low", "moderate", "high", "severe")


def _rank(level: str) -> int:
    return _LEVELS.index(level) if level in _LEVELS else 0


class RiskAssessmentAgent(Agent):
    name = "risk_assessment"
    description = (
        "Combines sea safety, fishing-zone distance and border proximity into one "
        "verdict on whether to go out, and whether the trip can be completed in time."
    )
    handles = (
        "risk", "danger", "hazard", "safe", "advice", "should i go", "trip",
        "return", "back", "overall", "decide",
    )
    is_stub = False

    async def run(self, context: QueryContext) -> AgentResult:
        latitude = context.latitude if context.latitude is not None else _DEFAULT_LAT
        longitude = context.longitude if context.longitude is not None else _DEFAULT_LON

        evidence: list[Evidence] = []
        factors: list[tuple[str, str]] = []  # (level, reason)

        # --- 1. Sea safety, and how long it holds -------------------------
        safe_hours: float | None = None
        weather_available = True
        try:
            conditions = await fetch_marine_conditions(latitude, longitude)
        except MarineDataError as exc:
            weather_available = False
            conditions = None
            factors.append(("high", f"sea conditions could not be checked ({exc})"))
            evidence.append(
                Evidence(
                    source="Open-Meteo Marine + Forecast API",
                    label="Sea conditions",
                    value="unavailable",
                    note="risk cannot be cleared without a forecast",
                )
            )

        if conditions and conditions.hourly:
            now = conditions.hourly[0].time
            window = summarise_window(
                conditions, now, now + timedelta(hours=12), "next 12 hours"
            )
            verdict = assess(window)

            level = {
                "safe": "low",
                "caution": "moderate",
                "unsafe": "severe",
                "unknown": "high",
            }.get(verdict.level, "high")
            factors.append((level, f"sea is {verdict.level}: {', '.join(verdict.reasons)}"))

            evidence.append(
                Evidence(
                    source="Open-Meteo Marine + Forecast API",
                    label="Sea safety verdict",
                    value=verdict.level,
                    note="; ".join(verdict.reasons),
                )
            )

            turning = safe_until(conditions.hourly, now)
            if turning is not None:
                safe_hours = max(0.0, (turning[0] - now).total_seconds() / 3600)
                evidence.append(
                    Evidence(
                        source="Open-Meteo Marine + Forecast API",
                        label="Safe window remaining",
                        value=f"{safe_hours:.1f}",
                        unit="hours",
                        note=f"until {turning[0]:%H:%M}, then {', '.join(turning[1])}",
                    )
                )
        elif weather_available:
            factors.append(("high", "the forecast returned no hourly data"))

        # --- 2. Border proximity ------------------------------------------
        try:
            fence = geofence_tool.locate(latitude, longitude)
            level = {
                "critical": "severe",
                "outside": "severe",
                "beyond_eez": "high",
                "warning": "high",
                "watch": "moderate",
                "clear": "low",
                "not_at_sea": "low",
            }.get(fence.level, "moderate")
            if level != "low":
                factors.append((level, fence.message))
            evidence.append(
                Evidence(
                    source=geofence_tool.SOURCE,
                    label="Maritime boundary status",
                    value=fence.level,
                    note=fence.message,
                )
            )
            if fence.nearest_boundary is not None:
                nb = fence.nearest_boundary
                evidence.append(
                    Evidence(
                        source=geofence_tool.SOURCE,
                        label=f"Nearest foreign boundary ({nb.neighbour})",
                        value=f"{nb.distance_km:.1f}",
                        unit="km",
                        note=f"to the {nb.bearing}",
                    )
                )
        except GeofenceDataError:
            # Boundary data missing is a gap in ORCA, not a hazard at sea; it is
            # reported rather than folded into the verdict as danger.
            evidence.append(
                Evidence(
                    source=geofence_tool.SOURCE,
                    label="Maritime boundary status",
                    value="unavailable",
                )
            )

        # --- 3. Reachability of the advised fishing ground ----------------
        reachable_note: str | None = None
        trip: dict = {}
        try:
            sector = pfz_tool.sector_for_location(latitude, longitude)
            advisory = await pfz_tool.get_sector_advisory(sector.secid, context.language)
            if advisory.points:
                nearest = min(
                    advisory.points,
                    key=lambda p: distance_km(latitude, longitude, p.latitude, p.longitude),
                )
                out_km = distance_km(latitude, longitude, nearest.latitude, nearest.longitude)
                round_trip_h = (2 * out_km) / BOAT_SPEED_KMH + FISHING_HOURS

                evidence.append(
                    Evidence(
                        source="INCOIS advisory + ORCA travel estimate",
                        label="Nearest advised fishing ground",
                        value=f"{out_km:.0f}",
                        unit="km",
                        note=(
                            f"off {nearest.landing_centre}; about {round_trip_h:.1f} h "
                            f"round trip at an assumed {BOAT_SPEED_KMH:.0f} km/h "
                            f"including {FISHING_HOURS:.1f} h fishing"
                        ),
                    )
                )

                trip = {
                    "distanceKm": round(out_km, 1),
                    "roundTripHours": round(round_trip_h, 1),
                    "landingCentre": nearest.landing_centre,
                    "assumedSpeedKmh": BOAT_SPEED_KMH,
                    "fishingHours": FISHING_HOURS,
                    "safeHours": None if safe_hours is None else round(safe_hours, 1),
                    "reachable": None if safe_hours is None else round_trip_h <= safe_hours,
                }
                if safe_hours is not None:
                    if round_trip_h > safe_hours:
                        factors.append(
                            (
                                "high",
                                f"the nearest advised ground is {out_km:.0f} km out — about "
                                f"{round_trip_h:.1f} h there and back, but conditions only "
                                f"hold for {safe_hours:.1f} h",
                            )
                        )
                        reachable_note = "not reachable and back before conditions turn"
                    else:
                        reachable_note = (
                            f"reachable and back with about "
                            f"{safe_hours - round_trip_h:.1f} h to spare"
                        )
                    evidence.append(
                        Evidence(
                            source="ORCA travel estimate",
                            label="Round trip against the safe window",
                            value=reachable_note,
                            note=(
                                "assumes a small mechanised boat; a slower vessel has "
                                "less margin"
                            ),
                        )
                    )
            else:
                # No advisory for this coast today is a real state, not a gap —
                # say so rather than leaving the trip section silently blank.
                evidence.append(
                    Evidence(
                        source="INCOIS Potential Fishing Zone Advisory",
                        label="Advised fishing ground",
                        value="none issued today",
                        note=f"no zones advised for the {advisory.sector_name} sector",
                    )
                )
        except pfz_tool.PfzDataError:
            evidence.append(
                Evidence(
                    source="INCOIS Potential Fishing Zone Advisory",
                    label="Advised fishing ground",
                    value="unavailable",
                )
            )

        # --- 4. Combine: the worst factor decides -------------------------
        overall = "low"
        for level, _reason in factors:
            if _rank(level) > _rank(overall):
                overall = level

        drivers = [reason for level, reason in factors if _rank(level) == _rank(overall)]
        if not drivers:
            drivers = ["no hazard was found in the sea state, boundary or trip distance"]

        headline = {
            "low": "Low risk",
            "moderate": "Moderate risk — go prepared",
            "high": "High risk — think twice",
            "severe": "Severe risk — do not go",
        }[overall]

        # Some drivers are whole sentences already (the boundary message is), so
        # trailing punctuation is stripped before they are joined.
        sentences = [d.strip().rstrip(".").strip() for d in drivers if d.strip()]
        summary = f"{headline}. " + ". ".join(s[0].upper() + s[1:] for s in sentences) + "."
        if reachable_note and overall != "severe":
            summary += f" The nearest advised ground is {reachable_note}."

        evidence.append(
            Evidence(
                source="ORCA risk model",
                label="How this was combined",
                value="worst factor decides",
                note=(
                    "sea safety, boundary proximity and trip reachability are not "
                    "averaged; missing data is never treated as safe"
                ),
            )
        )

        # Confidence tracks how much of the picture was actually available.
        confidence = 0.9 if weather_available else 0.45

        return AgentResult(
            agent=self.name,
            summary=summary,
            evidence=evidence,
            confidence=confidence,
            is_stub=False,
            data={
                "level": overall,
                "headline": headline,
                "drivers": sentences,
                "trip": trip,
                "safeHours": None if safe_hours is None else round(safe_hours, 1),
            },
        )
