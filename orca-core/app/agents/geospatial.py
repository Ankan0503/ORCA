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

from ..tools import oil_spill as oil_spill_tool
from ..tools import vessels as vessels_tool
from ..tools.closures import (
    BAN_EXEMPTION_NOTE,
    BAN_SOURCE,
    MPA_SOURCE,
    ban_status,
    protected_area_count,
    protected_areas_near,
)
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
        "boundary", "border", "eez", "restrict", "protected", "geofenc", "allowed",
        "limit", "sri lanka", "pakistan", "bangladesh", "myanmar", "arrest", "cross",
        "international", "waters", "avoid", "route", "navigat", "pfz", "fishing zone",
        "fishing area",
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

        # --- Rules, not weather: closures and protected areas -------------
        # A calm sea and a good catch are irrelevant if it is illegal to sail
        # today, or if the ground sits inside a sanctuary.
        summary_parts = [result.message]

        ban = ban_status(longitude)
        if ban.active:
            summary_parts.append(ban.message)
        evidence.append(
            Evidence(
                source=BAN_SOURCE,
                label=f"Annual fishing ban ({ban.coast})",
                value="in force" if ban.active else "not in force",
                note=ban.message + " " + BAN_EXEMPTION_NOTE,
            )
        )

        areas = protected_areas_near(latitude, longitude)
        inside = [a for a in areas if a.inside]
        if inside:
            names = ", ".join(a.name for a in inside[:2])
            summary_parts.append(
                f"This position is inside a protected area ({names}) — fishing there "
                "is restricted."
            )
        elif areas:
            nearest = areas[0]
            summary_parts.append(
                f"The {nearest.name} protected area is {nearest.distance_km:.0f} km away."
            )

        for area in areas[:3]:
            evidence.append(
                Evidence(
                    source=MPA_SOURCE,
                    label=("Inside protected area" if area.inside else "Nearby protected area"),
                    value=area.name,
                    unit=None if area.inside else "km",
                    note=(
                        f"{area.designation}"
                        + ("" if area.inside else f", {area.distance_km:.0f} km away")
                    ),
                )
            )

        # Coverage is stated rather than implied: this layer is only as complete
        # as the MoEFCC dataset behind it, and a geofence that knows about a
        # fraction of the sanctuaries must not read as an all-clear.
        evidence.append(
            Evidence(
                source=MPA_SOURCE,
                label="Protected areas in ORCA's layer",
                value=str(protected_area_count()),
                note=(
                    "marine areas loaded; India has roughly 130 marine protected areas, "
                    "so absence of a warning here is not proof there is no sanctuary"
                ),
            )
        )

        # Who and what else is in this water.
        #
        # Both were built, both serve their own endpoints, and neither could be
        # reached by anyone asking in words. "Is there anyone near me?" matters
        # after a breakdown, and a spill is a hazard the geofence cannot see.
        evidence.extend(await self._others_in_the_area(latitude, longitude))

        if inside or result.level in ("critical", "outside"):
            directive = "AVOID"
        elif result.level in ("warning", "watch") or ban.active:
            directive = "CAUTION"
        else:
            directive = "INFORMATIVE"

        return AgentResult(
            agent=self.name,
            summary=" ".join(summary_parts),
            evidence=evidence,
            confidence=_CONFIDENCE,
            is_stub=False,
            directive=directive,
            data={
                "fishingBan": ban.to_dict(),
                "protectedAreas": [a.to_dict() for a in areas[:5]],
                "protectedAreaLayerCount": protected_area_count(),
            },
        )


    async def _others_in_the_area(self, latitude: float, longitude: float) -> list[Evidence]:
        """Nearby vessels and any reported spill. Never fatal if either is down."""
        rows: list[Evidence] = []

        try:
            vessels = vessels_tool.get_live_vessels(latitude, longitude)
        except Exception:  # noqa: BLE001
            vessels = None
        if vessels and vessels.get("totalTargets"):
            nearest = min(
                vessels.get("targets", []),
                key=lambda t: t.get("distanceKm", 9e9),
                default=None,
            )
            rows.append(
                Evidence(
                    source=vessels.get("dataSource") or "MoES buoy network",
                    label="Tracked targets near you",
                    value=str(vessels["totalTargets"]),
                    note=(
                        f"nearest {nearest.get('buoyStationId', 'unknown')} at "
                        f"{nearest.get('distanceKm')} km"
                        if nearest
                        else None
                    ),
                )
            )

        try:
            spills = await oil_spill_tool.analyze_oil_spills(latitude, longitude)
        except Exception:  # noqa: BLE001
            spills = None
        if spills and spills.get("events"):
            rows.append(
                Evidence(
                    source="NASA EONET",
                    label="Reported water-quality or storm events nearby",
                    value=str(len(spills["events"])),
                    note=spills.get("recommendation"),
                )
            )
        return rows
