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

# --- Where these numbers come from -------------------------------------------
#
# These were previously invented. They are now taken from what India's own
# agencies actually tell fishermen, so a verdict here can be checked against a
# government bulletin instead of being taken on trust.
#
# WIND — India Meteorological Department "Wind Warning for Fishermen" bulletins
# (issued daily by each Cyclone Warning Centre; the ladder below was read
# directly off the legend of one such bulletin, IMD Meteorological Centre
# Thiruvananthapuram, valid 28-31 May 2026). IMD's colour-coded tiers are:
#
#   35-45 kmph gusting 55   <- lowest tier drawn on the map, and the bulletin
#                              says "fishermen are advised not to venture into
#                              the marked areas". This is IMD's operational
#                              floor for "do not go", not 40 or 50.
#   40-50 gusting 60 / 45-55 gusting 65 / 50-60 gusting 70 / 55-65 gusting 75
#   60-80 gusting 90 and above -> cyclonic storm categories.
#
# So DANGER is set at IMD's own floor of 35 km/h, and CAUTION a little below it
# to give warning before the government threshold is reached. The previous
# values (caution 25, danger 40) let a boat read "caution" in conditions where
# IMD had already said do not venture — they under-warned.
#
# WAVE — INCOIS issues a High Wave Alert around 1.9-2.2 m, so DANGER is set at
# 2.0 m rather than the 2.5 m guessed before. CAUTION stays at 1.5 m as an
# approach warning below the alert level.
#
# SWELL SURGE — a separate INCOIS product from the High Wave Alert, and a real
# hazard ORCA previously ignored entirely. It is triggered by *long period*
# swell rather than height: alerts in the bulletin above ran at 15-19 s period
# with heights as low as 0.8-1.0 m. Long-period swell surges over jetties and
# harbour mouths and capsizes boats that see nothing alarming in the wave
# height alone, which is exactly why height-only thresholds miss it.
#
# VISIBILITY has no equivalent published Indian small-craft figure, so those two
# remain ORCA's own and are labelled as such wherever they are surfaced.

WAVE_CAUTION_M = 1.5
WAVE_DANGER_M = 2.0  # INCOIS High Wave Alert level

WIND_CAUTION_KMH = 30.0
WIND_DANGER_KMH = 35.0  # IMD "do not venture" floor
GUST_CAUTION_KMH = 45.0
GUST_DANGER_KMH = 55.0  # gust figure paired with IMD's lowest warning tier

# Long-period swell, per INCOIS Swell Surge Alert practice.
SWELL_SURGE_PERIOD_S = 15.0
SWELL_SURGE_HEIGHT_M = 0.8

VISIBILITY_CAUTION_M = 2000.0
VISIBILITY_DANGER_M = 1000.0

# Cited in evidence so a fisherman (or a judge) can trace any verdict back to
# the document behind it.
WIND_SOURCE = "IMD Wind Warning for Fishermen (Cyclone Warning Centre bulletins)"
WAVE_SOURCE = "INCOIS High Wave Alert criteria"
SWELL_SOURCE = "INCOIS Swell Surge Alert criteria"
ORCA_SOURCE = "ORCA caution margin (no published Indian figure)"


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

    if point.wind_gusts_kmh is not None:
        if point.wind_gusts_kmh >= GUST_DANGER_KMH:
            escalate("unsafe", f"gusts {point.wind_gusts_kmh} km/h")
        elif point.wind_gusts_kmh >= GUST_CAUTION_KMH:
            escalate("caution", f"gusts {point.wind_gusts_kmh} km/h")

    # Long-period swell: dangerous at heights that look harmless on their own.
    if (
        point.swell_period_s is not None
        and point.swell_height_m is not None
        and point.swell_period_s >= SWELL_SURGE_PERIOD_S
        and point.swell_height_m >= SWELL_SURGE_HEIGHT_M
    ):
        escalate(
            "caution",
            f"long-period swell ({point.swell_period_s} s, {point.swell_height_m} m) "
            "can surge at the shore",
        )

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

    gusts = window.max_wind_gusts_kmh
    if gusts is not None:
        if gusts >= GUST_DANGER_KMH:
            escalate("unsafe", f"gusts reach {gusts} km/h")
        elif gusts >= GUST_CAUTION_KMH:
            escalate("caution", f"gusts reach {gusts} km/h")

    if (
        window.max_swell_period_s is not None
        and window.max_swell_height_m is not None
        and window.max_swell_period_s >= SWELL_SURGE_PERIOD_S
        and window.max_swell_height_m >= SWELL_SURGE_HEIGHT_M
    ):
        escalate(
            "caution",
            f"long-period swell ({window.max_swell_period_s} s, "
            f"{window.max_swell_height_m} m) may surge at the shore",
        )

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


def _sea_driver(window: WindowSummary) -> str | None:
    """Whether the sea is local wind chop or swell from distant weather.

    The distinction decides whether waiting helps. Wind waves ease within hours
    of the wind easing; swell arrives from a storm hundreds of miles away and
    keeps running through a flat calm, which is why a deceptively still morning
    can still be dangerous at a harbour mouth.
    """
    wind_wave = window.max_wind_wave_height_m
    swell = window.max_swell_height_m
    if wind_wave is None or swell is None:
        return None
    if swell > wind_wave * 1.3:
        return "mostly swell from distant weather — it will not ease with the wind"
    if wind_wave > swell * 1.3:
        return "mostly local wind chop — it eases when the wind does"
    return "a mix of local wind chop and distant swell"


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
    # Splitting the sea into local wind chop and distant swell tells a fisherman
    # *why* it is rough, and therefore whether waiting will help: wind waves
    # drop when the wind drops, swell keeps running in a flat calm.
    add("Wind-driven wave height", window.max_wind_wave_height_m, "m",
        note=_sea_driver(window))
    add("Swell period", window.max_swell_period_s, "s",
        note="long-period swell surges at the shore" if (
            window.max_swell_period_s is not None
            and window.max_swell_period_s >= SWELL_SURGE_PERIOD_S
        ) else None)
    add("Maximum wind speed", window.max_wind_speed_kmh, "km/h",
        note=f"from the {window.wind_from}" if window.wind_from else None)
    add("Maximum wind gusts", window.max_wind_gusts_kmh, "km/h")
    add("Lowest visibility", window.min_visibility_m, "m")
    add("Total rainfall", window.total_precipitation_mm, "mm")
    add("Sea surface temperature", window.avg_sea_temperature_c, "degC")
    add("Air temperature", window.avg_air_temperature_c, "degC")
    add("Maximum current speed", window.max_current_speed_ms, "m/s",
        note=f"setting towards the {window.current_towards}" if window.current_towards else None)

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

        # The numbers the verdict was judged against, and who published them —
        # so an answer can be traced to a government bulletin rather than trusted.
        evidence.extend(
            [
                Evidence(
                    source=WIND_SOURCE,
                    label="Wind thresholds applied",
                    value=f"{WIND_CAUTION_KMH:.0f} km/h caution, {WIND_DANGER_KMH:.0f} km/h do-not-venture",
                    note=(
                        "IMD's lowest fishermen-warning tier (35-45 km/h gusting 55) already "
                        "reads 'do not venture into the marked areas'"
                    ),
                ),
                Evidence(
                    source=WAVE_SOURCE,
                    label="Wave threshold applied",
                    value=f"{WAVE_DANGER_M:.1f}",
                    unit="m",
                    note="INCOIS issues a High Wave Alert around 1.9-2.2 m",
                ),
                Evidence(
                    source=SWELL_SOURCE,
                    label="Swell surge threshold applied",
                    value=f"{SWELL_SURGE_PERIOD_S:.0f} s period at {SWELL_SURGE_HEIGHT_M:.1f} m",
                    note="long-period swell is hazardous at heights that look harmless",
                ),
                Evidence(
                    source=ORCA_SOURCE,
                    label="Visibility thresholds applied",
                    value=f"{int(VISIBILITY_CAUTION_M)} m caution, {int(VISIBILITY_DANGER_M)} m unsafe",
                    note="ORCA's own margin — no published Indian small-craft figure found",
                ),
            ]
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
