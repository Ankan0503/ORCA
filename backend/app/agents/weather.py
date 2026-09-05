"""Weather Intelligence — the first agent backed by real observations.

It answers "is it safe to go out?" from live wave, wind and tide forecasts and
returns the numbers it judged on, so the verdict can be checked rather than
trusted.

Three things a fisherman needs that a maximum alone cannot give:

- Direction. Offshore wind pushing a boat out to sea is a different risk from
  the same speed blowing onshore, and it decides which way work is possible.
- Timing. "Waves reach 2 m today" is not actionable; "safe until 14:00" is.
- Lightning. Thunderstorms are among the biggest killers of Indian fishermen,
  and no wave or wind figure captures that risk.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from ..tools.marine import (
    HourlyPoint,
    MarineDataError,
    WindowSummary,
    compass,
    fetch_marine_conditions,
    summarise_window,
)
from .base import Agent, AgentResult, Evidence, QueryContext

# Digha harbour, used when the caller sends no position.
_DEFAULT_LAT = 21.6272
_DEFAULT_LON = 87.5079

SOURCE = "Open-Meteo Marine + Forecast API"

# Thresholds for the small mechanised and traditional craft this is built for,
# in metres, km/h and metres of visibility. These are working heuristics, not an
# official advisory — deliberately conservative, and they want tuning against
# INCOIS ocean state forecasts and IMD small-craft warnings before anyone relies
# on them.
WAVE_CAUTION_M = 1.5
WAVE_DANGER_M = 2.5
WIND_CAUTION_KMH = 25.0
WIND_DANGER_KMH = 40.0
GUST_DANGER_KMH = 50.0
VISIBILITY_CAUTION_M = 2000.0
VISIBILITY_DANGER_M = 1000.0


@dataclass
class Verdict:
    level: str  # "safe" | "caution" | "unsafe" | "unknown"
    reasons: list[str]


def _rank(level: str) -> int:
    return {"safe": 0, "caution": 1, "unsafe": 2}.get(level, 0)


def assess_point(point: HourlyPoint) -> tuple[str, list[str]]:
    """Judge a single hour. Used both for windows and for finding when it turns."""
    level = "safe"
    reasons: list[str] = []

    def escalate(to: str, why: str) -> None:
        nonlocal level
        reasons.append(why)
        if _rank(to) > _rank(level):
            level = to

    # Lightning outranks everything: an open boat has nowhere to shelter.
    if point.is_thunderstorm:
        escalate("unsafe", "thunderstorms with lightning")

    if point.wave_height_m is not None:
        if point.wave_height_m >= WAVE_DANGER_M:
            escalate("unsafe", f"waves {point.wave_height_m} m")
        elif point.wave_height_m >= WAVE_CAUTION_M:
            escalate("caution", f"waves {point.wave_height_m} m")

    if point.wind_speed_kmh is not None:
        if point.wind_speed_kmh >= WIND_DANGER_KMH:
            escalate("unsafe", f"wind {point.wind_speed_kmh} km/h")
        elif point.wind_speed_kmh >= WIND_CAUTION_KMH:
            escalate("caution", f"wind {point.wind_speed_kmh} km/h")

    if point.wind_gusts_kmh is not None and point.wind_gusts_kmh >= GUST_DANGER_KMH:
        escalate("unsafe", f"gusts {point.wind_gusts_kmh} km/h")

    if point.visibility_m is not None:
        if point.visibility_m <= VISIBILITY_DANGER_M:
            escalate("unsafe", f"visibility {int(point.visibility_m)} m")
        elif point.visibility_m <= VISIBILITY_CAUTION_M:
            escalate("caution", f"visibility {int(point.visibility_m)} m")

    return level, reasons


def assess(window: WindowSummary) -> Verdict:
    """Turn a window's worst case into a verdict.

    Missing data yields "unknown", never "safe". Silence from a forecast service
    is not a calm sea, and for a tool people use to decide whether to put out
    from shore, reporting an absence of data as an absence of danger is the one
    failure that could get somebody killed.
    """
    if window.max_wave_height_m is None and window.max_wind_speed_kmh is None:
        return Verdict(
            level="unknown",
            reasons=["no wave or wind data was available for this time and place"],
        )

    level = "safe"
    reasons: list[str] = []

    def escalate(to: str, why: str) -> None:
        nonlocal level
        reasons.append(why)
        if _rank(to) > _rank(level):
            level = to

    if window.has_thunderstorm:
        when = f" from {window.thunderstorm_at:%H:%M}" if window.thunderstorm_at else ""
        escalate("unsafe", f"thunderstorms with lightning{when}")

    wave = window.max_wave_height_m
    if wave is not None:
        if wave >= WAVE_DANGER_M:
            escalate("unsafe", f"waves reach {wave} m")
        elif wave >= WAVE_CAUTION_M:
            escalate("caution", f"waves build to {wave} m")

    wind = window.max_wind_speed_kmh
    if wind is not None:
        direction = f" from the {window.wind_from}" if window.wind_from else ""
        if wind >= WIND_DANGER_KMH:
            escalate("unsafe", f"wind reaches {wind} km/h{direction}")
        elif wind >= WIND_CAUTION_KMH:
            escalate("caution", f"wind rises to {wind} km/h{direction}")

    if window.max_wind_gusts_kmh is not None and window.max_wind_gusts_kmh >= GUST_DANGER_KMH:
        escalate("unsafe", f"gusts reach {window.max_wind_gusts_kmh} km/h")

    if window.min_visibility_m is not None:
        if window.min_visibility_m <= VISIBILITY_DANGER_M:
            escalate("unsafe", f"visibility drops to {int(window.min_visibility_m)} m")
        elif window.min_visibility_m <= VISIBILITY_CAUTION_M:
            escalate("caution", f"visibility drops to {int(window.min_visibility_m)} m")

    if not reasons:
        reasons.append("waves, wind and visibility stay within safe limits")

    return Verdict(level=level, reasons=reasons)


def safe_until(points: list[HourlyPoint], start: datetime) -> tuple[datetime, list[str]] | None:
    """Find when conditions first stop being safe.

    This is the difference between a forecast and advice. A fisherman does not
    need to know the day's worst wave — he needs to know how long he has.
    """
    for point in points:
        if point.time < start:
            continue
        level, reasons = assess_point(point)
        if level != "safe":
            return point.time, reasons
    return None


def _evidence_for(window: WindowSummary) -> list[Evidence]:
    observed = f"{window.start:%Y-%m-%d %H:%M} to {window.end:%H:%M}"
    items: list[Evidence] = []

    def add(label: str, value: object | None, unit: str | None = None, note: str | None = None):
        if value is not None:
            items.append(
                Evidence(
                    source=SOURCE,
                    label=f"{label} ({window.label})",
                    value=str(value),
                    unit=unit,
                    observed_at=observed,
                    note=note,
                )
            )

    add("Maximum wave height", window.max_wave_height_m, "m",
        note=f"from the {window.wave_from}" if window.wave_from else None)
    add("Wave period", window.wave_period_s, "s")
    add("Maximum swell height", window.max_swell_height_m, "m")
    add("Maximum wind speed", window.max_wind_speed_kmh, "km/h",
        note=f"from the {window.wind_from}" if window.wind_from else None)
    add("Maximum wind gusts", window.max_wind_gusts_kmh, "km/h")
    add("Lowest visibility", window.min_visibility_m, "m")
    add("Total rainfall", window.total_precipitation_mm, "mm")
    add("Sea surface temperature", window.avg_sea_temperature_c, "degC")
    add("Air temperature", window.avg_air_temperature_c, "degC")
    add("Maximum current speed", window.max_current_speed_ms, "m/s")

    if window.has_thunderstorm:
        add("Thunderstorm expected", "yes",
            note=f"from {window.thunderstorm_at:%H:%M}" if window.thunderstorm_at else None)

    for tide in window.tides:
        items.append(
            Evidence(
                source=SOURCE,
                label=f"{tide.kind.capitalize()} tide ({window.label})",
                value=str(tide.height_m),
                unit="m above mean sea level",
                observed_at=f"{tide.time:%Y-%m-%d %H:%M}",
            )
        )

    return items


class WeatherIntelligenceAgent(Agent):
    name = "weather_intelligence"
    description = (
        "Wind, waves, tides, visibility and storms; judges whether it is safe to go out "
        "and until when."
    )
    handles = (
        "safety", "weather", "wind", "wave", "storm", "rain", "go out", "venture",
        "tide", "lightning", "thunder", "visibility", "fog",
    )
    is_stub = False

    async def run(self, context: QueryContext) -> AgentResult:
        latitude = context.latitude if context.latitude is not None else _DEFAULT_LAT
        longitude = context.longitude if context.longitude is not None else _DEFAULT_LON

        try:
            conditions = await fetch_marine_conditions(latitude, longitude)
        except MarineDataError as exc:
            # A failed fetch is reported, never papered over with a guess — a
            # made-up "looks fine" is the one answer that could get someone hurt.
            return AgentResult(agent=self.name, summary="", confidence=0.0, error=str(exc))

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

        parts = [
            f"Next 12 hours: {now_verdict.level} — {', '.join(now_verdict.reasons)}.",
            f"Tomorrow morning: {morning_verdict.level} — {', '.join(morning_verdict.reasons)}.",
        ]

        # The actionable bit: how long the good conditions last.
        turning = safe_until(conditions.hourly, now)
        evidence = _evidence_for(next_12h) + _evidence_for(tomorrow_morning)

        if now_verdict.level == "safe" and turning is not None:
            turns_at, why = turning
            parts.insert(1, f"Conditions hold until {turns_at:%H:%M}, then {', '.join(why)}.")
            evidence.append(
                Evidence(
                    source=SOURCE,
                    label="Safe until",
                    value=f"{turns_at:%H:%M}",
                    note=f"then {', '.join(why)}",
                    observed_at=f"{turns_at:%Y-%m-%d}",
                )
            )
        elif now_verdict.level == "safe":
            parts.insert(1, "Conditions stay within safe limits for the whole forecast period.")

        if conditions.sunrise and conditions.sunset:
            evidence.append(
                Evidence(
                    source=SOURCE,
                    label="Daylight today",
                    value=f"{conditions.sunrise[0]:%H:%M} to {conditions.sunset[0]:%H:%M}",
                    note="sunrise to sunset",
                )
            )

        evidence.append(
            Evidence(
                source=SOURCE,
                label="Forecast location",
                value=f"{conditions.latitude:.3f}, {conditions.longitude:.3f}",
                note=f"timezone {conditions.timezone}",
            )
        )

        covered = min(next_12h.hours, 12) / 12 if next_12h.hours else 0
        confidence = round(0.55 + 0.4 * covered, 2)
        if now_verdict.level == "unknown" or morning_verdict.level == "unknown":
            confidence = min(confidence, 0.3)

        return AgentResult(
            agent=self.name,
            summary=" ".join(parts),
            evidence=evidence,
            confidence=confidence,
            is_stub=False,
        )
