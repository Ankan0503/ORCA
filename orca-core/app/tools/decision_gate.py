"""Authoritative Decision Gate.

Reconciles deterministic domain logic (IMD/INCOIS statutory bulletins, physical
marine thresholds, geofence restrictions) with agent synthesis, resolving the
divergence between the computed operational directive and conversational LLM answers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from ..agents.base import AgentResult


@dataclass
class DecisionDirective:
    verdict: str  # "PROCEED" | "CAUTION" | "AVOID" | "INFORMATIVE"
    constraints: list[str] = field(default_factory=list)
    rationale: str = ""
    source: str = ""
    safe_until: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "constraints": list(self.constraints),
            "rationale": self.rationale,
            "source": self.source,
            "safe_until": self.safe_until,
        }


def extract_decision_directive(results: list[AgentResult]) -> DecisionDirective:
    """Inspects agent results and derives the authoritative operational safety directive."""
    if not results:
        return DecisionDirective(verdict="INFORMATIVE", rationale="No specialist results available.")

    results_by_agent = {r.agent: r for r in results if not r.error}

    # 1. Statutory cyclones / severe disturbances outrank all other considerations
    cyclone_res = results_by_agent.get("cyclone_watch")
    if cyclone_res:
        if cyclone_res.directive == "AVOID":
            return DecisionDirective(
                verdict="AVOID",
                constraints=[cyclone_res.summary],
                rationale="Active cyclonic disturbance or statutory port warning in effect.",
                source="cyclone_watch",
            )
        elif cyclone_res.directive == "CAUTION":
            return DecisionDirective(
                verdict="CAUTION",
                constraints=[cyclone_res.summary],
                rationale="Elevated cyclogenesis or storm formation probability over 7-day outlook.",
                source="cyclone_watch",
            )
        summary_upper = cyclone_res.summary.upper()
        if any(term in summary_upper for term in ("CYCLONE", "DEPRESSION", "SIGNAL 3", "SIGNAL 4", "DANGER", "WARNING")):
            if "NO CYCLONIC" not in summary_upper and "NO ACTIVE" not in summary_upper:
                return DecisionDirective(
                    verdict="AVOID",
                    constraints=[cyclone_res.summary],
                    rationale="Active cyclonic disturbance or statutory port warning in effect.",
                    source="cyclone_watch",
                )

    # 2. Statutory maritime boundary / EEZ / MPA breaches outrank general operations
    geo_res = results_by_agent.get("geospatial")
    if geo_res and geo_res.directive == "AVOID":
        return DecisionDirective(
            verdict="AVOID",
            constraints=[geo_res.summary],
            rationale="Vessel position is within restricted waters or maritime boundary breach zone.",
            source="geospatial",
        )

    # 3. Check risk_assessment — deterministic fusion of weather, geofence, PFZ, closures
    risk_res = results_by_agent.get("risk_assessment")
    if risk_res:
        constraints: list[str] = []
        safe_until: str | None = None

        for ev in risk_res.evidence:
            if ev.label in ("Safe until", "Safe window"):
                safe_until = ev.value
                constraints.append(f"Safe until {ev.value}")
            elif any(k in ev.label.lower() for k in ("warning", "hazard", "alert", "border", "geofence")):
                constraints.append(f"{ev.label}: {ev.value}")

        if risk_res.directive in ("AVOID", "CAUTION", "PROCEED"):
            return DecisionDirective(
                verdict=risk_res.directive,
                constraints=constraints,
                rationale=risk_res.summary,
                source="risk_assessment",
                safe_until=safe_until,
            )

        # Fallback to evidence or summary text
        summary_upper = risk_res.summary.upper()
        verdict = "INFORMATIVE"
        for ev in risk_res.evidence:
            if ev.label == "Overall operational recommendation":
                verdict = ev.value.upper()

        if verdict not in ("PROCEED", "CAUTION", "AVOID"):
            if "AVOID" in summary_upper or "DO NOT VENTURE" in summary_upper or "UNSAFE" in summary_upper:
                verdict = "AVOID"
            elif "CAUTION" in summary_upper or "MODERATE" in summary_upper or "HIGH" in summary_upper:
                verdict = "CAUTION"
            elif "PROCEED" in summary_upper or "SAFE" in summary_upper:
                verdict = "PROCEED"

        if verdict in ("PROCEED", "CAUTION", "AVOID"):
            return DecisionDirective(
                verdict=verdict,
                constraints=constraints,
                rationale=risk_res.summary,
                source="risk_assessment",
                safe_until=safe_until,
            )

    # 4. Check weather_intelligence
    weather_res = results_by_agent.get("weather_intelligence")
    if weather_res:
        constraints = []
        safe_until = None
        for ev in weather_res.evidence:
            if ev.label == "Safe until":
                safe_until = ev.value
                constraints.append(f"Conditions safe until {ev.value} ({ev.note or ''})".strip())
            elif "threshold" in ev.label.lower() or "alert" in ev.label.lower():
                constraints.append(f"{ev.label}: {ev.value}")

        if weather_res.directive in ("AVOID", "CAUTION", "PROCEED"):
            rationale_map = {
                "AVOID": "Marine weather exceeds statutory safety thresholds (IMD/INCOIS).",
                "CAUTION": "Marine weather is approaching cautionary limits.",
                "PROCEED": "Conditions are within safe operational limits.",
            }
            return DecisionDirective(
                verdict=weather_res.directive,
                constraints=constraints or [weather_res.summary],
                rationale=rationale_map[weather_res.directive],
                source="weather_intelligence",
                safe_until=safe_until,
            )

        summary_lower = weather_res.summary.lower()
        if ": unsafe" in summary_lower or "do not venture" in summary_lower:
            return DecisionDirective(
                verdict="AVOID",
                constraints=constraints or [weather_res.summary],
                rationale="Marine weather exceeds statutory safety thresholds (IMD/INCOIS).",
                source="weather_intelligence",
                safe_until=safe_until,
            )
        elif ": caution" in summary_lower:
            return DecisionDirective(
                verdict="CAUTION",
                constraints=constraints or [weather_res.summary],
                rationale="Marine weather is approaching cautionary limits.",
                source="weather_intelligence",
                safe_until=safe_until,
            )
        elif ": safe" in summary_lower:
            return DecisionDirective(
                verdict="PROCEED",
                constraints=constraints,
                rationale="Conditions are within safe operational limits.",
                source="weather_intelligence",
                safe_until=safe_until,
            )

    # 5. Check geospatial fallback
    if geo_res:
        if geo_res.directive in ("AVOID", "CAUTION"):
            return DecisionDirective(
                verdict=geo_res.directive,
                constraints=[geo_res.summary],
                rationale="Vessel position is within restricted waters or maritime boundary caution zone.",
                source="geospatial",
            )
        summary_lower = geo_res.summary.lower()
        if "restricted" in summary_lower or "breach" in summary_lower or "sanctuary" in summary_lower:
            return DecisionDirective(
                verdict="AVOID",
                constraints=[geo_res.summary],
                rationale="Vessel position is within restricted waters or marine protected sanctuary.",
                source="geospatial",
            )
        elif "caution" in summary_lower or "near boundary" in summary_lower:
            return DecisionDirective(
                verdict="CAUTION",
                constraints=[geo_res.summary],
                rationale="Vessel is operating in proximity to maritime boundary or protected area.",
                source="geospatial",
            )

    return DecisionDirective(
        verdict="INFORMATIVE",
        constraints=[],
        rationale="Informational query without a direct marine voyage safety verdict.",
        source="general",
    )


def format_directive_for_prompt(directive: DecisionDirective) -> str:
    """Formats the decision gate directive as an imperative system prompt rule."""
    if directive.verdict == "INFORMATIVE":
        return ""

    lines = [
        "AUTHORITATIVE DECISION GATE (NON-NEGOTIABLE):",
        f"- OPERATIONAL VERDICT: {directive.verdict}",
    ]
    if directive.safe_until:
        lines.append(f"- SAFE TIME WINDOW: Conditions hold until {directive.safe_until}.")
    if directive.constraints:
        lines.append("- KEY CONSTRAINTS:")
        for c in directive.constraints[:3]:
            lines.append(f"  * {c}")

    lines.append(
        "- ENFORCEMENT RULES:\n"
        f"  1. Your answer MUST be completely consistent with the '{directive.verdict}' verdict.\n"
    )

    if directive.verdict == "AVOID":
        lines.append(
            "  2. You MUST clearly advise against going out or state that conditions/waters are unsafe or prohibited.\n"
            "  3. NEVER declare that it is safe or good to go."
        )
    elif directive.verdict == "CAUTION":
        lines.append(
            "  2. You MUST advise heightened caution, vigilance, or vessel suitability restrictions.\n"
            "  3. Do NOT issue an unqualified green light or declare conditions completely safe."
        )
    elif directive.verdict == "PROCEED":
        lines.append(
            "  2. State clearly that conditions are safe to venture out for the specified window.\n"
            "  3. Do NOT declare that it is unsafe or tell mariners not to go, but DO state when the safe window ends if applicable."
        )

    return "\n".join(lines)


# Contradiction detection patterns
_SAFE_AFFIRMATIONS = re.compile(
    r"\b(it is safe|conditions are safe|safe to venture|safe to go out|good to go|clear to sail|no danger|completely safe)\b",
    re.IGNORECASE,
)
_DANGER_ASSERTIONS = re.compile(
    r"\b(do not go|unsafe to go|stay ashore|do not venture|not safe|extremely dangerous|prohibited to go|avoid going)\b",
    re.IGNORECASE,
)


def reconcile_and_verify(answer: str, directive: DecisionDirective) -> tuple[str, bool, str]:
    """Validates the generated answer against the directive, fixing direct contradictions."""
    if directive.verdict == "INFORMATIVE" or not answer:
        return answer, False, "Informational query; no safety reconciliation needed."

    clean_ans = answer.strip()

    if directive.verdict == "AVOID":
        # Check if the LLM declared conditions safe despite AVOID
        if _SAFE_AFFIRMATIONS.search(clean_ans) and not _DANGER_ASSERTIONS.search(clean_ans):
            prefix = "Advisory: Conditions are UNSAFE. Do not venture out. "
            if directive.constraints:
                prefix = f"Advisory: Conditions are UNSAFE ({directive.constraints[0]}). Do not venture out. "
            reconciled = f"{prefix}{clean_ans}"
            return reconciled, True, f"Reconciled contradiction: model affirmed safety despite {directive.verdict} verdict."

    elif directive.verdict == "PROCEED":
        # Check if the LLM declared it is unsafe to go despite PROCEED
        if _DANGER_ASSERTIONS.search(clean_ans) and not _SAFE_AFFIRMATIONS.search(clean_ans):
            window_text = f" (safe until {directive.safe_until})" if directive.safe_until else ""
            prefix = f"Advisory: Conditions are currently SAFE to go out{window_text}. "
            reconciled = f"{prefix}{clean_ans}"
            return reconciled, True, f"Reconciled contradiction: model warned unsafe despite {directive.verdict} verdict."

    return clean_ans, False, f"Answer aligns with {directive.verdict} directive."
