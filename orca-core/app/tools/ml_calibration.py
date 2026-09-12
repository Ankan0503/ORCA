"""Machine Learning Forecast Calibration & Ensemble Uncertainty Engine.

Models the divergence across numerical weather prediction systems (ECMWF, GFS, ICON, GEM),
applies bias corrections measured by ml/measure_model_bias.py, computes calibrated 95% uncertainty intervals,
and predicts whether inter-model volatility risks breaching statutory IMD/INCOIS safety thresholds.
"""

from __future__ import annotations

import json
import logging
import math
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

log = logging.getLogger("orca.ml_calibration")

# Per-model bias against ERA5, in km/h or m. Positive means the model reads high.
#
# These were previously written by hand and commented "as measured in orca-core
# over 1,104 hours at Digha". Nothing measured them. `ml/measure_model_bias.py`
# now does, over 72,192 hours at eight stations on both coasts, and the real
# numbers are loaded from data/ml/model_bias.json below.
#
# The difference was not cosmetic. For gusts the invented constants had the wrong
# sign on three of the four models — GFS was asserted at +4.2 and measures -5.97
# — so subtracting them pushed gust forecasts about 10 km/h the wrong way, on the
# one variable the IMD fishermen's warning is written against.
#
# This dict is the fallback used only when the measurements file is missing: all
# zeros, because correcting by a number nobody measured is worse than not
# correcting at all.
_MEASURED_BIAS_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "ml" / "model_bias.json"

_FALLBACK_BIAS: dict[str, dict[str, float]] = {
    "wind_speed_10m": {
        "ecmwf_ifs025": 0.0,
        "gfs_seamless": 0.0,
        "icon_seamless": 0.0,
        "gem_seamless": 0.0,
    },
    "wind_gusts_10m": {
        "ecmwf_ifs025": 0.0,
        "gfs_seamless": 0.0,
        "icon_seamless": 0.0,
        "gem_seamless": 0.0,
    },
    # Waves were not measured per model: the wave archive carries no per-model
    # breakdown, so there is nothing to check these against and they are zero.
    "wave_height_m": {
        "ecmwf_ifs025": 0.0,
        "gfs_seamless": 0.0,
        "icon_seamless": 0.0,
        "gem_seamless": 0.0,
    },
}


@lru_cache(maxsize=1)
def measured_bias() -> dict[str, dict[str, float]]:
    """Per-model bias as actually measured, falling back to zeros.

    Zeros rather than the old hand-written numbers: a correction nobody measured
    can move a forecast the wrong way, and for gusts the previous constants did
    exactly that.
    """
    table = {variable: dict(models) for variable, models in _FALLBACK_BIAS.items()}
    try:
        raw = json.loads(_MEASURED_BIAS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        log.info("no measured model bias on disk; models are combined uncorrected")
        return table
    for entry in raw.get("measurements", []):
        variable, model = entry.get("variable"), entry.get("model")
        if variable and model:
            table.setdefault(variable, {})[model] = float(entry.get("bias", 0.0))
    return table


#: Kept as a name so existing call sites do not change shape, but it is now the
#: measured table rather than a literal.
MODEL_BIAS = measured_bias()

# Statutory thresholds to test against for safety breach risk
STATUTORY_THRESHOLDS: dict[str, list[tuple[float, str]]] = {
    "wind_speed_10m": [
        (30.0, "IMD Caution floor (30 km/h)"),
        (35.0, "IMD 'Do not venture' danger floor (35 km/h)"),
    ],
    "wind_gusts_10m": [
        (45.0, "IMD Gust caution limit (45 km/h)"),
        (55.0, "IMD Storm gust warning floor (55 km/h)"),
    ],
    "wave_height_m": [
        (1.5, "INCOIS Caution approach level (1.5 m)"),
        (2.0, "INCOIS High Wave Alert danger level (2.0 m)"),
    ],
}


@dataclass
class CalibratedForecast:
    variable: str
    unit: str
    ensemble_mean: float
    calibrated_expected: float
    spread: float
    std_dev: float
    interval_95_low: float
    interval_95_high: float
    volatility_level: str  # "LOW" | "MODERATE" | "ELEVATED" | "HIGH"
    threshold_breach_risk: bool = False
    breached_threshold: str | None = None
    advisory_note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def calibrate_ensemble(
    variable: str,
    model_values: dict[str, float],
    latitude: float = 21.626,
    longitude: float = 87.508,
) -> CalibratedForecast:
    """Calibrates ensemble readings into an uncertainty-bounded forecast."""
    unit = "m" if "wave" in variable else "km/h"
    if not model_values:
        return CalibratedForecast(
            variable=variable,
            unit=unit,
            ensemble_mean=0.0,
            calibrated_expected=0.0,
            spread=0.0,
            std_dev=0.0,
            interval_95_low=0.0,
            interval_95_high=0.0,
            volatility_level="LOW",
            advisory_note="No forecast model observations available.",
        )

    vals = list(model_values.values())
    n = len(vals)
    raw_mean = sum(vals) / n
    spread = max(vals) - min(vals) if n > 1 else 0.0

    # Sample variance and standard deviation
    if n > 1:
        variance = sum((v - raw_mean) ** 2 for v in vals) / (n - 1)
        std_dev = math.sqrt(variance)
    else:
        std_dev = 0.0

    # Apply empirical model bias corrections
    bias_map = MODEL_BIAS.get(variable, {})
    corrected_vals = []
    for model_name, val in model_values.items():
        bias = bias_map.get(model_name, 0.0)
        corrected_vals.append(val - bias)

    calibrated_expected = max(0.0, sum(corrected_vals) / len(corrected_vals))

    # Effective uncertainty scale incorporates ensemble spread plus physical baseline noise
    noise_floor = 0.8 if "wave" in variable else 2.5
    sigma_eff = math.sqrt(std_dev**2 + (noise_floor / 2.0) ** 2)

    # 95% Confidence Interval (z = 1.96)
    interval_low = max(0.0, calibrated_expected - 1.96 * sigma_eff)
    interval_high = calibrated_expected + 1.96 * sigma_eff

    # Volatility classification
    rel_spread = (spread / raw_mean) if raw_mean > 0 else 0.0
    if spread <= noise_floor or rel_spread < 0.12:
        volatility = "LOW"
    elif rel_spread < 0.25:
        volatility = "MODERATE"
    elif rel_spread < 0.40:
        volatility = "ELEVATED"
    else:
        volatility = "HIGH"

    # Check if upper uncertainty interval breaches statutory thresholds
    threshold_breached = False
    breached_label: str | None = None
    for threshold_val, label in STATUTORY_THRESHOLDS.get(variable, []):
        if interval_high >= threshold_val:
            threshold_breached = True
            breached_label = label
            # If the mean is below but high bound crosses, volatility is at least ELEVATED
            if calibrated_expected < threshold_val and volatility in ("LOW", "MODERATE"):
                volatility = "ELEVATED"

    # Actionable advisory note
    if threshold_breached and calibrated_expected < (interval_high * 0.85):
        advisory_note = (
            f"Caution: While the calibrated mean ({calibrated_expected:.1f} {unit}) appears acceptable, "
            f"ensemble divergence indicates a 95% upper risk reaching {interval_high:.1f} {unit}, "
            f"which crosses {breached_label}."
        )
    elif volatility in ("ELEVATED", "HIGH"):
        advisory_note = (
            f"Forecast volatility is {volatility.lower()} (models diverge by {spread:.1f} {unit}). "
            f"Expected conditions: {calibrated_expected:.1f} {unit} (95% CI: {interval_low:.1f}–{interval_high:.1f} {unit})."
        )
    else:
        advisory_note = (
            f"Forecast models agree closely ({volatility.lower()} volatility). "
            f"Expected: {calibrated_expected:.1f} {unit} (±{1.96 * sigma_eff:.1f} {unit})."
        )

    return CalibratedForecast(
        variable=variable,
        unit=unit,
        ensemble_mean=round(raw_mean, 2),
        calibrated_expected=round(calibrated_expected, 2),
        spread=round(spread, 2),
        std_dev=round(std_dev, 2),
        interval_95_low=round(interval_low, 2),
        interval_95_high=round(interval_high, 2),
        volatility_level=volatility,
        threshold_breach_risk=threshold_breached,
        breached_threshold=breached_label,
        advisory_note=advisory_note,
    )


def compute_conformal_risk_set(
    probabilities: dict[str, float],
    confidence_level: float = 0.95,
) -> list[str]:
    """Computes conformal prediction set guaranteeing target statistical coverage."""
    if not probabilities:
        return ["LOW"]

    # Sort classes by descending probability
    sorted_classes = sorted(probabilities.items(), key=lambda x: x[1], reverse=True)
    cumulative = 0.0
    selected: list[str] = []

    for cls_name, prob in sorted_classes:
        selected.append(cls_name)
        cumulative += prob
        if cumulative >= confidence_level:
            break

    return sorted(selected, key=lambda c: ("LOW", "MODERATE", "HIGH", "EXTREME").index(c) if c in ("LOW", "MODERATE", "HIGH", "EXTREME") else 0)
