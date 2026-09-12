"""Do the forecasts agree, and does it matter?

ORCA shows one number. Behind that number are several forecast models that do
not say the same thing, and the difference between them is not small: measured
at Digha over 1,104 hours against ERA5 reanalysis, ECMWF ran 1.5 km/h under,
GFS 3.5 km/h over, and the four models spanned roughly 5 km/h in the mean. A
single figure presented without that spread is more confident than the evidence
behind it.

This module asks two questions of the same coordinate seen by several models.

**How far apart are they?** — the plain spread, which is what HackHeritage's
``sourceComparison.ts`` computed, and the shape of that function is kept here.

**Does the disagreement change the answer?** — which that function did not ask,
and which is the only version of the question a fisherman has any use for.

Two corrections to the original, both learned by looking at what its rule does
to real numbers:

*A flat percentage is the wrong test.* It flagged disagreement above 25%
relative spread, for every variable, at every magnitude. Twenty-five percent of
a 0.4 m sea is 0.1 m, which is noise. Twenty-five percent of a 2.0 m sea is
0.5 m, which straddles the INCOIS High Wave Alert line. The same percentage is
meaningless at one end of the range and decisive at the other, so each variable
here carries an absolute floor beneath which a percentage is not reported at
all.

*Crossing a threshold is the finding.* When one model says 1.8 m and another
says 2.2 m, the useful statement is not "they differ by 22%" — it is that one
source would let you go and the other would not. The thresholds used are the
ones ORCA already quotes to the user, from IMD and INCOIS, not invented here.

Nothing in this module decides anything. It reports, so the screen can say the
sources disagree rather than silently picking one and sounding certain.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

import httpx

from ..config import get_settings
from .ml_calibration import CalibratedForecast, calibrate_ensemble

# The models to ask. Each is a genuinely separate forecast system run by a
# different agency, which is what makes the comparison meaningful — four
# re-readings of one model would agree by construction and prove nothing.
#
# "best_match" is deliberately excluded. Open-Meteo resolves it to
# reanalysis-backed data for past dates, so comparing it against ERA5 returns a
# spread of exactly zero: a perfect agreement that reflects the two series
# being the same series. Anything reading like flawless agreement here should
# be suspected of measuring itself.
MODELS: dict[str, str] = {
    "ecmwf_ifs025": "ECMWF IFS (0.25°)",
    "gfs_seamless": "NOAA GFS",
    "icon_seamless": "DWD ICON",
    "gem_seamless": "ECCC GEM",
}

# Below these, a difference is instrument noise dressed as a finding.
NOISE_FLOOR: dict[str, float] = {
    "wind_speed_10m": 3.0,      # km/h
    "wind_gusts_10m": 5.0,      # km/h
}

# The published lines the disagreement is tested against. These are the same
# figures the weather agent applies and cites, so a "sources straddle the
# limit" warning here and a "do not venture" verdict there cannot drift apart.
THRESHOLDS: dict[str, list[tuple[float, str, str]]] = {
    "wind_speed_10m": [
        (35.0, "IMD 'do not venture' floor", "IMD Wind Warning for Fishermen"),
    ],
    "wind_gusts_10m": [
        (55.0, "gust figure paired with IMD's lowest warning tier", "IMD Wind Warning for Fishermen"),
    ],
}

# Above this, the models are far enough apart to say so even when no published
# line falls between them.
RELATIVE_SPREAD_LIMIT = 0.25

# ...but only once the numbers are large enough for the difference to reach a
# decision. Measured at Digha, four models gave 0.7, 1.3, 4.1 and 5.9 km/h — a
# 173% relative spread across a flat calm, which the percentage rule alone
# reports as strong disagreement. It is not a disagreement: every model says the
# same thing about the only question being asked, which is whether it is safe to
# go out. Percentage-based disagreement is therefore withheld until at least one
# model reaches halfway to the lowest published limit for that variable, so the
# test is anchored to the advice rather than to arithmetic.
MATERIALITY_FRACTION = 0.5


def _materiality_floor(variable: str) -> float | None:
    """Half the lowest published limit for this variable, or None if it has no limit."""
    limits = [limit for limit, _, _ in THRESHOLDS.get(variable, [])]
    return min(limits) * MATERIALITY_FRACTION if limits else None


@dataclass
class Comparison:
    """One variable, as several models saw it."""

    variable: str
    unit: str
    values: dict[str, float] = field(default_factory=dict)
    calibration: CalibratedForecast | None = None

    @property
    def spread(self) -> float | None:
        if len(self.values) < 2:
            return None
        return max(self.values.values()) - min(self.values.values())

    @property
    def mean(self) -> float | None:
        if not self.values:
            return None
        return sum(self.values.values()) / len(self.values)

    @property
    def relative_spread(self) -> float | None:
        """Spread against the mean, suppressed where the spread is noise.

        Returning ``None`` rather than a large number near zero is the point:
        a mean of 0.1 km/h and a spread of 0.2 makes a 200% disagreement out of
        two models that both say there is no wind.
        """
        spread, mean = self.spread, self.mean
        if spread is None or mean in (None, 0):
            return None
        if spread < NOISE_FLOOR.get(self.variable, 0.0):
            return None
        return abs(spread / mean)

    @property
    def straddles(self) -> list[dict[str, str | float]]:
        """Published limits that fall between the lowest and highest model.

        This is the finding worth surfacing: not that the models differ, but
        that they differ across a line where the advice changes.
        """
        if len(self.values) < 2:
            return []
        low, high = min(self.values.values()), max(self.values.values())
        crossed = []
        for limit, label, source in THRESHOLDS.get(self.variable, []):
            if low < limit <= high:
                below = sorted(k for k, v in self.values.items() if v < limit)
                above = sorted(k for k, v in self.values.items() if v >= limit)
                crossed.append(
                    {
                        "limit": limit,
                        "label": label,
                        "source": source,
                        "below": ", ".join(MODELS.get(m, m) for m in below),
                        "atOrAbove": ", ".join(MODELS.get(m, m) for m in above),
                    }
                )
        return crossed

    @property
    def is_material(self) -> bool:
        """Are the numbers big enough for a difference between them to matter?

        A variable with no published limit has no anchor, so materiality cannot
        be judged and the percentage rule stands on its own.
        """
        floor = _materiality_floor(self.variable)
        if floor is None or not self.values:
            return True
        return max(self.values.values()) >= floor

    @property
    def disagrees(self) -> bool:
        # Straddling a published line is a disagreement at any magnitude,
        # because that is exactly where the advice changes.
        if self.straddles:
            return True
        if not self.is_material:
            return False
        relative = self.relative_spread
        return relative is not None and relative > RELATIVE_SPREAD_LIMIT

    def to_dict(self) -> dict:
        relative = self.relative_spread
        d = {
            "variable": self.variable,
            "unit": self.unit,
            "values": {MODELS.get(k, k): round(v, 2) for k, v in self.values.items()},
            "spread": None if self.spread is None else round(self.spread, 2),
            "mean": None if self.mean is None else round(self.mean, 2),
            "relativeSpread": None if relative is None else round(relative, 3),
            "material": self.is_material,
            "disagrees": self.disagrees,
            "straddles": self.straddles,
        }
        if self.calibration:
            d["calibration"] = self.calibration.to_dict()
        return d


@dataclass
class AgreementReport:
    latitude: float
    longitude: float
    hours_ahead: int
    comparisons: list[Comparison]
    unavailable: list[str] = field(default_factory=list)

    @property
    def decision_changing(self) -> list[Comparison]:
        """Only the disagreements that cross a published line."""
        return [c for c in self.comparisons if c.straddles]

    @property
    def headline(self) -> str:
        crossing = self.decision_changing
        if crossing:
            first = crossing[0].straddles[0]
            return (
                f"The forecasts disagree across the {first['label']}: "
                f"{first['below']} sits below it, {first['atOrAbove']} at or above."
            )
        if any(c.disagrees for c in self.comparisons):
            return "The forecasts differ, but not across any warning level."
        if any(c.spread and not c.is_material for c in self.comparisons):
            return "The forecasts agree that conditions are well inside safe limits."
        if sum(len(c.values) for c in self.comparisons) == 0:
            return "No model returned a comparable figure."
        return "The forecasts agree."

    def to_dict(self) -> dict:
        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "hoursAhead": self.hours_ahead,
            "modelsAsked": list(MODELS.values()),
            "modelsUnavailable": self.unavailable,
            "headline": self.headline,
            "decisionChanging": bool(self.decision_changing),
            "thresholdBreachRisk": any(c.calibration and c.calibration.threshold_breach_risk for c in self.comparisons),
            "comparisons": [c.to_dict() for c in self.comparisons],
            "note": (
                "Separate forecast systems run by different agencies. Where they "
                "straddle a published warning level, ORCA says so rather than "
                "choosing one and sounding certain."
            ),
        }


class AgreementError(RuntimeError):
    """Raised when no model could be reached at all."""


async def _one_model(
    client: httpx.AsyncClient,
    url: str,
    latitude: float,
    longitude: float,
    variables: list[str],
    hours_ahead: int,
    model: str,
) -> dict[str, float]:
    response = await client.get(
        url,
        params={
            "latitude": latitude,
            "longitude": longitude,
            "hourly": ",".join(variables),
            "models": model,
            "forecast_days": 2,
            "timezone": "auto",
        },
    )
    response.raise_for_status()
    hourly = (response.json() or {}).get("hourly") or {}
    times = hourly.get("time") or []
    if not times:
        return {}

    index = min(hours_ahead, len(times) - 1)
    out: dict[str, float] = {}
    for variable in variables:
        # A pinned model answers under its own suffixed key on some responses
        # and the bare name on others, so both are accepted rather than
        # assuming one and silently reading nothing.
        series = hourly.get(variable) or hourly.get(f"{variable}_{model}") or []
        if index < len(series) and isinstance(series[index], (int, float)):
            out[variable] = float(series[index])
    return out


async def compare_forecasts(
    latitude: float,
    longitude: float,
    hours_ahead: int = 0,
    variables: list[str] | None = None,
    timeout: float = 30.0,
) -> AgreementReport:
    """Ask several forecast models the same question and report the spread.

    A model that fails is recorded as unavailable rather than allowed to sink
    the comparison — three opinions are still worth having. Only when every
    model is unreachable does this raise, because a report claiming agreement
    among zero sources would be the worst possible output.
    """
    variables = variables or ["wind_speed_10m", "wind_gusts_10m"]
    settings = get_settings()

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        gathered = await asyncio.gather(
            *(
                _one_model(
                    client,
                    settings.open_meteo_forecast_url,
                    latitude,
                    longitude,
                    variables,
                    hours_ahead,
                    model,
                )
                for model in MODELS
            ),
            return_exceptions=True,
        )

    units = {"wind_speed_10m": "km/h", "wind_gusts_10m": "km/h"}
    comparisons = {v: Comparison(variable=v, unit=units.get(v, "")) for v in variables}
    unavailable: list[str] = []

    for model, result in zip(MODELS, gathered):
        if isinstance(result, BaseException) or not result:
            unavailable.append(MODELS[model])
            continue
        for variable, value in result.items():
            comparisons[variable].values[model] = value

    for comp in comparisons.values():
        comp.calibration = calibrate_ensemble(comp.variable, comp.values, latitude, longitude)

    if len(unavailable) == len(MODELS):
        raise AgreementError("No forecast model could be reached")

    return AgreementReport(
        latitude=latitude,
        longitude=longitude,
        hours_ahead=hours_ahead,
        comparisons=list(comparisons.values()),
        unavailable=unavailable,
    )
