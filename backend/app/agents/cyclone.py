"""Cyclone Watch — the days-ahead warning a forecast cannot give.

The weather agent can see a thunderstorm in the next few hours. A cyclone is a
different kind of threat: it is declared by an authority, it is named, and the
useful warning arrives days before there is anything to measure at the coast.
This agent reports what RSMC Tropical Cyclones, New Delhi has actually said.

Its most valuable output is not "is there a cyclone" — most days there is not —
but IMD's own **probability of cyclogenesis over the next seven days** for the
basin the user fishes in. A fisherman who learns on Monday that formation
probability rises to MODERATE by Thursday can plan a trip around it. That is
the difference between a weather app and a disaster-management tool.

ORCA never declares a cyclone itself. Deriving one from wind fields would be
borrowing an authority it does not have; every statement here traces to a
published RSMC bulletin, and the bulletin's own issue time is reported so a
stale outlook is visible rather than assumed current.
"""

from ..tools.cyclone import (
    FORECAST_STEPS,
    PROBABILITY_SCALE,
    CycloneDataError,
    fetch_outlook,
)
from .base import Agent, AgentResult, Evidence, QueryContext

# Digha, used when the caller sends no position — the basin still resolves.
_DEFAULT_LAT = 21.6272
_DEFAULT_LON = 87.5079

SOURCE = "IMD / RSMC Tropical Cyclones, New Delhi — Tropical Weather Outlook"

# How a formation probability maps to how loudly ORCA should say it.
_URGENCY = {"NIL": 0, "LOW": 1, "MODERATE": 2, "HIGH": 3}


class CycloneWatchAgent(Agent):
    name = "cyclone_watch"
    description = (
        "Cyclones and depressions in the Bay of Bengal and Arabian Sea, from IMD/RSMC's "
        "official outlook: what systems exist now and the chance of a new one forming "
        "over the next 7 days. Use for cyclone, storm-formation or 'is a cyclone coming' "
        "questions, and for planning trips several days ahead."
    )
    handles = (
        "cyclone", "storm", "depression", "low pressure", "hurricane", "typhoon",
        "imd", "rsmc", "warning", "alert", "coming", "forming", "next week",
    )
    is_stub = False

    async def run(self, context: QueryContext) -> AgentResult:
        latitude = context.latitude if context.latitude is not None else _DEFAULT_LAT
        longitude = context.longitude if context.longitude is not None else _DEFAULT_LON

        try:
            outlook = await fetch_outlook()
        except CycloneDataError as exc:
            # Never answer "no cyclone" because the check failed. An unreachable
            # bulletin is not an all-clear, and for a cyclone it is the one
            # substitution that could cost lives.
            return AgentResult(agent=self.name, summary="", confidence=0.0, error=str(exc))

        basin = outlook.basin_for(longitude)
        evidence: list[Evidence] = [
            Evidence(
                source=SOURCE,
                label="Outlook issued",
                value=outlook.issued_text or "unknown",
                note="RSMC issues this once daily for the whole North Indian Ocean",
            )
        ]

        parts: list[str] = []

        # --- What exists right now ---------------------------------------
        active = outlook.active_cyclone
        if active is not None:
            parts.append(
                f"IMD reports a {active.kind} in the {active.basin}: {active.sentence}"
            )
            evidence.append(
                Evidence(
                    source=SOURCE,
                    label="Active system",
                    value=active.kind,
                    note=active.sentence,
                )
            )
        elif outlook.systems:
            # Below cyclone strength, but worth naming — these are what cyclones
            # grow from, and a fisherman should know one is sitting there.
            weaker = outlook.systems[0]
            parts.append(
                f"No cyclone. IMD notes a {weaker.kind} in the {weaker.basin}, "
                "which is below cyclone strength."
            )
            evidence.append(
                Evidence(
                    source=SOURCE,
                    label="System present (below cyclone strength)",
                    value=weaker.kind,
                    note=weaker.sentence,
                )
            )
        else:
            parts.append("IMD reports no cyclone in the Bay of Bengal or the Arabian Sea.")

        # --- Will one form? ------------------------------------------------
        if basin is not None and basin.cyclogenesis:
            peak = basin.peak_probability
            first = basin.first_risk_step
            if _URGENCY.get(peak, 0) == 0:
                parts.append(
                    f"For the {basin.basin}, IMD puts the chance of a new system forming "
                    "at nil for the next 7 days."
                )
            else:
                parts.append(
                    f"For the {basin.basin}, IMD puts the chance of a new system forming "
                    f"at {peak.lower()} ({PROBABILITY_SCALE.get(peak, '')}), "
                    f"first from {first}."
                )

            for step, value in zip(FORECAST_STEPS, basin.cyclogenesis):
                evidence.append(
                    Evidence(
                        source=SOURCE,
                        label=f"Cyclone formation chance — {step} ({basin.basin})",
                        value=value,
                        note=PROBABILITY_SCALE.get(value, ""),
                    )
                )

        if outlook.no_cyclone_declared:
            evidence.append(
                Evidence(
                    source=SOURCE,
                    label="IMD national cyclone bulletin",
                    value="No Cyclone",
                    note="IMD is publishing its explicit no-cyclone bulletin today",
                )
            )

        # Confidence reflects whether the basin's own table was readable, not how
        # calm the sea is — a quiet outlook that parsed cleanly is a confident
        # answer, and a missing table is not.
        confidence = 0.92 if (basin and len(basin.cyclogenesis) == 7) else 0.55

        return AgentResult(
            agent=self.name,
            summary=" ".join(parts),
            evidence=evidence,
            confidence=confidence,
            is_stub=False,
            data={
                "issued": outlook.issued_text,
                "basin": basin.basin if basin else None,
                "peakProbability": basin.peak_probability if basin else None,
                "firstRiskWindow": basin.first_risk_step if basin else None,
                "activeCyclone": active.to_dict() if active else None,
                "systems": [s.to_dict() for s in outlook.systems],
                "sourceUrl": outlook.source_url,
            },
        )
