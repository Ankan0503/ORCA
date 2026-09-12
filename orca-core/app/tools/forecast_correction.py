"""What the forecast gets wrong here, and how likely it is to matter.

A numerical weather model carries a bias that depends on where you are: at one
day out the wind-speed forecast runs 1.3 km/h high at Kochi and 2.8 km/h low at
Rameswaram. No rule expresses that, and it is the one thing here worth learning
from data — see ``docs/ml-plan.md`` for why the risk classifier that preceded it
was not.

Two things come out of this module:

* a **corrected** forecast, and
* the **probability the real value exceeds a threshold**, which is the part a
  deterministic forecast cannot answer. "Gusts 33 km/h" against a 35 km/h warning
  line reads as safe and is a coin toss; ``P(gusts > 35) = 0.41`` says so.

Only wind gusts are corrected. Wind speed and wave height were measured and left
alone because their corrections did not clear the floor that would change an
answer — ``docs/ml-plan.md`` §7 has the numbers. Asking for either returns the
forecast untouched, and says so, rather than quietly pretending to improve it.

Inference is a dot product and a linear interpolation, written in plain Python.
The coefficients were fitted offline, so nothing here needs numpy, scikit-learn,
xgboost or torch at runtime — which matters, because the deployed host installs
none of them. An earlier version of this module imported numpy and took the whole
service down on deploy: numpy is present locally only as a transitive dependency
of the Copernicus pipeline, which is not installed there.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

MODEL_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "ml" / "correction_model.json"

EARTH_RADIUS_KM = 6371.0

#: Beyond this the nearest station's bias is not the local bias. The eight
#: stations cover both coasts, so a boat off India is rarely further than this
#: from one — and when it is, saying so beats applying a correction from a
#: different sea.
MAX_STATION_KM = 400.0

#: The model was fitted at these lead times. A request in between takes the
#: nearest, which is reported rather than hidden.
FITTED_LEADS = (1, 2, 3)

#: Where each station sits. Must match ml/build_dataset.py.
STATIONS: dict[str, tuple[float, float]] = {
    "Digha": (21.6266, 87.5074),
    "Paradip": (20.2644, 86.6947),
    "Visakhapatnam": (17.6868, 83.2185),
    "Chennai": (13.0827, 80.2707),
    "Rameswaram": (9.2880, 79.3130),
    "Kochi": (9.9312, 76.2673),
    "Mangaluru": (12.8698, 74.8430),
    "Veraval": (20.9077, 70.3677),
}


@dataclass
class Correction:
    """A forecast value, what we think it should be, and how sure that is."""

    variable: str
    forecast: float
    corrected: float
    applied: bool
    reason: str
    station: str | None = None
    station_km: float | None = None
    lead_days: int | None = None
    #: Standard deviation of what is left over after correcting, measured on rows
    #: the coefficients were not fitted on. The width of the honest error bar.
    residual_sd: float | None = None
    quantiles: dict[str, float] = field(default_factory=dict)

    @property
    def adjustment(self) -> float:
        return self.corrected - self.forecast

    def exceedance_probability(self, threshold: float) -> float | None:
        """P(the real value is above `threshold`).

        Read off the empirical distribution of what the correction leaves behind,
        interpolated between measured quantiles, with a normal tail beyond the
        outermost ones. None when nothing was corrected — a probability implies a
        measured error distribution, and without one this would be a guess with a
        decimal point on it.
        """
        if not self.applied or not self.quantiles or self.residual_sd is None:
            return None

        # The real value exceeds the threshold when the leftover residual does.
        margin = threshold - self.corrected

        points = sorted((float(q), value) for q, value in self.quantiles.items())
        probabilities = [p for p, _ in points]
        values = [v for _, v in points]

        if margin <= values[0]:
            # Below everything measured: normal tail rather than a flat 1.0.
            if self.residual_sd <= 0:
                return 1.0
            return float(min(1.0, 1.0 - _normal_cdf((margin - values[0]) / self.residual_sd) * probabilities[0]))
        if margin >= values[-1]:
            if self.residual_sd <= 0:
                return 0.0
            tail = 1.0 - probabilities[-1]
            return float(max(0.0, tail * (1.0 - _normal_cdf((margin - values[-1]) / self.residual_sd))))

        # P(residual <= margin) interpolated, then inverted.
        below = _interpolate(margin, values, probabilities)
        return float(min(1.0, max(0.0, 1.0 - below)))

    def to_dict(self) -> dict:
        payload = {
            "variable": self.variable,
            "forecast": round(self.forecast, 3),
            "corrected": round(self.corrected, 3),
            "adjustment": round(self.adjustment, 3),
            "applied": self.applied,
            "reason": self.reason,
        }
        if self.applied:
            payload.update(
                {
                    "station": self.station,
                    "stationKm": round(self.station_km or 0.0, 1),
                    "leadDays": self.lead_days,
                    "residualSd": round(self.residual_sd or 0.0, 3),
                }
            )
        return payload


def _normal_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def _interpolate(x: float, xs: list[float], ys: list[float]) -> float:
    """Linear interpolation over ascending `xs`, clamped at both ends.

    Stands in for numpy.interp. The quantile table has seven points, so a scan
    costs nothing and saves a dependency the deployed host does not have.
    """
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for index in range(1, len(xs)):
        if x <= xs[index]:
            span = xs[index] - xs[index - 1]
            if span == 0:
                return ys[index]
            weight = (x - xs[index - 1]) / span
            return ys[index - 1] + weight * (ys[index] - ys[index - 1])
    return ys[-1]


def _dot(features: list[float], coefficients: list[float]) -> float:
    return sum(f * c for f, c in zip(features, coefficients))


def _distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def nearest_station(latitude: float, longitude: float) -> tuple[str, float]:
    """The station whose measured bias is most likely to be this boat's."""
    name, km = min(
        ((s, _distance_km(latitude, longitude, *coords)) for s, coords in STATIONS.items()),
        key=lambda pair: pair[1],
    )
    return name, km


@lru_cache(maxsize=1)
def _model() -> dict:
    """The fitted coefficients. An absent file is a reason to do nothing, not to fail."""
    try:
        return json.loads(MODEL_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"models": {}, "shipped_variables": []}


def _features(shape: str, forecast: float, day_of_year: int, hour: int) -> list[float]:
    columns = [1.0, forecast]
    if shape == "seasonal":
        columns += [
            math.sin(2 * math.pi * day_of_year / 365.25),
            math.cos(2 * math.pi * day_of_year / 365.25),
            math.sin(2 * math.pi * hour / 24.0),
            math.cos(2 * math.pi * hour / 24.0),
        ]
    return columns


def correct(
    variable: str,
    forecast: float,
    latitude: float,
    longitude: float,
    lead_days: float,
    day_of_year: int,
    hour: int,
) -> Correction:
    """Correct one forecast value, or explain why it was left alone."""
    model = _model()
    untouched = lambda why: Correction(  # noqa: E731 - one line, used four times below
        variable=variable, forecast=forecast, corrected=forecast, applied=False, reason=why
    )

    if variable not in model.get("shipped_variables", []):
        return untouched(
            "no correction for this variable — measured, and the gain was too small "
            "to change an answer (see docs/ml-plan.md)"
        )

    station, km = nearest_station(latitude, longitude)
    if km > MAX_STATION_KM:
        return untouched(f"nearest fitted station ({station}) is {km:.0f} km away")

    lead = min(FITTED_LEADS, key=lambda candidate: abs(candidate - lead_days))
    entry = model["models"].get(f"{variable}|{station}|{lead}")
    if entry is None:
        return untouched(f"no fitted correction for {station} at {lead} day(s)")

    beta = [float(c) for c in entry["coefficients"]]
    adjustment = _dot(_features(entry["shape"], forecast, day_of_year, hour), beta)

    corrected = forecast + adjustment
    # Wind and wave cannot be negative, and a linear correction near zero can
    # push them there.
    corrected = max(0.0, corrected)

    return Correction(
        variable=variable,
        forecast=forecast,
        corrected=corrected,
        applied=True,
        reason=f"bias correction fitted at {station}, {lead} day lead",
        station=station,
        station_km=km,
        lead_days=lead,
        residual_sd=float(entry["residual_sd"]),
        quantiles={str(k): float(v) for k, v in entry["residual_quantiles"].items()},
    )


def available() -> dict:
    """What this layer can currently correct — for /health and data discovery."""
    model = _model()
    return {
        "shipped_variables": model.get("shipped_variables", []),
        "groups": len(model.get("models", {})),
        "trained_at": model.get("trained_at"),
        "stations": sorted(STATIONS),
        "truth": model.get("truth"),
    }
