"""Weather Intelligence — the first agent backed by real observations.

It answers "is it safe to go out?" from live wave and wind forecasts rather
than a rule of thumb, and returns the numbers it judged on so the verdict can
be checked rather than trusted.

Two windows are always evaluated: the next twelve hours, and tomorrow morning.
Which one matters depends on the question, and deciding that from keywords
breaks across six languages — so both are reported and the orchestrator's
synthesis step uses whichever the user actually asked about.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from ..tools.marine import (
    MarineDataError,
    WindowSummary,
    fetch_marine_conditions,
    summarise_window,
)
from .base import Agent, AgentResult, Evidence, QueryContext

# Digha harbour, used when the caller sends no position.
_DEFAULT_LAT = 21.6272
_DEFAULT_LON = 87.5079

SOURCE = "Open-Meteo Marine + Forecast API"

# Thresholds for the small mechanised and traditional craft this is built for,
# in metres and km/h. These are working heuristics, not an official advisory —
# they are deliberately conservative and should be tuned against INCOIS ocean
# state forecasts and IMD small-craft warnings before anyone relies on them.
WAVE_CAUTION_M = 1.5
WAVE_DANGER_M = 2.5
WIND_CAUTION_KMH = 25.0
WIND_DANGER_KMH = 40.0
GUST_DANGER_KMH = 50.0


@dataclass
class Verdict:
    level: str  # "safe" | "caution" | "unsafe" | "unknown"
    reasons: list[str]


def assess(window: WindowSummary) -> Verdict:
    """Turn numbers into a verdict, keeping the reason for each escalation.

    Missing data yields "unknown", never "safe". Silence from a forecast service
    is not a calm sea, and for a tool people use to decide whether to put out
    from shore, reporting an absence of data as an absence of danger is the one
    failure that could get somebody killed.
    """
    reasons: list[str] = []
    level = "safe"

    def escalate(to: str, why: str) -> None:
        nonlocal level
        reasons.append(why)
        if to == "unsafe" or level == "unsafe":
            level = "unsafe"
        elif to == "caution" and level == "safe":
            level = "caution"

    wave = window.max_wave_height_m
    if wave is not None:
        if wave >= WAVE_DANGER_M:
            escalate("unsafe", f"waves reach {wave} m")
        elif wave >= WAVE_CAUTION_M:
            escalate("caution", f"waves build to {wave} m")

    wind = window.max_wind_speed_kmh
    if wind is not None:
        if wind >= WIND_DANGER_KMH:
            escalate("unsafe", f"wind reaches {wind} km/h")
        elif wind >= WIND_CAUTION_KMH:
            escalate("caution", f"wind rises to {wind} km/h")

    gusts = window.max_wind_gusts_kmh
    if gusts is not None and gusts >= GUST_DANGER_KMH:
        escalate("unsafe", f"gusts reach {gusts} km/h")

    if window.max_wave_height_m is None and window.max_wind_speed_kmh is None:
        return Verdict(
            level="unknown",
            reasons=["no wave or wind data was available for this time and place"],
        )

    if not reasons:
        reasons.append("waves and wind stay within safe limits")

    return Verdict(level=level, reasons=reasons)


def _evidence_for(window: WindowSummary) -> list[Evidence]:
    observed = f"{window.start:%Y-%m-%d %H:%M} to {window.end:%H:%M}"
    items: list[Evidence] = []

    def add(label: str, value: float | None, unit: str) -> None:
        if value is not None:
            items.append(
                Evidence(
                    source=SOURCE,
                    label=f"{label} ({window.label})",
                    value=str(value),
                    unit=unit,
                    observed_at=observed,
                )
            )

    add("Maximum wave height", window.max_wave_height_m, "m")
    add("Maximum swell height", window.max_swell_height_m, "m")
    add("Maximum wind speed", window.max_wind_speed_kmh, "km/h")
    add("Maximum wind gusts", window.max_wind_gusts_kmh, "km/h")
    add("Total rainfall", window.total_precipitation_mm, "mm")
    add("Sea surface temperature", window.avg_sea_temperature_c, "degC")
    return items


class WeatherIntelligenceAgent(Agent):
    name = "weather_intelligence"
    description = "Wind, waves and weather; judges whether it is safe to go out."
    handles = ("safety", "weather", "wind", "wave", "storm", "rain", "go out", "venture")
    is_stub = False

    async def run(self, context: QueryContext) -> AgentResult:
        latitude = context.latitude if context.latitude is not None else _DEFAULT_LAT
        longitude = context.longitude if context.longitude is not None else _DEFAULT_LON

        try:
            conditions = await fetch_marine_conditions(latitude, longitude)
        except MarineDataError as exc:
            # A failed fetch is reported, never papered over with a guess — a
            # made-up "looks fine" is the one answer that could get someone hurt.
            return AgentResult(
                agent=self.name,
                summary="",
                confidence=0.0,
                error=str(exc),
            )

        now = conditions.hourly[0].time if conditions.hourly else datetime.now()

        next_12h = summarise_window(conditions, now, now + timedelta(hours=12), "next 12 hours")
        tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        tomorrow_morning = summarise_window(
            conditions,
            tomorrow + timedelta(hours=5),
            tomorrow + timedelta(hours=11),
            "tomorrow morning",
        )

        now_verdict = assess(next_12h)
        morning_verdict = assess(tomorrow_morning)

        summary = (
            f"Next 12 hours: {now_verdict.level} — {', '.join(now_verdict.reasons)}. "
            f"Tomorrow morning: {morning_verdict.level} — {', '.join(morning_verdict.reasons)}."
        )

        evidence = _evidence_for(next_12h) + _evidence_for(tomorrow_morning)
        evidence.append(
            Evidence(
                source=SOURCE,
                label="Forecast location",
                value=f"{conditions.latitude:.3f}, {conditions.longitude:.3f}",
                note=f"timezone {conditions.timezone}",
            )
        )

        # Confidence reflects how much of the window actually came back, not how
        # strongly the model feels about it.
        covered = min(next_12h.hours, 12) / 12 if next_12h.hours else 0
        confidence = round(0.55 + 0.4 * covered, 2)
        if now_verdict.level == "unknown" or morning_verdict.level == "unknown":
            confidence = min(confidence, 0.3)

        return AgentResult(
            agent=self.name,
            summary=summary,
            evidence=evidence,
            confidence=confidence,
            is_stub=False,
        )
