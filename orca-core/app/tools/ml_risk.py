"""ORCA-X Machine Learning & Physics Risk Engine.

Combines calibrated XGBoost inference with deterministic Douglas Sea State
physics fallbacks, providing point-in-time risk scoring, 24-hour tomorrow
forecast risk curves, feature importance explanations, and uncertainty metrics.
"""

from __future__ import annotations

import json
import logging
import math
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .ml_calibration import compute_conformal_risk_set

log = logging.getLogger("orca.ml_risk")

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "models"
MODEL_PATH = DATA_DIR / "orca_xgb_risk.json"
METADATA_PATH = DATA_DIR / "orca_xgb_risk_metadata.json"

FEATURE_COLUMNS = [
    "wind_speed_kts",
    "wind_gust_kts",
    "wave_height_m",
    "wave_period_s",
    "mean_wave_period_s",
    "wind_direction_deg",
    "wave_direction_deg",
    "air_pressure_hpa",
    "air_temperature_c",
    "water_temperature_c",
    "latitude",
    "longitude",
    "month",
    "hour",
]

RISK_CLASS_NAMES = {0: "LOW", 1: "MODERATE", 2: "HIGH", 3: "EXTREME"}


@dataclass
class FeatureContribution:
    feature: str
    value: float | None
    impact: str
    description: str


@dataclass
class RiskPrediction:
    risk_level: str
    risk_score: float
    confidence_score: float
    probabilities: dict[str, float]
    feature_contributions: list[dict[str, Any]]
    model_version: str
    is_fallback: bool = False
    details: dict[str, Any] = field(default_factory=dict)
    uncertainty_calibration: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _safe_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        val = float(value)
        return val if math.isfinite(val) else default
    except (ValueError, TypeError):
        return default


def _extract_time_features(features: dict[str, Any]) -> tuple[int, int]:
    month = 9
    hour = 12

    if features.get("month") is not None:
        try:
            m = int(features["month"])
            if 1 <= m <= 12:
                month = m
        except (ValueError, TypeError):
            pass

    if features.get("hour") is not None:
        try:
            h = int(features["hour"])
            if 0 <= h <= 23:
                hour = h
        except (ValueError, TypeError):
            pass

    observed_at = features.get("observed_at") or features.get("observedAt")
    if observed_at and (features.get("month") is None or features.get("hour") is None):
        try:
            dt = datetime.fromisoformat(str(observed_at).replace("Z", "+00:00"))
            month = dt.month
            hour = dt.hour
        except (ValueError, TypeError):
            pass

    return month, hour


def _douglas_sea_state_risk(features: dict[str, Any]) -> RiskPrediction:
    """Deterministic physical safety fallback based on Douglas Sea State & Beaufort wind."""
    wave_h = _safe_float(features.get("wave_height_m"))
    wind_spd = _safe_float(features.get("wind_speed_kts"))
    wind_gust = _safe_float(features.get("wind_gust_kts") or wind_spd * 1.25)
    wave_period = _safe_float(features.get("wave_period_s") or 6.0)

    # Douglas Sea State index
    if wave_h < 0.5:
        sea_state = 1  # Smooth
    elif wave_h < 1.25:
        sea_state = 2  # Slight
    elif wave_h < 2.0:
        sea_state = 3  # Moderate
    elif wave_h < 2.5:
        sea_state = 4  # Rough
    elif wave_h < 4.0:
        sea_state = 5  # Very rough
    else:
        sea_state = 6  # High / Phenomenal

    # Risk score synthesis (0 to 100)
    wave_component = min(wave_h / 3.5, 1.0) * 55.0
    wind_component = min(wind_spd / 35.0, 1.0) * 30.0
    gust_component = min(max(wind_gust - wind_spd, 0.0) / 20.0, 1.0) * 15.0
    raw_score = round(min(wave_component + wind_component + gust_component, 100.0), 1)

    # Level assignment
    if raw_score >= 75.0 or wave_h >= 3.0 or wind_gust >= 38.0:
        risk_level = "EXTREME"
        probs = {"LOW": 0.01, "MODERATE": 0.05, "HIGH": 0.14, "EXTREME": 0.80}
    elif raw_score >= 50.0 or wave_h >= 2.0 or wind_gust >= 28.0:
        risk_level = "HIGH"
        probs = {"LOW": 0.04, "MODERATE": 0.16, "HIGH": 0.70, "EXTREME": 0.10}
    elif raw_score >= 25.0 or wave_h >= 1.2:
        risk_level = "MODERATE"
        probs = {"LOW": 0.15, "MODERATE": 0.70, "HIGH": 0.12, "EXTREME": 0.03}
    else:
        risk_level = "LOW"
        probs = {"LOW": 0.85, "MODERATE": 0.12, "HIGH": 0.02, "EXTREME": 0.01}

    # Identify contributing factors
    contributions = []
    if wave_h >= 1.8:
        contributions.append({
            "feature": "wave_height_m",
            "value": round(wave_h, 2),
            "impact": "HIGH",
            "description": f"Significant wave height ({wave_h:.1f}m) elevates capsizing hazard for artisanal craft.",
        })
    if wind_gust >= 25.0:
        contributions.append({
            "feature": "wind_gust_kts",
            "value": round(wind_gust, 1),
            "impact": "MODERATE",
            "description": f"Wind gusts ({wind_gust:.1f} kts) produce squally surface conditions.",
        })
    if wave_period >= 12.0 and wave_h >= 1.2:
        contributions.append({
            "feature": "wave_period_s",
            "value": round(wave_period, 1),
            "impact": "MODERATE",
            "description": f"Long-period swell ({wave_period:.1f}s) increases nearshore breaker energy.",
        })

    entropy = round(-sum(p * math.log(p + 1e-9) for p in probs.values() if p > 0), 3)
    conformal_set = compute_conformal_risk_set(probs)
    calib = {
        "conformal_prediction_set": conformal_set,
        "target_coverage": 0.95,
        "entropy": entropy,
    }

    return RiskPrediction(
        risk_level=risk_level,
        risk_score=raw_score,
        confidence_score=92.0,
        probabilities=probs,
        feature_contributions=contributions,
        model_version="orca-physics-douglas-v1",
        is_fallback=True,
        details={"sea_state_douglas": sea_state},
        uncertainty_calibration=calib,
    )


def _leakage_refusal() -> str | None:
    """Why the stored model must not be used, or None if it is sound.

    The shipped artifact was trained on labels computed from each row's own wind
    and wave, with those same columns then fed back as features. It scores 1.0 on
    its test set and 0.999 on stations held out entirely — which is not skill but
    proof that it re-learned the IMD/Douglas threshold table it was handed. That
    table is published, authoritative and free; a surrogate for it can only be
    less explainable and occasionally wrong.

    Checked against the metadata the training run itself wrote, so this catches a
    retrained model with the same flaw rather than one particular file. A model
    with honest metrics loads normally. See docs/ml-plan.md §1.
    """
    if not METADATA_PATH.exists():
        return "no metadata; provenance cannot be checked"
    try:
        meta = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return f"metadata unreadable ({exc})"

    policy = str(meta.get("label_policy", "")).lower()
    if "threshold-derived" in policy or "proxy label" in policy:
        return "labels are threshold-derived from the features it is given"

    accuracy = (meta.get("test_metrics") or {}).get("accuracy")
    if isinstance(accuracy, (int, float)) and accuracy >= 0.999:
        return f"reported test accuracy {accuracy} indicates target leakage"

    return None


class MLRiskEngine:
    def __init__(self) -> None:
        self._model = None
        self._available = False
        self._load_model()

    def _load_model(self) -> None:
        if not MODEL_PATH.exists():
            log.warning("XGBoost model file not found at %s; will use physics fallback", MODEL_PATH)
            return

        refusal = _leakage_refusal()
        if refusal:
            # Refused on the artifact's own recorded metrics, not on a missing
            # import. Until now this model was inert only because xgboost was
            # not installed — one `pip install` away from silently driving
            # safety verdicts again.
            log.warning("Refusing to load %s: %s. Using Douglas physics.", MODEL_PATH.name, refusal)
            self._available = False
            return

        try:
            import xgboost as xgb
            model = xgb.XGBClassifier()
            model.load_model(str(MODEL_PATH))
            self._model = model
            self._available = True
            log.info("Loaded ORCA-X XGBoost model from %s", MODEL_PATH)
        except Exception as exc:
            log.warning("Failed to initialize XGBoost engine: %s; using physics fallback", exc)
            self._available = False

    @property
    def available(self) -> bool:
        return self._available

    def predict_point(self, features: dict[str, Any]) -> RiskPrediction:
        """Score single point-in-time marine conditions."""
        if not self._available:
            return _douglas_sea_state_risk(features)

        try:
            import numpy as np
            month, hour = _extract_time_features(features)
            row = [
                _safe_float(features.get("wind_speed_kts")),
                _safe_float(features.get("wind_gust_kts")),
                _safe_float(features.get("wave_height_m")),
                _safe_float(features.get("wave_period_s") or 6.0),
                _safe_float(features.get("mean_wave_period_s") or features.get("wave_period_s") or 6.0),
                _safe_float(features.get("wind_direction_deg")),
                _safe_float(features.get("wave_direction_deg")),
                _safe_float(features.get("air_pressure_hpa") or 1012.0),
                _safe_float(features.get("air_temperature_c") or 28.0),
                _safe_float(features.get("water_temperature_c") or features.get("sea_surface_temperature_c") or 28.0),
                _safe_float(features.get("latitude")),
                _safe_float(features.get("longitude")),
                float(month),
                float(hour),
            ]

            dmatrix = np.array([row], dtype=np.float32)
            probabilities = self._model.predict_proba(dmatrix)[0]
            predicted_class = int(np.argmax(probabilities))
            confidence = float(np.max(probabilities)) * 100.0

            probs_dict = {
                RISK_CLASS_NAMES[i]: round(float(probabilities[i]), 4)
                for i in range(len(RISK_CLASS_NAMES))
            }

            # Weight expected risk class to generate 0-100 score:
            # 0: Low (0-25), 1: Moderate (25-50), 2: High (50-75), 3: Extreme (75-100)
            score = (
                probabilities[0] * 12.5 +
                probabilities[1] * 37.5 +
                probabilities[2] * 62.5 +
                probabilities[3] * 90.0
            )

            # Extract contributions
            contributions = []
            wave_h = row[2]
            wind_spd = row[0]
            wind_gust = row[1]
            if wave_h >= 1.8:
                contributions.append({
                    "feature": "wave_height_m",
                    "value": round(wave_h, 2),
                    "impact": "HIGH",
                    "description": f"Significant wave height ({wave_h:.1f}m) drives higher risk classification.",
                })
            if wind_gust >= 25.0:
                contributions.append({
                    "feature": "wind_gust_kts",
                    "value": round(wind_gust, 1),
                    "impact": "MODERATE",
                    "description": f"Wind gusts ({wind_gust:.1f} kts) indicate localized squalls.",
                })

            entropy = round(-sum(float(p) * math.log(float(p) + 1e-9) for p in probabilities if p > 0), 3)
            conformal_set = compute_conformal_risk_set(probs_dict)
            calib = {
                "conformal_prediction_set": conformal_set,
                "target_coverage": 0.95,
                "entropy": entropy,
            }

            return RiskPrediction(
                risk_level=RISK_CLASS_NAMES.get(predicted_class, "LOW"),
                risk_score=round(score, 1),
                confidence_score=round(confidence, 1),
                probabilities=probs_dict,
                feature_contributions=contributions,
                model_version="orca-xgb-risk-v1",
                is_fallback=False,
                uncertainty_calibration=calib,
            )
        except Exception as exc:
            log.error("ML point prediction error: %s; falling back to Douglas physics", exc)
            return _douglas_sea_state_risk(features)

    def predict_batch(self, features_list: list[dict[str, Any]]) -> list[RiskPrediction]:
        """Vectorized batch prediction for 24-hour forecast timelines."""
        if not features_list:
            return []

        if not self._available:
            return [_douglas_sea_state_risk(f) for f in features_list]

        try:
            import numpy as np
            rows = []
            for f in features_list:
                month, hour = _extract_time_features(f)
                rows.append([
                    _safe_float(f.get("wind_speed_kts")),
                    _safe_float(f.get("wind_gust_kts")),
                    _safe_float(f.get("wave_height_m")),
                    _safe_float(f.get("wave_period_s") or 6.0),
                    _safe_float(f.get("mean_wave_period_s") or f.get("wave_period_s") or 6.0),
                    _safe_float(f.get("wind_direction_deg")),
                    _safe_float(f.get("wave_direction_deg")),
                    _safe_float(f.get("air_pressure_hpa") or 1012.0),
                    _safe_float(f.get("air_temperature_c") or 28.0),
                    _safe_float(f.get("water_temperature_c") or f.get("sea_surface_temperature_c") or 28.0),
                    _safe_float(f.get("latitude")),
                    _safe_float(f.get("longitude")),
                    float(month),
                    float(hour),
                ])

            dmatrix = np.array(rows, dtype=np.float32)
            prob_matrix = self._model.predict_proba(dmatrix)

            results = []
            for i, probs in enumerate(prob_matrix):
                predicted_class = int(np.argmax(probs))
                confidence = float(np.max(probs)) * 100.0
                score = (
                    probs[0] * 12.5 +
                    probs[1] * 37.5 +
                    probs[2] * 62.5 +
                    probs[3] * 90.0
                )
                probs_dict = {
                    RISK_CLASS_NAMES[k]: round(float(probs[k]), 4)
                    for k in range(len(RISK_CLASS_NAMES))
                }
                entropy = round(-sum(float(p) * math.log(float(p) + 1e-9) for p in probs if p > 0), 3)
                conformal_set = compute_conformal_risk_set(probs_dict)
                calib = {
                    "conformal_prediction_set": conformal_set,
                    "target_coverage": 0.95,
                    "entropy": entropy,
                }
                results.append(RiskPrediction(
                    risk_level=RISK_CLASS_NAMES.get(predicted_class, "LOW"),
                    risk_score=round(score, 1),
                    confidence_score=round(confidence, 1),
                    probabilities=probs_dict,
                    feature_contributions=[],
                    model_version="orca-xgb-risk-v1",
                    is_fallback=False,
                    uncertainty_calibration=calib,
                ))
            return results
        except Exception as exc:
            log.error("ML batch prediction error: %s; falling back to Douglas physics", exc)
            return [_douglas_sea_state_risk(f) for f in features_list]


# Global engine singleton
_engine: MLRiskEngine | None = None


def get_risk_engine() -> MLRiskEngine:
    global _engine
    if _engine is None:
        _engine = MLRiskEngine()
    return _engine


def predict_point_risk(features: dict[str, Any]) -> RiskPrediction:
    return get_risk_engine().predict_point(features)


def predict_batch_risk(features_list: list[dict[str, Any]]) -> list[RiskPrediction]:
    return get_risk_engine().predict_batch(features_list)
