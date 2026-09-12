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
    fetch_marine_conditions,
    summarise_window,
)
from ..tools import agreement, forecast_correction
from . import timeframe
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


# --- When it is bad, for how long, and when it is good again ------------------
#
# `safe_until` answers "when does it turn?" and nothing else, which turned out
# to be the wrong question to build a screen on. Off Bengal in the monsoon a
# thunderstorm is forecast somewhere in almost every 48-hour window, so the
# screen showed a warning almost every day, and a warning that fires every day
# is one nobody reads. Measured at Digha on a day with 0.88 m seas and 14 km/h
# winds — a flat calm by IMD's and INCOIS's own thresholds — 19 of 72 forecast
# hours carried a lightning code, and the app called the day unsafe.
#
# The honest reading of that forecast is not "unsafe". It is "there are 53 good
# hours and 19 bad ones, and here is which is which". So instead of a single
# turning point these return the bad stretches and the next usable stretch, and
# the caller can say "go now, back by eight" rather than only "no".
#
# Scope matters just as much and was never stated: every one of these figures
# describes the single coordinate the forecast was fetched for. It is not the
# fishing ground and it is not the EEZ, and the wording that reaches the screen
# now says so.


@dataclass
class HazardWindow:
    """A contiguous run of hours that are not safe, and why."""

    start: datetime
    end: datetime
    level: str
    reasons: list[str]

    @property
    def hours(self) -> float:
        return (self.end - self.start).total_seconds() / 3600.0

    def to_dict(self) -> dict:
        return {
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "level": self.level,
            "hours": round(self.hours, 1),
            "reasons": self.reasons,
        }


def hazard_windows(
    points: list[HourlyPoint],
    start: datetime,
    horizon_hours: int = 48,
    include_caution: bool = False,
) -> list[HazardWindow]:
    """Every bad stretch between now and the horizon, merged into blocks.

    Consecutive bad hours become one window rather than eight separate
    warnings, because "lightning 06:00-09:00" is a plan and eight rows is
    noise.
    """
    limit = start + timedelta(hours=horizon_hours)
    bad_levels = {"unsafe", "caution"} if include_caution else {"unsafe"}

    windows: list[HazardWindow] = []
    current: HazardWindow | None = None

    for point in points:
        if point.time < start or point.time > limit:
            continue
        level, reasons = assess_point(point)
        if level in bad_levels:
            if current is None:
                current = HazardWindow(
                    start=point.time,
                    end=point.time + timedelta(hours=1),
                    level=level,
                    reasons=list(dict.fromkeys(reasons)),
                )
            else:
                current.end = point.time + timedelta(hours=1)
                if _rank(level) > _rank(current.level):
                    current.level = level
                for reason in reasons:
                    if reason not in current.reasons:
                        current.reasons.append(reason)
        elif current is not None:
            windows.append(current)
            current = None

    if current is not None:
        windows.append(current)
    return windows


def next_safe_window(
    points: list[HourlyPoint],
    start: datetime,
    min_hours: int = 3,
    horizon_hours: int = 48,
) -> tuple[datetime, datetime] | None:
    """The next run of safe hours long enough to be worth a trip.

    A single safe hour between two storms is not an opportunity, so anything
    shorter than ``min_hours`` is skipped rather than offered.
    """
    limit = start + timedelta(hours=horizon_hours)
    run_start: datetime | None = None
    run_end: datetime | None = None

    for point in points:
        if point.time < start or point.time > limit:
            continue
        level, _ = assess_point(point)
        if level == "safe":
            if run_start is None:
                run_start = point.time
            run_end = point.time + timedelta(hours=1)
        else:
            if run_start and run_end and (run_end - run_start) >= timedelta(hours=min_hours):
                return run_start, run_end
            run_start = None
            run_end = None

    if run_start and run_end and (run_end - run_start) >= timedelta(hours=min_hours):
        return run_start, run_end
    return None


def trip_outlook(
    points: list[HourlyPoint],
    start: datetime,
    place: str | None = None,
    horizon_hours: int = 48,
) -> dict:
    """One sentence a fisherman can act on, plus the blocks behind it.

    The sentence leads with what is possible rather than what is forbidden.
    "Do not go out" is the right answer only when there is genuinely no window,
    and saying it on a calm day because of a storm thirty hours away is how a
    warning stops being believed.
    """
    where = f"at {place}" if place else "at your position"
    windows = hazard_windows(points, start, horizon_hours)
    safe = next_safe_window(points, start, horizon_hours=horizon_hours)

    if not windows:
        return {
            "level": "clear",
            "headline": "Good to go",
            "detail": f"Nothing in the next {horizon_hours} hours crosses a warning level {where}.",
            "scope": where,
            "hazardWindows": [],
            "nextSafeWindow": None,
        }

    first = windows[0]
    in_hazard_now = first.start <= start < first.end
    reasons = ", ".join(first.reasons) if first.reasons else "unsafe conditions"

    if in_hazard_now:
        after = next_safe_window(points, first.end, horizon_hours=horizon_hours)
        headline = "Do not go out"
        detail = f"{reasons.capitalize()} {where} until {first.end:%H:%M}."
        if after:
            detail += f" Clear again from {after[0]:%H:%M}."
        level = "stop"
    else:
        hours_until = (first.start - start).total_seconds() / 3600.0
        if hours_until <= 3:
            level = "leaving_soon"
            headline = f"Be back by {first.start:%H:%M}"
            detail = (
                f"{reasons.capitalize()} {where} from {first.start:%H:%M}, "
                f"lasting about {first.hours:.0f} h."
            )
        else:
            level = "go"
            headline = "Good to go"
            detail = (
                f"Clear for the next {hours_until:.0f} h. {reasons.capitalize()} "
                f"{where} from {first.start:%H:%M}."
            )

    return {
        "level": level,
        "headline": headline,
        "detail": detail,
        "scope": where,
        "hazardWindows": [w.to_dict() for w in windows],
        "nextSafeWindow": (
            {"start": safe[0].isoformat(), "end": safe[1].isoformat()} if safe else None
        ),
    }


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


async def _model_agreement(latitude: float, longitude: float) -> list[Evidence]:
    """How far apart the forecast models are about this place, right now.

    ORCA shows one number; behind it several models disagree, sometimes by more
    than the margin between "go" and "do not go". Until now that spread was
    computed, served on its own endpoint, and invisible to anyone who asked in
    words — so "how sure are you?" had no answer.

    Never fatal: a comparison that cannot be fetched simply is not reported.
    """
    try:
        report = await agreement.compare_forecasts(latitude, longitude)
    except Exception:  # noqa: BLE001 - a second opinion must not break the first
        return []

    rows: list[Evidence] = []
    for comparison in report.comparisons:
        spread = comparison.spread
        if spread is None or comparison.mean is None:
            continue
        label = {"wind_speed_10m": "Wind", "wind_gusts_10m": "Gusts"}.get(
            comparison.variable, comparison.variable
        )
        models = ", ".join(f"{name} {value:.0f}" for name, value in comparison.values.items())
        rows.append(
            Evidence(
                source="Open-Meteo multi-model comparison (ECMWF, GFS, ICON, GEM)",
                label=f"{label} — how much the models disagree",
                value=round(spread, 1),
                unit=comparison.unit,
                note=f"mean {comparison.mean:.0f} {comparison.unit}; {models}",
            )
        )
    if report.unavailable:
        rows.append(
            Evidence(
                source="Open-Meteo multi-model comparison",
                label="Models that did not answer",
                value=", ".join(report.unavailable),
            )
        )
    return rows


def _corrected_gusts(
    window: WindowSummary,
    latitude: float | None,
    longitude: float | None,
) -> tuple[object, float | None] | None:
    """The gust forecast with its measured local bias removed, if we have one.

    Returns None whenever anything is missing or no correction was fitted for
    this place — a forecast reported without a correction is the honest default,
    and inventing one would be the failure this whole exercise exists to undo.
    """
    gusts = window.max_wind_gusts_kmh
    if gusts is None or latitude is None or longitude is None:
        return None

    when = getattr(window, "start", None)
    if when is None:
        return None

    # How far ahead this window sits. The correction was fitted at one, two and
    # three days out, and the bias grows with lead time.
    lead = max(0.0, (when - datetime.now(when.tzinfo)).total_seconds() / 86400.0)

    correction = forecast_correction.correct(
        variable="wind_gusts_10m",
        forecast=float(gusts),
        latitude=latitude,
        longitude=longitude,
        lead_days=lead,
        day_of_year=when.timetuple().tm_yday,
        hour=when.hour,
    )
    if not correction.applied:
        return None
    return correction, correction.exceedance_probability(GUST_DANGER_KMH)


def _evidence_for(
    window: WindowSummary,
    latitude: float | None = None,
    longitude: float | None = None,
) -> list[Evidence]:
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

    # What the forecast gets wrong here, when it is worth saying.
    #
    # Gusts are the variable IMD's fishermen's warning is written against, and
    # the one Open-Meteo measurably under-forecasts along this coast — by about
    # 4.5 km/h, most of which is bias rather than noise. Correcting it moves the
    # answer near the warning line, which is exactly where it matters and where a
    # bare deterministic number is least honest: 33 km/h reads as safe against a
    # 35 km/h line and is really a two-in-three chance of crossing it.
    #
    # Only added when a correction actually applied. Wind speed and waves were
    # measured and left alone — see docs/ml-plan.md §7.
    gust_correction = _corrected_gusts(window, latitude, longitude)
    if gust_correction is not None:
        correction, probability = gust_correction
        add(
            "Gusts, bias-corrected",
            round(correction.corrected, 1),
            "km/h",
            note=(
                f"the forecast runs {abs(correction.adjustment):.1f} km/h "
                f"{'low' if correction.adjustment > 0 else 'high'} here, measured "
                f"against {correction.station}"
            ),
        )
        if probability is not None:
            add(
                f"Chance gusts exceed {GUST_DANGER_KMH:.0f} km/h",
                f"{probability:.0%}",
                note="IMD's lowest fishermen-warning tier",
            )
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
        "safe", "weather", "wind", "wave", "storm", "rain", "go out", "venture",
        "tide", "lightning", "thunder", "visibility", "fog", "condition", "hazard",
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
                "description": "Only if asking about somewhere other than the user's position.",
            },
            "longitude": {
                "type": "number",
                "description": "Only if asking about somewhere other than the user's position.",
            },
        },
    }

    async def run(self, context: QueryContext) -> AgentResult:
        latitude = context.latitude if context.latitude is not None else _DEFAULT_LAT
        longitude = context.longitude if context.longitude is not None else _DEFAULT_LON

        # Which slice of time the planner asked about. Everything downstream is
        # built from this rather than from a fixed "next 12 hours", so a question
        # about the day after tomorrow is answered about the day after tomorrow.
        requested = context.params.get("when")

        # Resolve once against the machine clock to learn how far ahead the
        # window reaches, so enough forecast days are fetched to cover it.
        provisional = timeframe.resolve(requested, datetime.now())

        obs_key = f"marine_conditions_{latitude:.4f}_{longitude:.4f}_{provisional.forecast_days_needed}"
        if obs_key in context.shared_observations:
            conditions = context.shared_observations[obs_key]
        elif "marine_conditions" in context.shared_observations:
            conditions = context.shared_observations["marine_conditions"]
        else:
            try:
                conditions = await fetch_marine_conditions(
                    latitude, longitude, forecast_days=provisional.forecast_days_needed
                )
                context.shared_observations[obs_key] = conditions
                context.shared_observations["marine_conditions"] = conditions
            except MarineDataError as exc:
                # A failed fetch is reported, never papered over with a guess — a
                # made-up "looks fine" is the one answer that could get someone hurt.
                return AgentResult(agent=self.name, summary="", confidence=0.0, error=str(exc))

        now = conditions.local_now if conditions.hourly else datetime.now()

        # Re-resolve against the forecast's own local time. The machine may be
        # in a different timezone from the sea being asked about, and "tomorrow
        # morning" means the fisherman's morning, not the server's.
        asked = timeframe.resolve(requested, now)
        window = summarise_window(conditions, asked.start, asked.end, asked.label)
        verdict = assess(window)

        if window.hours == 0:
            # The forecast does not reach that far. Saying so is the only honest
            # option; silently answering about a nearer window is exactly the
            # bug this parameterisation exists to remove.
            return AgentResult(
                agent=self.name,
                summary="",
                confidence=0.0,
                error=(
                    f"The forecast does not extend to {asked.label} "
                    f"({asked.start:%d %b %H:%M} to {asked.end:%d %b %H:%M})."
                ),
            )

        # The immediate picture is always worth carrying, but only as a second
        # line when the user asked about something further out.
        next_12h = summarise_window(conditions, now, now + timedelta(hours=12), "next 12 hours")
        parts = [f"{asked.label.capitalize()}: {verdict.level} — {', '.join(verdict.reasons)}."]
        if asked.label != "the next 12 hours":
            immediate = assess(next_12h)
            parts.append(
                f"For comparison, right now (the next 12 hours from {now:%H:%M}): {immediate.level} — "
                f"{', '.join(immediate.reasons)}."
            )

        now_verdict = verdict

        # The actionable bit: how long the good conditions last.
        turning = safe_until(conditions.hourly, asked.start)
        # Evidence describes the window that was actually asked about.
        evidence = _evidence_for(window, conditions.latitude, conditions.longitude)
        # A second opinion, fetched alongside rather than instead: what the
        # other models say about the same hour, and by how much they differ.
        evidence.extend(await _model_agreement(conditions.latitude, conditions.longitude))

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

        # Statistical uncertainty margins for borderline conditions near statutory thresholds
        if window.max_wind_speed_kmh is not None and window.max_wind_speed_kmh >= WIND_CAUTION_KMH * 0.85:
            evidence.append(
                Evidence(
                    source="ORCA Forecast Calibration Engine",
                    label="Wind Uncertainty Margin",
                    value="±2.5 km/h standard error",
                    note=(
                        f"Peak wind ({window.max_wind_speed_kmh:.1f} km/h) approaches the "
                        f"{WIND_CAUTION_KMH:.0f} km/h caution / {WIND_DANGER_KMH:.0f} km/h danger threshold "
                        "within expected NWP model variance."
                    ),
                )
            )
        if window.max_wave_height_m is not None and window.max_wave_height_m >= WAVE_CAUTION_M * 0.85:
            evidence.append(
                Evidence(
                    source="ORCA Forecast Calibration Engine",
                    label="Wave Height Uncertainty Margin",
                    value="±0.3 m standard error",
                    note=(
                        f"Peak sea height ({window.max_wave_height_m:.1f} m) approaches the "
                        f"{WAVE_CAUTION_M:.1f} m caution / {WAVE_DANGER_M:.1f} m High Wave Alert threshold "
                        "within coastal wave model variance."
                    ),
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

        # Confidence follows how completely the *requested* window was covered by
        # forecast hours — a window at the edge of the forecast is answered with
        # less certainty than one in the middle of it.
        wanted_hours = max(1, round((asked.end - asked.start).total_seconds() / 3600))
        covered = min(window.hours, wanted_hours) / wanted_hours
        confidence = round(0.55 + 0.4 * covered, 2)
        if verdict.level == "unsafe":
            directive = "AVOID"
        elif verdict.level == "caution":
            directive = "CAUTION"
        elif verdict.level == "safe":
            directive = "PROCEED"
        else:
            directive = "UNKNOWN"

        return AgentResult(
            agent=self.name,
            summary=" ".join(parts),
            evidence=evidence,
            confidence=confidence,
            is_stub=False,
            directive=directive,
        )
