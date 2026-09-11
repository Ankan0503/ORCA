"""Operational Decision Fusion Engine.

Synthesizes environmental risk, authoritative geofencing (boundaries & MPAs),
statutory fishing closures, and Potential Fishing Zone (PFZ) suitability into
a single operational recommendation: PROCEED, CAUTION, or AVOID.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class DecisionFusionResult:
    decision: str  # PROCEED | CAUTION | AVOID | UNAVAILABLE
    confidence: str  # HIGH | MEDIUM | LOW | UNAVAILABLE
    score: int  # 0 - 100 operational safety-yield index
    rationale: str
    factors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    selected_zone: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def fuse_marine_decision(
    risk: dict[str, Any] | None,
    geofence: dict[str, Any] | None = None,
    pfz: dict[str, Any] | None = None,
    closures: dict[str, Any] | None = None,
) -> DecisionFusionResult:
    """Fuses risk, borders, closures and fishing zones into an actionable decision."""
    warnings: list[str] = []
    factors: list[str] = []

    if not risk:
        return DecisionFusionResult(
            decision="UNAVAILABLE",
            confidence="LOW",
            score=0,
            rationale="Marine observations are unavailable; voyage assessment cannot be verified.",
            warnings=["No live sea-state telemetry available."],
        )

    risk_level = (risk.get("risk_level") or risk.get("level") or "LOW").upper()
    risk_score = float(risk.get("risk_score") or risk.get("score") or 0.0)
    risk_confidence = float(risk.get("confidence_score") or risk.get("confidence") or 80.0)

    # Base operational score derived from environmental safety (100 is safest)
    score = max(0, 100 - int(risk_score))
    factors.append(f"Marine environmental risk: {risk_level} ({risk_score:.0f}/100).")

    # 1. Statutory Closures (Monsoon Fishing Ban & Wildlife Sanctuaries)
    monsoon_closed = False
    if closures:
        if closures.get("active") or closures.get("is_closed"):
            monsoon_closed = True
            reason = closures.get("reason") or "Statutory annual monsoon uniform fishing ban is in effect."
            warnings.append(f"Statutory closure: {reason}")
            factors.append(f"Closed water advisory: {reason}")

    # 2. Authoritative Geofence (IMBL, Treaty Lines, MPAs)
    restricted = False
    caution_geo = False
    if geofence:
        geo_status = str(geofence.get("status") or "").upper()
        in_restricted = geofence.get("in_restricted_waters") or geofence.get("inRestrictedWaters")
        dist_km = geofence.get("distance_to_boundary_km") or geofence.get("distance_km")

        if in_restricted or "BREACH" in geo_status or geo_status == "CRITICAL":
            restricted = True
            factors.append("Authoritative geofence indicates restricted or foreign sovereign waters.")
            warnings.append(
                "Do not navigate in restricted waters or across international boundaries; authoritative limits take precedence."
            )
        elif geo_status in ("CAUTION", "WARNING") or (dist_km is not None and float(dist_km) < 20.0):
            caution_geo = True
            factors.append(f"Vessel operates in caution zone near boundary ({dist_km:.1f} km away).")
            warnings.append("Approach with extreme vigilance; maintain continuous radar and radio watch.")

    # 3. Decision Rules - Safety and Border Limits Strictly Override Potential
    if monsoon_closed:
        score = 0
        decision = "AVOID"
        rationale = f"Voyage is prohibited due to the statutory annual monsoon uniform fishing ban: {closures.get('reason', '')}"
    elif restricted:
        score = 0
        decision = "AVOID"
        rationale = "Voyage is prohibited due to proximity or entry into restricted sovereign/protected waters."
    elif risk_level in ("EXTREME", "SEVERE"):
        score = min(score, 10)
        decision = "AVOID"
        warnings.append("Severe sea-state hazards override any fishing potential.")
        rationale = "Extreme sea-state conditions (severe waves/gales) render navigation hazardous."
    elif risk_level == "HIGH":
        score = min(score, 35)
        decision = "CAUTION"
        warnings.append("High wave energy or squally conditions require experienced crew and heavy craft.")
        rationale = "High sea-state risk limits operations; small craft must remain in harbor or sheltered waters."
    elif caution_geo:
        score = min(score, 55)
        decision = "CAUTION"
        rationale = "Operating conditions are fair, but boundary caution zones require strict course adherence."
    elif risk_level == "MODERATE":
        score = min(score, 65)
        decision = "CAUTION"
        factors.append("Moderate sea state requires continuous weather monitoring.")
        rationale = "Moderate sea state permits daytime fishing for seaworthy mechanised craft."
    else:
        # Environmental risk is LOW and boundaries are clear
        decision = "PROCEED"
        factors.append("Clear boundary limits and calm sea conditions confirmed.")
        rationale = "Conditions are favorable for coastal navigation and fishing operations."

    # 4. Integrate PFZ Suitability
    selected_zone = None
    if pfz:
        pfz_status = pfz.get("status") or "READY"
        best_zone = pfz.get("best_zone") or pfz.get("bestZone")
        if isinstance(best_zone, dict):
            selected_zone = best_zone.get("name") or best_zone.get("sector")
            zone_suitability = best_zone.get("suitability", "MODERATE")
            factors.append(f"PFZ harvest zone identified: {selected_zone} (Suitability: {zone_suitability}).")
        elif isinstance(best_zone, str):
            selected_zone = best_zone
            factors.append(f"PFZ harvest zone identified: {selected_zone}.")

        if pfz_status == "UNAVAILABLE":
            factors.append("No active INCOIS PFZ advisory published for today.")

    # 5. Confidence Calculation
    if risk_confidence >= 85 and not restricted and not monsoon_closed:
        confidence = "HIGH"
    elif risk_confidence >= 65:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    return DecisionFusionResult(
        decision=decision,
        confidence=confidence,
        score=score,
        rationale=rationale,
        factors=factors,
        warnings=warnings,
        selected_zone=selected_zone,
    )
