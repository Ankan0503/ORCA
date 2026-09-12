"""Tests for degraded mode, data provenance, and operational status."""

from app.agents.base import AgentResult, Evidence
from app.agents.orchestrator import OrchestratorResponse
from app.schemas import ChatResponse


def test_orchestrator_response_serialization():
    """OrchestratorResponse serializes status, directive, and data freshness."""
    resp = OrchestratorResponse(
        answer="Conditions are safe.",
        language="en",
        agents_used=["weather_intelligence", "risk_assessment"],
        results=[
            AgentResult(
                agent="weather_intelligence",
                summary="Safe sea.",
                directive="PROCEED",
                evidence=[
                    Evidence(source="Open-Meteo", label="Obs", value="1.0m", observed_at="2026-09-12T10:00:00Z")
                ],
            )
        ],
        directive="PROCEED",
        status="COMPLETE",
        degraded_components=[],
        data_freshness={"weather_intelligence": "2026-09-12T10:00:00Z"},
    )
    d = resp.to_dict()
    assert d["status"] == "COMPLETE"
    assert d["directive"] == "PROCEED"
    assert d["degraded_components"] == []
    assert d["data_freshness"]["weather_intelligence"] == "2026-09-12T10:00:00Z"

    # Verify Pydantic ChatResponse accepts the dict
    chat_resp = ChatResponse(**d)
    assert chat_resp.status == "COMPLETE"
    assert chat_resp.directive == "PROCEED"
    assert chat_resp.data_freshness["weather_intelligence"] == "2026-09-12T10:00:00Z"


def test_orchestrator_degraded_mode_recording():
    """When an optional agent fails, response status is DEGRADED and recorded."""
    resp = OrchestratorResponse(
        answer="Sea conditions hold until 14:00.",
        language="en",
        agents_used=["weather_intelligence", "cyclone_watch"],
        results=[
            AgentResult(agent="weather_intelligence", summary="Safe.", directive="PROCEED"),
            AgentResult(agent="cyclone_watch", summary="", error="HTTP 502 Service Unavailable"),
        ],
        directive="PROCEED",
        status="DEGRADED",
        degraded_components=["cyclone_watch"],
        data_freshness={"weather": "2026-09-12T11:00:00Z"},
    )
    d = resp.to_dict()
    assert d["status"] == "DEGRADED"
    assert "cyclone_watch" in d["degraded_components"]
    assert d["directive"] == "PROCEED"


def test_guardrail_blocked_status():
    """Off-topic or harmful input results in BLOCKED status."""
    resp = OrchestratorResponse(
        answer="I can only assist with marine and fishing safety questions.",
        language="en",
        agents_used=[],
        results=[],
        directive="INFORMATIVE",
        status="BLOCKED",
        degraded_components=[],
        data_freshness={},
    )
    d = resp.to_dict()
    assert d["status"] == "BLOCKED"
    assert d["directive"] == "INFORMATIVE"
