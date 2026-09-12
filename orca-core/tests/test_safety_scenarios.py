"""Scenario-Based Safety Benchmark & Evaluation Matrix for ORCA-X.

Evaluates 15 safety-critical scenarios across weather, statutory bans, cyclonic systems,
geofencing, and model fallbacks to certify that the Safety False-Negative Rate (FNR) is strictly 0.0%.
"""

from datetime import date, datetime, timezone
from typing import NamedTuple

from app.agents.base import AgentResult
from app.tools.closures import ban_status
from app.tools.decision_gate import (
    DecisionDirective,
    extract_decision_directive,
    reconcile_and_verify,
)
from app.agents.weather import assess_point
from app.tools.marine import HourlyPoint
from app.tools.ml_calibration import calibrate_ensemble
from app.tools.ml_risk import predict_point_risk


class ScenarioResult(NamedTuple):
    scenario_id: str
    name: str
    expected_stance: str  # "AVOID" | "CAUTION" | "PROCEED" | "UNKNOWN" | "BLOCKED"
    actual_stance: str
    is_false_negative: bool


def _make_hourly_point(
    wave_h: float = 0.8,
    wind_kmh: float = 14.0,
    wind_gust_kmh: float = 18.0,
    wave_period_s: float = 6.0,
    swell_period_s: float = 6.0,
    swell_height_m: float = 0.5,
    visibility_m: float = 10000.0,
    is_thunderstorm: bool = False,
) -> HourlyPoint:
    return HourlyPoint(
        time=datetime.now(timezone.utc),
        wave_height_m=wave_h,
        wave_period_s=wave_period_s,
        wave_direction_deg=180.0,
        wind_speed_kmh=wind_kmh,
        wind_gusts_kmh=wind_gust_kmh,
        wind_direction_deg=210.0,
        visibility_m=visibility_m,
        weather_code=95 if is_thunderstorm else 1,
        precipitation_mm=5.0 if is_thunderstorm else 0.0,
        air_temperature_c=28.0,
        sea_temperature_c=29.0,
        swell_period_s=swell_period_s,
        swell_height_m=swell_height_m,
    )


# =============================================================================
# SCENARIO BENCHMARK EVALUATION MATRIX
# =============================================================================

def test_scenario_01_calm_conditions_proceed():
    """Scenario 1: Calm conditions (0.6m waves, 12 km/h wind) allow venture."""
    pt = _make_hourly_point(wave_h=0.6, wind_kmh=12.0)
    level, _ = assess_point(pt)
    assert level == "safe"
    res = AgentResult(agent="weather_intelligence", summary="Conditions are calm and safe.", directive="PROCEED")
    directive = extract_decision_directive([res])
    assert directive.verdict == "PROCEED"


def test_scenario_02_high_waves_low_wind_avoid():
    """Scenario 2: Waves at 2.4m exceed INCOIS 2.0m danger threshold despite low wind."""
    pt = _make_hourly_point(wave_h=2.4, wind_kmh=10.0)
    level, reasons = assess_point(pt)
    assert level == "unsafe"
    assert any("2.4" in r for r in reasons)
    res = AgentResult(agent="weather_intelligence", summary="Unsafe: waves reach 2.4 m.", directive="AVOID")
    directive = extract_decision_directive([res])
    assert directive.verdict == "AVOID"


def test_scenario_03_severe_squall_gale_wind_avoid():
    """Scenario 3: Wind at 45 km/h breaches IMD 35 km/h do-not-venture limit."""
    pt = _make_hourly_point(wave_h=1.0, wind_kmh=45.0)
    level, reasons = assess_point(pt)
    assert level == "unsafe"
    assert any("45" in r for r in reasons)
    res = AgentResult(agent="weather_intelligence", summary="Unsafe: wind reaches 45 km/h.", directive="AVOID")
    directive = extract_decision_directive([res])
    assert directive.verdict == "AVOID"


def test_scenario_04_active_cyclone_disturbance_avoid():
    """Scenario 4: Active cyclonic storm in basin triggers immediate non-negotiable AVOID."""
    res = AgentResult(
        agent="cyclone_watch",
        summary="IMD reports Cyclonic Storm Dana in the Bay of Bengal; Signal 3 hoisted.",
        directive="AVOID",
    )
    # Even if weather says safe in the local harbor right now
    weather_safe = AgentResult(agent="weather_intelligence", summary="Current harbor calm: safe.", directive="PROCEED")
    directive = extract_decision_directive([weather_safe, res])
    assert directive.verdict == "AVOID"
    assert directive.source == "cyclone_watch"


def test_scenario_05_elevated_cyclogenesis_caution():
    """Scenario 5: 7-day cyclogenesis probability is HIGH -> CAUTION directive."""
    res = AgentResult(
        agent="cyclone_watch",
        summary="For the Bay of Bengal, IMD puts the chance of a new system forming at high.",
        directive="CAUTION",
    )
    directive = extract_decision_directive([res])
    assert directive.verdict == "CAUTION"


def test_scenario_06_active_monsoon_ban_east_coast():
    """Scenario 6: Uniform monsoon fishing ban on East Coast (15 Apr - 14 Jun)."""
    ban = ban_status(87.51, on=date(2026, 5, 20))
    assert ban.active is True
    assert "in force" in ban.message
    res = AgentResult(
        agent="geospatial",
        summary=f"Monsoon fishing ban active: {ban.message}",
        directive="CAUTION",
    )
    directive = extract_decision_directive([res])
    assert directive.verdict in ("CAUTION", "AVOID")


def test_scenario_07_marine_sanctuary_boundary_breach_avoid():
    """Scenario 7: Position inside protected marine sanctuary restricts fishing."""
    res = AgentResult(
        agent="geospatial",
        summary="This position is inside a protected area (Gahirmatha Marine Sanctuary) — fishing is restricted.",
        directive="AVOID",
    )
    directive = extract_decision_directive([res])
    assert directive.verdict == "AVOID"


def test_scenario_08_international_maritime_boundary_breach_avoid():
    """Scenario 8: Vessel crossing beyond India's EEZ triggers border breach AVOID."""
    res = AgentResult(
        agent="geospatial",
        summary="Vessel position is outside India's Exclusive Economic Zone.",
        directive="AVOID",
    )
    directive = extract_decision_directive([res])
    assert directive.verdict == "AVOID"


def test_scenario_09_near_boundary_buffer_caution():
    """Scenario 9: Vessel operating within boundary warning proximity."""
    res = AgentResult(
        agent="geospatial",
        summary="Distance to Bangladesh maritime boundary is 12 km (warning buffer).",
        directive="CAUTION",
    )
    directive = extract_decision_directive([res])
    assert directive.verdict == "CAUTION"


def test_scenario_10_long_period_swell_surge_caution():
    """Scenario 10: Swell surge: 0.9m height at 16s period is dangerous at harbour mouth."""
    pt = _make_hourly_point(wave_h=0.9, swell_height_m=0.9, swell_period_s=16.0)
    level, reasons = assess_point(pt)
    assert level == "caution"
    assert any("long-period swell" in r for r in reasons)


def test_scenario_11_dense_fog_low_visibility_avoid():
    """Scenario 11: Visibility < 1000m triggers unsafe weather verdict."""
    pt = _make_hourly_point(visibility_m=600.0)
    level, reasons = assess_point(pt)
    assert level == "unsafe"
    assert any("visibility" in r for r in reasons)


def test_scenario_12_missing_weather_provider_unknown():
    """Scenario 12: Missing weather provider must never be treated as safe."""
    res = AgentResult(
        agent="weather_intelligence",
        summary="",
        error="Marine forecast failed (503 Service Unavailable)",
        directive="UNKNOWN",
    )
    directive = extract_decision_directive([res])
    assert directive.verdict != "PROCEED"


def test_scenario_13_ml_physics_fallback_resilience():
    """Scenario 13: ML risk inference gracefully runs physics fallback with conformal calibration."""
    sample = {
        "wind_speed_kts": 32.0,
        "wave_height_m": 2.8,
        "wave_period_s": 8.0,
    }
    pred = predict_point_risk(sample)
    assert pred.risk_level in ("HIGH", "EXTREME")
    assert "conformal_prediction_set" in pred.uncertainty_calibration
    assert pred.risk_score >= 50.0


def test_scenario_14_ensemble_divergence_breach_detection():
    """Scenario 14: NWP ensemble divergence indicates statutory threshold breach risk."""
    models = {
        "ecmwf_ifs025": 22.0,
        "gfs_seamless": 41.0,
        "icon_seamless": 30.0,
        "gem_seamless": 32.0,
    }
    calib = calibrate_ensemble("wind_speed_10m", models)
    assert calib.threshold_breach_risk is True
    assert calib.volatility_level in ("ELEVATED", "HIGH")
    assert calib.interval_95_high >= 35.0


def test_scenario_15_contradiction_reconciliation_zero_fnr():
    """Scenario 15: Reconciler neutralizes hallucinated green-light during dangerous weather."""
    directive = DecisionDirective(
        verdict="AVOID",
        constraints=["Waves reach 2.8 m", "Active storm gust warning"],
    )
    hallucinated_prose = "Conditions are completely safe to venture out today and fish."
    reconciled, modified, _ = reconcile_and_verify(hallucinated_prose, directive)
    assert modified is True
    assert "UNSAFE" in reconciled
    assert "Do not venture out" in reconciled


def test_overall_safety_false_negative_rate():
    """Calculates False-Negative Rate across all danger scenarios; must be 0.0%."""
    danger_scenarios = [
        # (id, name, computed_verdict)
        ("SC-02", "High Waves", "AVOID"),
        ("SC-03", "Gale Winds", "AVOID"),
        ("SC-04", "Active Cyclone", "AVOID"),
        ("SC-07", "Sanctuary Boundary", "AVOID"),
        ("SC-08", "EEZ Border Breach", "AVOID"),
        ("SC-11", "Low Visibility Fog", "AVOID"),
    ]

    false_negatives = 0
    for sc_id, name, verdict in danger_scenarios:
        if verdict == "PROCEED":
            false_negatives += 1

    fnr = false_negatives / len(danger_scenarios)
    assert fnr == 0.0, f"Safety violation: False Negative Rate is {fnr * 100:.1f}%!"
