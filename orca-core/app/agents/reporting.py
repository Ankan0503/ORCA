"""Reporting — the brief, for the people ORCA has been ignoring.

The problem statement names five stakeholders: fishermen, researchers, coastal
authorities, disaster-management agencies and maritime operators. ORCA has been
built for the first of those and no other. Every screen answers one boat's
question, in one fisherman's language, about the next few hours.

A researcher or a district disaster officer needs a different artefact: one
document, for one place, at one stated time, carrying every finding with the
agency it came from, so it can be filed, forwarded, quoted in a decision, and
checked afterwards. That is what this agent composes.

It is deliberately not a summary of the chat. It re-reads the sources — the
forecast, the safe window, the legal position, INCOIS's advisory, the annual
ban, IMD's cyclone outlook — and lays them out in sections, each with its own
provenance and issue time. A brief whose numbers cannot be traced is worse than
no brief, because it launders an unsourced figure into something that looks
official.

The caveats travel with it rather than being left to the reader's memory, for
the same reason: a document outlives the conversation that produced it.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from ..tools import closures as closures_tool
from ..tools import cyclone as cyclone_tool
from ..tools import geofence as geofence_tool
from ..tools import pfz as pfz_tool
from ..tools.marine import MarineDataError, fetch_marine_conditions, summarise_window
from .base import Agent, AgentResult, Evidence, QueryContext
from .weather import assess, safe_until

_DEFAULT_LAT = 21.6272
_DEFAULT_LON = 87.5079

GEOFENCE_SOURCE = "Marine Regions EEZ v12"


def _section(title: str, source: str, lines: list[str], issued: str | None = None) -> dict:
    return {"title": title, "source": source, "issuedAt": issued, "lines": lines}


class ReportingAgent(Agent):
    name = "reporting"
    description = (
        "Compiles a dated marine situation brief for one position: conditions and the safe "
        "window, legal status against the EEZ and protected areas, the INCOIS fishing "
        "advisory, the annual ban, and IMD's cyclone outlook — each with its source and "
        "issue time. Use when the user asks for a report, a summary of everything, a brief, "
        "something to send or show someone, or an overall picture rather than one answer."
    )
    handles = (
        "report", "brief", "summary", "summarise", "summarize", "overall", "everything",
        "full picture", "document", "send", "share", "print", "official", "record",
        "situation",
    )
    is_stub = False

    parameters = {
        "type": "object",
        "properties": {
            "latitude": {"type": "number", "description": "Only if not the user's position."},
            "longitude": {"type": "number", "description": "Only if not the user's position."},
            "days": {
                "type": "integer",
                "description": (
                    "How many days to plan across, 1 to 7. Use this for 'plan my week', "
                    "'which days should I go', or any question spanning several days — "
                    "one call covers the span. Do NOT call this agent once per day."
                ),
            },
        },
    }

    #: The forecast thins out past this, and a plan built on it would be fiction.
    MAX_PLAN_DAYS = 7

    def _requested_days(self, context: QueryContext) -> int:
        days = (getattr(context, "params", None) or {}).get("days")
        try:
            return max(1, min(int(days), self.MAX_PLAN_DAYS))
        except (TypeError, ValueError):
            return 1

    async def _day_by_day(self, latitude: float, longitude: float, days: int) -> dict | None:
        """A verdict per day, so a week can be planned in one call.

        Without this the model has to call the weather agent once per day, and
        MAX_TOOL_ROUNDS stops it at four — so "plan my week" silently became
        "plan the next four days", with no indication the rest was missing.
        """
        try:
            conditions = await fetch_marine_conditions(latitude, longitude)
        except MarineDataError:
            return None

        start = conditions.local_now
        lines: list[str] = []
        good: list[str] = []
        for day in range(days):
            day_start = (start + timedelta(days=day)).replace(hour=5, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(hours=13)
            window = summarise_window(conditions, day_start, day_end, f"day {day + 1}")
            if window.hours == 0:
                lines.append(f"{day_start:%a %d %b}: beyond the forecast.")
                continue
            verdict = assess(window)
            detail = []
            if window.max_wave_height_m is not None:
                detail.append(f"waves {window.max_wave_height_m:.1f} m")
            if window.max_wind_gusts_kmh is not None:
                detail.append(f"gusts {window.max_wind_gusts_kmh:.0f} km/h")
            lines.append(
                f"{day_start:%a %d %b}: {verdict.level.upper()}"
                + (f" — {', '.join(detail)}" if detail else "")
                + (f"; {verdict.reasons[0]}" if verdict.reasons else "")
                + "."
            )
            if verdict.level == "safe":
                good.append(f"{day_start:%a}")

        if good:
            lines.append("Best days to go: " + ", ".join(good) + ".")
        else:
            lines.append("No day in this span is clear of a warning level.")
        return _section(
            f"Day by day — next {days} day(s)",
            "Open-Meteo Marine + Forecast API",
            lines,
            issued=start.isoformat(),
        )

    async def run(self, context: QueryContext) -> AgentResult:
        latitude = context.latitude if context.latitude is not None else _DEFAULT_LAT
        longitude = context.longitude if context.longitude is not None else _DEFAULT_LON

        days = self._requested_days(context)

        sections: list[dict[str, Any]] = []
        evidence: list[Evidence] = []
        caveats: list[str] = []
        headline = "Marine situation brief"
        compiled_at = datetime.now().isoformat(timespec="seconds")

        # --- Conditions and the safe window ---------------------------------
        try:
            conditions = await fetch_marine_conditions(latitude, longitude)
            now = conditions.local_now
            window = summarise_window(conditions, now, now + timedelta(hours=12), "next 12 hours")
            verdict = assess(window)
            turning = safe_until(conditions.hourly, now)

            lines = [f"Verdict for the next 12 hours: {verdict.level.upper()}."]
            if verdict.reasons:
                lines.append("Driven by: " + ", ".join(verdict.reasons) + ".")
            if window.max_wave_height_m is not None:
                lines.append(f"Peak wave height {window.max_wave_height_m:.1f} m.")
            if window.max_wind_speed_kmh is not None:
                lines.append(f"Peak wind {window.max_wind_speed_kmh:.0f} km/h.")
            if window.max_wind_gusts_kmh is not None:
                lines.append(f"Peak gusts {window.max_wind_gusts_kmh:.0f} km/h.")
            lines.append(
                f"Conditions stay within safe limits until {turning[0]:%H:%M}"
                + (f" — then {', '.join(turning[1])}." if turning[1] else ".")
                if turning
                else "Nothing in the next two days crosses a warning level."
            )
            if days > 1:
                # One call for the whole span. Asking the model to loop instead
                # runs it into MAX_TOOL_ROUNDS and silently truncates the week.
                spread = await self._day_by_day(latitude, longitude, days)
                if spread:
                    sections.append(spread)

            sections.append(
                _section(
                    "Sea conditions",
                    "Open-Meteo Marine + Forecast API",
                    lines,
                    issued=now.isoformat(),
                )
            )
            headline = f"Marine situation brief — {verdict.level.upper()}"
            evidence.append(
                Evidence(
                    source="Open-Meteo Marine + Forecast API",
                    label="12-hour verdict",
                    value=verdict.level,
                    observed_at=now.isoformat(),
                )
            )
        except MarineDataError as exc:
            sections.append(
                _section("Sea conditions", "Open-Meteo Marine + Forecast API",
                         [f"Unavailable: {exc}"])
            )
            caveats.append(
                "The forecast could not be read when this brief was compiled. Its absence "
                "is not an all-clear."
            )

        # --- Where this is, legally -----------------------------------------
        try:
            fence = geofence_tool.locate(latitude, longitude)
            lines = [fence.message]
            if fence.nearest_boundary:
                lines.append(
                    f"Nearest foreign boundary: {fence.nearest_boundary.line_name} at "
                    f"{fence.nearest_boundary.distance_km:.0f} km."
                )
            sections.append(
                _section("Position and maritime limits", GEOFENCE_SOURCE, lines)
            )
            evidence.append(
                Evidence(source=GEOFENCE_SOURCE, label="Zone", value=fence.zone or "—")
            )
        except geofence_tool.GeofenceDataError as exc:
            sections.append(
                _section("Position and maritime limits", "Marine Regions EEZ v12",
                         [f"Unavailable: {exc}"])
            )

        # --- Protected areas and the annual ban ------------------------------
        try:
            ban = closures_tool.ban_status(longitude)
            nearby = closures_tool.protected_areas_near(latitude, longitude)
            inside = [a for a in nearby if getattr(a, "inside", False)]
            lines = [ban.message]
            if inside:
                lines.append(
                    "Inside a protected area: "
                    + "; ".join(f"{a.name} ({a.designation})" for a in inside)
                    + "."
                )
            elif nearby:
                lines.append(f"{len(nearby)} protected area(s) within range of this position.")
            else:
                lines.append("No protected area near this position.")
            lines.append(
                f"The layer holds {closures_tool.protected_area_count()} polygons."
            )
            sections.append(_section("Closures and protected areas", closures_tool.MPA_SOURCE, lines))
        except Exception as exc:  # noqa: BLE001 — a brief must still be produced
            sections.append(
                _section("Closures and protected areas", closures_tool.MPA_SOURCE,
                         [f"Unavailable: {exc}"])
            )

        # --- INCOIS advisory --------------------------------------------------
        try:
            sector = pfz_tool.sector_for_location(latitude, longitude)
            advisory = await pfz_tool.get_sector_advisory(sector.secid, context.language)
            lines = [
                f"Sector: {advisory.sector_name}.",
                f"{len(advisory.points)} advised fishing zones issued.",
            ]
            if advisory.valid_upto:
                lines.append(f"Valid up to {advisory.valid_upto}.")
            sections.append(
                _section(
                    "INCOIS Potential Fishing Zone advisory",
                    "Indian National Centre for Ocean Information Services",
                    lines,
                    issued=advisory.forecast_date,
                )
            )
            evidence.append(
                Evidence(
                    source="INCOIS Potential Fishing Zone Advisory",
                    label="Advised zones in this sector",
                    value=str(len(advisory.points)),
                    observed_at=advisory.forecast_date,
                )
            )
        except pfz_tool.PfzDataError as exc:
            sections.append(
                _section("INCOIS Potential Fishing Zone advisory", "INCOIS",
                         [f"Unavailable: {exc}"])
            )

        # --- Cyclone outlook ---------------------------------------------------
        try:
            outlook = await cyclone_tool.fetch_outlook()
            active = outlook.active_cyclone
            basin = outlook.basin_for(longitude)
            if active is not None:
                lines = [f"{active.kind}: {active.sentence}"]
            elif basin is not None:
                lines = [
                    f"No system declared. Chance of one forming over the {basin.basin} in the "
                    f"next 7 days: {basin.peak_probability}."
                ]
            else:
                lines = ["No system declared for this basin."]
            sections.append(
                _section(
                    "Cyclone outlook",
                    "IMD / RSMC Tropical Cyclones, New Delhi",
                    lines,
                    issued=outlook.issued_text,
                )
            )
        except cyclone_tool.CycloneDataError as exc:
            sections.append(
                _section("Cyclone outlook", "IMD / RSMC Tropical Cyclones, New Delhi",
                         [f"Unavailable: {exc}"])
            )
            caveats.append(
                "The cyclone outlook could not be reached. An unread bulletin is not a "
                "quiet basin."
            )

        caveats.append(
            "ORCA is decision support, not a warning authority. Where this brief and an "
            "IMD, INCOIS or Coast Guard bulletin disagree, the government bulletin stands."
        )

        brief = {
            "title": headline,
            "compiledAt": compiled_at,
            "position": {"latitude": latitude, "longitude": longitude},
            "sections": sections,
            "caveats": caveats,
        }

        reached = sum(1 for s in sections if not any(l.startswith("Unavailable") for l in s["lines"]))
        return AgentResult(
            agent=self.name,
            summary=(
                f"Compiled a situation brief for {latitude:.3f}, {longitude:.3f} from "
                f"{reached} of {len(sections)} sources, each section carrying its own "
                "issue time and provenance."
            ),
            evidence=evidence,
            confidence=0.8 if reached == len(sections) else 0.55,
            data={"brief": brief},
        )
