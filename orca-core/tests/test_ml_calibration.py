"""Tests for ML Forecast Calibration & Ensemble Uncertainty Engine."""

from app.tools.ml_calibration import (
    calibrate_ensemble,
    compute_conformal_risk_set,
)
from app.tools.ml_risk import predict_point_risk, predict_batch_risk
from app.tools.agreement import Comparison, AgreementReport


def test_calibrate_ensemble_tight_agreement():
    """Tight agreement across models yields LOW volatility and narrow 95% interval."""
    model_values = {
        "ecmwf_ifs025": 12.0,
        "gfs_seamless": 13.0,
        "icon_seamless": 12.5,
        "gem_seamless": 12.2,
    }
    calib = calibrate_ensemble("wind_speed_10m", model_values)
    assert calib.volatility_level == "LOW"
    assert calib.threshold_breach_risk is False
    assert calib.interval_95_low < calib.calibrated_expected < calib.interval_95_high
    assert "close" in calib.advisory_note.lower() or "low" in calib.advisory_note.lower()


def test_calibrate_ensemble_divergence_breaches_threshold():
    """Wide inter-model divergence where 95% upper bound breaches IMD 35 km/h limit."""
    model_values = {
        "ecmwf_ifs025": 24.0,
        "gfs_seamless": 40.0,
        "icon_seamless": 31.0,
        "gem_seamless": 33.0,
    }
    calib = calibrate_ensemble("wind_speed_10m", model_values)
    assert calib.volatility_level in ("ELEVATED", "HIGH")
    assert calib.threshold_breach_risk is True
    assert calib.breached_threshold is not None
    assert "IMD" in calib.breached_threshold
    assert calib.interval_95_high >= 35.0


def test_calibrate_ensemble_wave_height_incois_breach():
    """Wave models diverging around 1.8-2.3m trigger INCOIS alert threshold breach."""
    model_values = {
        "ecmwf_ifs025": 1.7,
        "gfs_seamless": 2.3,
        "icon_seamless": 1.9,
        "gem_seamless": 2.0,
    }
    calib = calibrate_ensemble("wave_height_m", model_values)
    assert calib.threshold_breach_risk is True
    assert "INCOIS" in str(calib.breached_threshold)
    assert calib.unit == "m"


def test_calibrate_ensemble_empty_and_single():
    """Empty or single model values handle gracefully without throwing errors."""
    empty = calibrate_ensemble("wind_speed_10m", {})
    assert empty.volatility_level == "LOW"
    assert empty.calibrated_expected == 0.0

    single = calibrate_ensemble("wind_speed_10m", {"ecmwf_ifs025": 15.0})
    assert single.spread == 0.0
    assert single.std_dev == 0.0


def test_conformal_risk_set_coverage():
    """Conformal prediction set expands when uncertainty is high and contracts when sharp."""
    # Sharp low-risk distribution
    sharp_low = {"LOW": 0.96, "MODERATE": 0.03, "HIGH": 0.01, "EXTREME": 0.0}
    c_set = compute_conformal_risk_set(sharp_low, confidence_level=0.95)
    assert c_set == ["LOW"]

    # Ambiguous boundary distribution between MODERATE and HIGH
    ambiguous = {"LOW": 0.05, "MODERATE": 0.52, "HIGH": 0.40, "EXTREME": 0.03}
    c_set2 = compute_conformal_risk_set(ambiguous, confidence_level=0.95)
    assert "MODERATE" in c_set2
    assert "HIGH" in c_set2
    assert len(c_set2) >= 2


def test_ml_risk_engine_uncertainty_calibration():
    """predict_point_risk returns calibrated conformal prediction set and entropy."""
    # Moderate wave conditions
    sample = {
        "wind_speed_kts": 14.0,
        "wind_gust_kts": 18.0,
        "wave_height_m": 1.5,
        "wave_period_s": 6.5,
        "latitude": 21.626,
        "longitude": 87.508,
    }
    pred = predict_point_risk(sample)
    assert hasattr(pred, "uncertainty_calibration")
    calib = pred.uncertainty_calibration
    assert "conformal_prediction_set" in calib
    assert "entropy" in calib
    assert calib["target_coverage"] == 0.95
    assert isinstance(calib["conformal_prediction_set"], list)
    assert calib["entropy"] >= 0.0


def test_ml_risk_batch_uncertainty_calibration():
    """predict_batch_risk embeds uncertainty calibration into all timeline points."""
    samples = [
        {"wave_height_m": 0.5, "wind_speed_kts": 8.0},
        {"wave_height_m": 2.2, "wind_speed_kts": 25.0},
    ]
    preds = predict_batch_risk(samples)
    assert len(preds) == 2
    for p in preds:
        assert "conformal_prediction_set" in p.uncertainty_calibration
        assert p.uncertainty_calibration["entropy"] >= 0.0


def test_agreement_report_with_calibration():
    """AgreementReport serializes thresholdBreachRisk and calibration blocks."""
    comp = Comparison(
        variable="wind_speed_10m",
        unit="km/h",
        values={"ecmwf_ifs025": 20.0, "gfs_seamless": 38.0},
    )
    comp.calibration = calibrate_ensemble(comp.variable, comp.values)
    report = AgreementReport(
        latitude=21.626,
        longitude=87.508,
        hours_ahead=0,
        comparisons=[comp],
        unavailable=[],
    )
    d = report.to_dict()
    assert "thresholdBreachRisk" in d
    assert "calibration" in d["comparisons"][0]
    assert d["comparisons"][0]["calibration"]["volatility_level"] in ("ELEVATED", "HIGH")
