"""Historical Trends — the only agent that reasons across years.

Every other specialist in ORCA answers about now, or about the next few days.
This one exists for the last question on the problem statement's own list of
things a user should be able to ask: *"Why has fish productivity declined in
this region?"*

**The honest shape of that answer.** ORCA has no catch records — no landings, no
CPUE series, no fisheries census. So this agent must never confirm that
productivity has declined, and never quantify it. What it can do is read the
observational record for the exact patch of sea being asked about, report what
the water has measurably done over the past decade, and explain the mechanisms
by which those specific changes are known to affect the base of the food chain.
Whether the catch has fallen is the fisherman's own observation; what ORCA adds
is whether the ocean around him has changed in ways that would explain it.

That distinction is the feature. An agent that answered "yes, productivity is
down 30%" would be inventing a number nobody measured, which is the failure mode
this codebase exists to avoid. Refusing to invent it, while still producing four
real decade-long records and the physics that link them, is a stronger answer
and a defensible one.
"""

from ..tools.history import (
    DEFAULT_YEARS,
    HistoryDataError,
    MetricTrend,
    fetch_season_history,
)
from .base import Agent, AgentResult, Evidence, QueryContext

# Digha, used when the caller sends no position.
_DEFAULT_LAT = 21.6272
_DEFAULT_LON = 87.5079

#: How large a per-decade change has to be before it is worth calling a trend
#: rather than noise. Set from what a decade of these records actually moves —
#: below these, a "trend" is one unusual year pulling the line.
_MATERIAL = {
    "sst": 0.15,   # °C per decade
    "wind": 1.0,   # km/h per decade
    "rain": 1.5,   # mm/day per decade
    "wave": 0.15,  # m per decade
}

#: Why each change matters, physically. Keyed by metric and direction.
_MECHANISM = {
    ("sst", "up"): (
        "warmer surface water floats more strongly on the cooler water beneath it, "
        "which slows the mixing that carries nutrients up to where plankton can use them"
    ),
    ("sst", "down"): (
        "cooler surface water mixes more readily with the layer below, which tends to "
        "bring more nutrients within reach of plankton"
    ),
    ("wind", "up"): (
        "stronger wind stirs the upper ocean harder, which usually means more nutrients "
        "reaching the sunlit layer — though it also means fewer days small boats can work"
    ),
    ("wind", "down"): (
        "weaker wind stirs the surface less, leaving it more stratified and more "
        "nutrient-starved"
    ),
    ("rain", "up"): (
        "heavier monsoon rain and river runoff cap the sea with a layer of fresh, light "
        "water that resists mixing — a Bay of Bengal effect that works independently of "
        "temperature"
    ),
    ("rain", "down"): (
        "less freshwater runoff leaves the surface layer saltier and easier to mix"
    ),
    ("wave", "up"): "a rougher sea over the season, and fewer workable days for a small boat",
    ("wave", "down"): "a calmer season overall, with more workable days",
}


def _direction(slope: float) -> str:
    return "up" if slope > 0 else "down"


def _describe(metric: MetricTrend) -> str | None:
    """One sentence about a metric, or None when it has not meaningfully moved."""
    slope = metric.slope_per_decade
    if slope is None or abs(slope) < _MATERIAL.get(metric.key, 0.0):
        return None
    direction = "risen" if slope > 0 else "fallen"
    return (
        f"{metric.label} has {direction} about {abs(slope):.2f} {metric.unit} per decade "
        f"({metric.first_year}–{metric.last_year})"
    )


class HistoricalTrendsAgent(Agent):
    name = "historical_trends"
    description = (
        "How the sea at a place has changed over the past decade — surface temperature, "
        "wind, rainfall and wave height for the same weeks of every year, from ERA5 and "
        "NOAA satellite records. Use for questions about decline, change over the years, "
        "'it was better before', why fishing is worse than it used to be, or any question "
        "comparing now against past seasons. Does NOT hold catch or landing data."
    )
    handles = (
        "decline", "declined", "decrease", "less fish", "fewer fish", "used to",
        "before", "earlier years", "past", "history", "historical", "trend",
        "changed", "changing", "climate", "warming", "over the years", "why",
        "worse", "compared to last year",
    )
    is_stub = False

    parameters = {
        "type": "object",
        "properties": {
            "latitude": {
                "type": "number",
                "description": "Only if asking about somewhere other than the user's position.",
            },
            "longitude": {
                "type": "number",
                "description": "Only if asking about somewhere other than the user's position.",
            },
            "years": {
                "type": "integer",
                "description": (
                    f"How many past years to compare against. Default {DEFAULT_YEARS}. "
                    "More years give a firmer trend but take longer to fetch."
                ),
                "minimum": 3,
                "maximum": 20,
            },
        },
    }

    async def run(self, context: QueryContext) -> AgentResult:
        latitude = context.latitude if context.latitude is not None else _DEFAULT_LAT
        longitude = context.longitude if context.longitude is not None else _DEFAULT_LON
        years = int(context.params.get("years") or DEFAULT_YEARS)
        years = max(3, min(20, years))

        try:
            history = await fetch_season_history(latitude, longitude, years=years)
        except HistoryDataError as exc:
            return AgentResult(
                agent=self.name,
                summary=(
                    "The historical record for this position could not be read, so no "
                    "comparison with past years is possible right now."
                ),
                error=str(exc),
                confidence=0.0,
            )

        evidence = [
            Evidence(
                source=metric.source,
                label=f"{metric.label}, {history.window_label}",
                value=(
                    f"{metric.latest:.2f} this year"
                    if metric.latest is not None
                    else "—"
                ),
                unit=metric.unit,
                observed_at=f"{metric.first_year}–{metric.last_year}",
                note=(
                    None
                    if metric.baseline is None
                    else (
                        f"{metric.anomaly:+.2f} {metric.unit} against the "
                        f"{metric.first_year}–{metric.last_year - 1} average of "
                        f"{metric.baseline:.2f}"
                    )
                ),
            )
            for metric in history.metrics
        ]

        moved = [m for m in history.metrics if _describe(m)]
        window = history.window_label

        if not moved:
            summary = (
                f"Over the past {years} years, the sea here in the {window} window has not "
                "changed in any direction large enough to call a trend: surface temperature, "
                "wind, rainfall and wave height are all within their normal year-to-year "
                "spread. ORCA holds no catch records, so it cannot say whether fishing has "
                "changed — only that the water has not, measurably."
            )
            confidence = 0.55
        else:
            changes = "; ".join(_describe(m) for m in moved)
            mechanisms = [
                _MECHANISM.get((m.key, _direction(m.slope_per_decade or 0.0)))
                for m in moved
                if m.key in ("sst", "wind", "rain")
            ]
            mechanisms = [m for m in mechanisms if m]
            because = (
                f" That matters because {mechanisms[0]}." if mechanisms else ""
            )
            summary = (
                f"Comparing the same weeks ({window}) in every year since "
                f"{min(m.first_year for m in history.metrics)}: {changes}.{because} "
                "ORCA has no catch or landing records, so it cannot confirm that fish "
                "productivity has fallen — what it can say is whether the water has changed "
                "in ways that would explain it."
            )
            confidence = 0.7 if len(moved) > 1 else 0.6

        return AgentResult(
            agent=self.name,
            summary=summary,
            evidence=evidence,
            confidence=confidence,
            data=history.to_dict(),
        )
