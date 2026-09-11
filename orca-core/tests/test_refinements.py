"""Tests for the integrated ML Risk, Decision Fusion, Statutory Evidence, and Marine Tools."""

import pytest
from app.tools.ml_risk import MLRiskEngine, predict_point_risk, predict_batch_risk, _douglas_sea_state_risk
from app.tools.fusion import fuse_marine_decision
from app.tools.evidence import seed_statutory_corpus, search, load_corpus
from app.tools.oil_spill import analyze_oil_spills
from app.tools.vessels import get_live_vessels, OFFICIAL_MOES_BUOY_STATIONS


# --- 1. ML Risk & Douglas Physics Tests -------------------------------------


def test_ml_risk_engine_point_prediction():
    sample = {
        "wind_speed_kts": 10.0,
        "wind_gust_kts": 14.0,
        "wave_height_m": 0.8,
        "wave_period_s": 5.5,
        "latitude": 21.626,
        "longitude": 87.508,
    }
    pred = predict_point_risk(sample)
    assert pred.risk_level in ("LOW", "MODERATE", "HIGH", "EXTREME")
    assert 0.0 <= pred.risk_score <= 100.0
    assert pred.confidence_score > 50.0


def test_ml_risk_high_hazard_detection():
    hazardous = {
        "wind_speed_kts": 35.0,
        "wind_gust_kts": 45.0,
        "wave_height_m": 3.8,
        "wave_period_s": 9.5,
        "latitude": 21.626,
        "longitude": 87.508,
    }
    pred = predict_point_risk(hazardous)
    assert pred.risk_level in ("HIGH", "EXTREME")
    assert pred.risk_score >= 50.0
    assert len(pred.feature_contributions) > 0


def test_ml_risk_batch_prediction():
    items = [
        {"wind_speed_kts": 8.0, "wave_height_m": 0.6, "latitude": 21.626, "longitude": 87.508},
        {"wind_speed_kts": 22.0, "wave_height_m": 2.2, "latitude": 21.626, "longitude": 87.508},
    ]
    preds = predict_batch_risk(items)
    assert len(preds) == 2
    assert preds[0].risk_score < preds[1].risk_score


def test_douglas_sea_state_fallback():
    sample = {
        "wind_speed_kts": 15.0,
        "wind_gust_kts": 20.0,
        "wave_height_m": 1.6,
        "wave_period_s": 6.0,
    }
    fallback = _douglas_sea_state_risk(sample)
    assert fallback.is_fallback is True
    assert fallback.model_version == "orca-physics-douglas-v1"
    assert fallback.risk_level in ("LOW", "MODERATE", "HIGH", "EXTREME")


# --- 2. Decision Fusion Tests ------------------------------------------------


def test_decision_fusion_clear_proceed():
    risk = {"risk_level": "LOW", "risk_score": 15.0, "confidence_score": 90.0}
    geofence = {"status": "CLEAR", "in_restricted_waters": False, "distance_to_boundary_km": 120.0}
    pfz = {"status": "READY", "best_zone": "Digha Sector A"}

    result = fuse_marine_decision(risk=risk, geofence=geofence, pfz=pfz)
    assert result.decision == "PROCEED"
    assert result.confidence == "HIGH"
    assert result.score > 70


def test_decision_fusion_monsoon_ban_overrides_all():
    risk = {"risk_level": "LOW", "risk_score": 10.0, "confidence_score": 95.0}
    closures = {"active": True, "reason": "Annual uniform monsoon ban active on East Coast"}

    result = fuse_marine_decision(risk=risk, closures=closures)
    assert result.decision == "AVOID"
    assert result.score == 0
    assert "monsoon" in result.rationale.lower()


def test_decision_fusion_geofence_breach_overrides_pfz():
    risk = {"risk_level": "LOW", "risk_score": 10.0, "confidence_score": 90.0}
    geofence = {"status": "CRITICAL", "in_restricted_waters": True, "distance_to_boundary_km": 2.0}
    pfz = {"status": "READY", "best_zone": "High Density Tuna Aggregation"}

    result = fuse_marine_decision(risk=risk, geofence=geofence, pfz=pfz)
    assert result.decision == "AVOID"
    assert result.score == 0
    assert any("restricted" in w.lower() for w in result.warnings)


def test_decision_fusion_extreme_risk_caution():
    risk = {"risk_level": "EXTREME", "risk_score": 88.0, "confidence_score": 95.0}
    result = fuse_marine_decision(risk=risk)
    assert result.decision == "AVOID"
    assert result.score <= 10


# --- 3. Statutory Evidence Corpus Tests --------------------------------------


def test_statutory_evidence_seed_and_search():
    stats = seed_statutory_corpus()
    assert stats["status"] == "ok"
    assert stats["corpus_total"] >= 14

    hits = search("monsoon ban trawl dates")
    assert len(hits) > 0
    top_hit = hits[0]
    assert top_hit.score > 0.0
    assert top_hit.document.authority != ""

    hits_vhf = search("coast guard vhf channel 16 emergency")
    assert len(hits_vhf) > 0


# --- 4. Marine Tools Tests (Oil Spill & Vessels) -----------------------------


@pytest.mark.asyncio
async def test_oil_spill_analysis():
    analysis = await analyze_oil_spills(latitude=21.626, longitude=87.508)
    assert "status" in analysis
    assert "events" in analysis
    assert "recommendation" in analysis


def test_vessels_moes_buoy_tracking():
    vessels = get_live_vessels(latitude=21.626, longitude=87.508, max_radius_km=300.0)
    assert vessels["totalTargets"] > 0
    assert any(t["buoyStationId"] == "CB02" for t in vessels["targets"])
    assert vessels["dataSource"] != ""
