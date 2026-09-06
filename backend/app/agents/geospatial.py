"""Geospatial — where the boat is, relative to India's maritime limits.

This agent answers the question a forecast cannot: *am I allowed to be here, and
how close is the line?* Crossing into Sri Lankan or Pakistani waters is one of
the commonest ways Indian fishermen are arrested, and it usually happens by
drift or by following a shoal rather than by intent.

Everything it reports comes from Marine Regions v12 boundary data held locally
(:mod:`app.tools.geofence`) — the same authority behind the EEZ drawn on the
map. Because the data is on disk, this agent still works with no connectivity,
which matters most at sea.

The proximity thresholds are ORCA's own caution margins, not a legal standard,
and the agent says so in its evidence rather than implying an official ruling.
"""

from ..tools.geofence import (
    CRITICAL_KM,
    SOURCE,
    WARNING_KM,
    GeofenceDataError,
    locate,
)
from .base import Agent, AgentResult, Evidence, QueryContext

# Digha harbour, used when the caller sends no position.
_DEFAULT_LAT = 21.6272
_DEFAULT_LON = 87.5079

# How much confidence to report. The geometry is exact; what is uncertain is
# only whether the caller's position is accurate, so this stays high.
_CONFIDENCE = 0.92


class GeospatialAgent(Agent):
    name = "geospatial"
    description = (
        "India's EEZ and international maritime boundaries: whether a position is inside "
        "Indian waters and how far the nearest foreign boundary is."
    )
    handles = (
        "boundary", "border", "eez", "restricted", "protected", "geofence", "allowed",
        "limit", "sri lanka", "pakistan", "bangladesh", "myanmar", "arrest", "cross",
        "international", "waters",
    )
    is_stub = False

    async def run(self, context: QueryContext) -> AgentResult:
        latitude = context.latitude if context.latitude is not None else _DEFAULT_LAT
        longitude = context.longitude if context.longitude is not None else _DEFAULT_LON

        try:
            result = locate(latitude, longitude)
        except GeofenceDataError as exc:
            return AgentResult(agent=self.name, summary="", confidence=0.0, error=str(exc))

        evidence: list[Evidence] = [
            Evidence(
                source=SOURCE,
                label="Inside India's EEZ",
                value="yes" if result.inside_eez else "no",
                note=result.zone or None,
            )
        ]

        nearest = result.nearest_boundary
        if nearest is not None:
            evidence.extend(
                [
                    Evidence(
                        source=SOURCE,
                        label=f"Distance to {nearest.neighbour} maritime boundary",
                        value=f"{nearest.distance_km:.1f}",
                        unit="km",
                        note=f"to the {nearest.bearing} ({nearest.line_type.lower()} line)",
                    ),
                    Evidence(
                        source=SOURCE,
                        label="Nearest point on that boundary",
                        value=f"{nearest.latitude:.3f}, {nearest.longitude:.3f}",
                        note=nearest.line_name,
                    ),
                ]
            )

        evidence.append(
            Evidence(
                source="ORCA caution margins",
                label="Warning distances used",
                value=f"{CRITICAL_KM:.0f} km critical, {WARNING_KM:.0f} km warning",
                note="ORCA's own margins for early warning, not a legal limit",
            )
        )

        return AgentResult(
            agent=self.name,
            summary=result.message,
            evidence=evidence,
            confidence=_CONFIDENCE,
            is_stub=False,
        )
