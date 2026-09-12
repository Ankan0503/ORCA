"""Tests for Authoritative Decision Gate in orca-core."""

from app.agents.base import AgentResult, Evidence
from app.tools.decision_gate import (
    DecisionDirective,
    extract_decision_directive,
    format_directive_for_prompt,
    reconcile_and_verify,
)


def test_extract_directive_avoid_from_unsafe_weather():
    results = [
        AgentResult(
            agent="weather_intelligence",
            summary="Next 12 hours: unsafe — wind reaches 42 km/h (exceeds IMD 35 km/h do-not-venture threshold).",
            evidence=[
                Evidence(
                    source="IMD Wind Warning for Fishermen",
                    label="Wind thresholds applied",
                    value="30 km/h caution, 35 km/h do-not-venture",
                )
            ],
            confidence=0.9,
        )
    ]
    directive = extract_decision_directive(results)
    assert directive.verdict == "AVOID"
    assert directive.source == "weather_intelligence"
    assert any("threshold" in c.lower() or "unsafe" in c.lower() for c in directive.constraints)


def test_extract_directive_proceed_from_safe_weather_with_window():
    results = [
        AgentResult(
            agent="weather_intelligence",
            summary="Next 12 hours: safe — wave 1.0 m, wind 15 km/h. Conditions hold until 14:00, then wind rises to 28 km/h.",
            evidence=[
                Evidence(
                    source="Open-Meteo",
                    label="Safe until",
                    value="14:00",
                    note="then wind rises",
                )
            ],
            confidence=0.85,
        )
    ]
    directive = extract_decision_directive(results)
    assert directive.verdict == "PROCEED"
    assert directive.safe_until == "14:00"
    assert any("14:00" in c for c in directive.constraints)


def test_extract_directive_avoid_from_cyclone():
    results = [
        AgentResult(
            agent="cyclone_watch",
            summary="Active Cyclonic Storm 'Dana' over Bay of Bengal; Local Cautionary Signal 3 hoisted at Paradip Port.",
            confidence=0.95,
        )
    ]
    directive = extract_decision_directive(results)
    assert directive.verdict == "AVOID"
    assert directive.source == "cyclone_watch"


def test_extract_directive_from_risk_fusion():
    results = [
        AgentResult(
            agent="risk_assessment",
            summary="Overall trip risk is severe; annual uniform monsoon ban in effect.",
            evidence=[
                Evidence(
                    source="ORCA Decision Fusion Engine",
                    label="Overall operational recommendation",
                    value="AVOID",
                ),
                Evidence(
                    source="Statutory Order",
                    label="Closure warning",
                    value="Annual monsoon fishing ban active until June 14",
                ),
            ],
            confidence=0.92,
        )
    ]
    directive = extract_decision_directive(results)
    assert directive.verdict == "AVOID"
    assert directive.source == "risk_assessment"


def test_extract_directive_caution_from_geospatial():
    results = [
        AgentResult(
            agent="geospatial",
            summary="Operating in caution zone near India-Bangladesh maritime boundary (14 km away).",
            confidence=0.88,
        )
    ]
    directive = extract_decision_directive(results)
    assert directive.verdict == "CAUTION"
    assert directive.source == "geospatial"


def test_format_directive_for_prompt():
    directive = DecisionDirective(
        verdict="AVOID",
        constraints=["Wind reaches 44 km/h", "Safe until 11:00"],
        safe_until="11:00",
    )
    prompt = format_directive_for_prompt(directive)
    assert "AUTHORITATIVE DECISION GATE" in prompt
    assert "OPERATIONAL VERDICT: AVOID" in prompt
    assert "NEVER declare that it is safe" in prompt


def test_reconcile_contradiction_avoid_overrides_safe_claim():
    directive = DecisionDirective(
        verdict="AVOID",
        constraints=["IMD wind warning 45 km/h"],
        rationale="Unsafe conditions",
    )
    hallucinated_safe_answer = "It is safe to go out today and enjoy calm waters."
    reconciled, modified, note = reconcile_and_verify(hallucinated_safe_answer, directive)

    assert modified is True
    assert "UNSAFE" in reconciled
    assert "Do not venture out" in reconciled


def test_reconcile_contradiction_proceed_overrides_danger_claim():
    directive = DecisionDirective(
        verdict="PROCEED",
        constraints=["Conditions hold until 16:00"],
        safe_until="16:00",
        rationale="Calm conditions",
    )
    hallucinated_danger_answer = "Do not go out today because of potential rough seas."
    reconciled, modified, note = reconcile_and_verify(hallucinated_danger_answer, directive)

    assert modified is True
    assert "currently SAFE to go out" in reconciled
    assert "16:00" in reconciled


def test_reconcile_preserves_consistent_answer():
    directive = DecisionDirective(
        verdict="AVOID",
        constraints=["High Wave Alert 2.4 m"],
    )
    consistent_answer = "Do not venture into the sea today. Waves reach 2.4 m exceeding INCOIS alert limits."
    reconciled, modified, note = reconcile_and_verify(consistent_answer, directive)

    assert modified is False
    assert reconciled == consistent_answer


def test_typed_directive_precedence_over_summary():
    """Explicitly typed directive overrides any ambiguous summary phrasing."""
    results = [
        AgentResult(
            agent="risk_assessment",
            summary="Conditions are calm in the morning.",
            directive="AVOID",
            confidence=0.9,
        )
    ]
    directive = extract_decision_directive(results)
    assert directive.verdict == "AVOID"
    assert directive.source == "risk_assessment"


def test_cyclone_directive_outranks_safe_weather():
    """Cyclone watch AVOID directive outranks a safe weather intelligence PROCEED."""
    results = [
        AgentResult(
            agent="weather_intelligence",
            summary="Waves 0.8m, wind 12 km/h: safe.",
            directive="PROCEED",
            confidence=0.9,
        ),
        AgentResult(
            agent="cyclone_watch",
            summary="Deep depression intensifying into cyclonic storm.",
            directive="AVOID",
            confidence=0.95,
        ),
    ]
    directive = extract_decision_directive(results)
    assert directive.verdict == "AVOID"
    assert directive.source == "cyclone_watch"


def test_geospatial_boundary_breach_outranks_safe_weather():
    """Geospatial boundary breach AVOID outranks safe weather PROCEED."""
    results = [
        AgentResult(
            agent="weather_intelligence",
            summary="Waves 0.8m, wind 10 km/h: safe.",
            directive="PROCEED",
            confidence=0.9,
        ),
        AgentResult(
            agent="geospatial",
            summary="Vessel is outside India's EEZ.",
            directive="AVOID",
            confidence=0.95,
        ),
    ]
    directive = extract_decision_directive(results)
    assert directive.verdict == "AVOID"
    assert directive.source == "geospatial"


def test_query_context_shared_observations():
    """QueryContext.with_params propagates shared mutable observations."""
    from app.agents.base import QueryContext

    ctx = QueryContext(question="Is it safe?")
    ctx.shared_observations["sample_obs"] = {"temp": 28.5}

    child_ctx = ctx.with_params({"latitude": 21.5, "longitude": 87.5})
    assert "sample_obs" in child_ctx.shared_observations
    assert child_ctx.shared_observations["sample_obs"]["temp"] == 28.5

    # Modifications in child are reflected in parent
    child_ctx.shared_observations["from_child"] = True
    assert ctx.shared_observations.get("from_child") is True

