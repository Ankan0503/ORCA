"""Ocean Analytics — finds where the fish are likely to be.

The authoritative answer is INCOIS's own Potential Fishing Zone advisory. INCOIS
(under the Ministry of Earth Sciences) issues it daily from satellite sea
surface temperature and chlorophyll, sector by sector along the coast, and this
agent reads it directly (:mod:`app.tools.pfz`). When an advisory exists for the
user's stretch of coast, that is what ORCA reports — a real government fishing
zone, with the landing centre, bearing, depth and distance INCOIS gives.

Only when INCOIS has issued *no* advisory for that sector today — which happens
when cloud cover hides the satellite — does the agent fall back to deriving
zones itself from the same two ingredients:

- Chlorophyll marks plankton, the base of the food chain.
- Thermal fronts — sharp temperature boundaries — concentrate that food.

That derived layer is always labelled as ORCA's own estimate, never as INCOIS,
so the two can never be confused. Either way the agent reports the numbers
behind each zone, because "go here" is worth nothing to a fisherman who cannot
see why.
"""

from dataclasses import dataclass

from ..tools import pfz
from ..tools.ocean import (
    GridValue,
    OceanDataError,
    bearing_compass,
    distance_km,
    fetch_chlorophyll_grid,
    fetch_sst_points,
    nearest,
)
from .base import Agent, AgentResult, Evidence, QueryContext

_DEFAULT_LAT = 21.6272
_DEFAULT_LON = 87.5079

SOURCE_CHL = "NOAA CoastWatch VIIRS gap-filled chlorophyll"
SOURCE_SST = "Open-Meteo Marine sea surface temperature"

# How far out to look, in degrees. Roughly 55 km each way — a day trip for a
# small mechanised boat, not an offshore expedition.
SEARCH_SPAN_DEG = 0.5
GRID_STEPS = 5

# Chlorophyll in mg/m3. Productive water is good; very high readings usually
# mean river silt or an algal bloom rather than good fishing, so the score peaks
# in a band instead of rising forever.
CHL_IDEAL_LOW = 0.5
CHL_IDEAL_HIGH = 3.0
CHL_TOO_HIGH = 8.0

# A front worth crossing an ocean for. Degrees C between neighbouring samples.
FRONT_STRONG_C = 0.5


@dataclass
class Zone:
    latitude: float
    longitude: float
    chlorophyll: float
    sst: float
    front_strength_c: float
    distance_km: float
    bearing: str
    score: float
    reasons: list[str]


def _chlorophyll_score(value: float) -> tuple[float, str]:
    """Score productivity, penalising water that is too turbid to fish well."""
    if value < CHL_IDEAL_LOW:
        return 0.2, f"low plankton ({value:.2f} mg/m3)"
    if value <= CHL_IDEAL_HIGH:
        return 1.0, f"good plankton ({value:.2f} mg/m3)"
    if value <= CHL_TOO_HIGH:
        return 0.6, f"very rich water ({value:.2f} mg/m3)"
    return 0.25, f"water probably too silty or blooming ({value:.2f} mg/m3)"


def _front_score(gradient: float) -> tuple[float, str]:
    if gradient >= FRONT_STRONG_C:
        return 1.0, f"strong temperature front ({gradient:.2f} degC nearby)"
    if gradient >= FRONT_STRONG_C / 2:
        return 0.6, f"weak temperature front ({gradient:.2f} degC nearby)"
    return 0.2, "no clear temperature front"


def build_zones(
    origin_lat: float,
    origin_lon: float,
    sst_points: list[GridValue],
    chlorophyll: list[GridValue],
) -> list[Zone]:
    """Rank candidate fishing grounds from the two satellite fields."""
    zones: list[Zone] = []

    for point in sst_points:
        chl = nearest(chlorophyll, point.latitude, point.longitude)
        if chl is None:
            continue

        # Front strength: the largest temperature step to any nearby sample.
        # A front is a boundary, so what matters is the difference across it.
        neighbours = [
            other
            for other in sst_points
            if other is not point
            and distance_km(point.latitude, point.longitude, other.latitude, other.longitude) < 30
        ]
        gradient = max(
            (abs(point.value - other.value) for other in neighbours), default=0.0
        )

        chl_score, chl_reason = _chlorophyll_score(chl.value)
        front_score, front_reason = _front_score(gradient)

        away = distance_km(origin_lat, origin_lon, point.latitude, point.longitude)
        # Closer is better: fuel costs money and distance costs rescue time.
        distance_penalty = max(0.0, 1.0 - away / 90.0)

        score = 0.45 * chl_score + 0.35 * front_score + 0.20 * distance_penalty

        zones.append(
            Zone(
                latitude=point.latitude,
                longitude=point.longitude,
                chlorophyll=round(chl.value, 3),
                sst=round(point.value, 2),
                front_strength_c=round(gradient, 2),
                distance_km=round(away, 1),
                bearing=bearing_compass(origin_lat, origin_lon, point.latitude, point.longitude),
                score=round(score, 3),
                reasons=[chl_reason, front_reason],
            )
        )

    zones.sort(key=lambda z: z.score, reverse=True)
    return zones


class OceanAnalyticsAgent(Agent):
    name = "ocean_analytics"
    description = (
        "Sea surface temperature, chlorophyll and potential fishing zones derived from them."
    )
    handles = (
        "fish", "pfz", "fishing zone", "chlorophyll", "temperature", "catch",
        "where", "spot", "plankton", "productive",
    )
    is_stub = False

    async def run(self, context: QueryContext) -> AgentResult:
        latitude = context.latitude if context.latitude is not None else _DEFAULT_LAT
        longitude = context.longitude if context.longitude is not None else _DEFAULT_LON

        # The real government advisory comes first. Only if INCOIS has issued
        # nothing for this coast today — or cannot be reached — does the agent
        # fall back to deriving zones from satellite fields itself.
        incois = await self._incois_result(latitude, longitude, context.language)
        if incois is not None:
            return incois

        return await self._derived_result(latitude, longitude)

    async def _incois_result(
        self, latitude: float, longitude: float, language: str
    ) -> AgentResult | None:
        """The authoritative answer: INCOIS's advisory for the nearest sector.

        Returns None when there is no advisory to report (INCOIS issued none for
        this sector today, or was unreachable with nothing cached), so the caller
        can fall back to the derived estimate.
        """
        sector = pfz.sector_for_location(latitude, longitude)
        try:
            advisory = await pfz.get_sector_advisory(sector.secid, language)
        except pfz.PfzDataError:
            return None
        if advisory.empty or not advisory.points:
            return None

        # Rank the government's zones by distance from the fisherman.
        ranked = sorted(
            advisory.points,
            key=lambda p: distance_km(latitude, longitude, p.latitude, p.longitude),
        )
        best = ranked[0]
        best_km = round(distance_km(latitude, longitude, best.latitude, best.longitude), 1)
        best_bearing = bearing_compass(latitude, longitude, best.latitude, best.longitude)

        depth = (
            f", depth {int(best.depth_m_from)}-{int(best.depth_m_to)} m"
            if best.depth_m_from is not None and best.depth_m_to is not None
            else ""
        )
        stale = " (last available advisory — INCOIS not reachable now)" if advisory.stale else ""
        valid = f" valid to {advisory.valid_upto}" if advisory.valid_upto else ""
        summary = (
            f"INCOIS potential fishing zone for {advisory.sector_name}"
            f"{f' ({advisory.forecast_date}{valid})' if advisory.forecast_date else ''}: "
            f"nearest ground about {best_km} km to the {best_bearing} off "
            f"{best.landing_centre}{depth}. {len(ranked)} zones advised today.{stale}"
        )

        source = f"INCOIS Potential Fishing Zone Advisory — {advisory.sector_name} sector"
        evidence: list[Evidence] = []
        for rank, point in enumerate(ranked[:5], start=1):
            label = "Nearest fishing zone" if rank == 1 else f"Fishing zone {rank}"
            km = round(distance_km(latitude, longitude, point.latitude, point.longitude), 1)
            bearing = bearing_compass(latitude, longitude, point.latitude, point.longitude)
            depth_note = (
                f"{int(point.depth_m_from)}-{int(point.depth_m_to)} m depth"
                if point.depth_m_from is not None and point.depth_m_to is not None
                else None
            )
            evidence.append(
                Evidence(
                    source=source,
                    label=f"{label} — off {point.landing_centre}",
                    value=f"{point.latitude:.3f}, {point.longitude:.3f}",
                    observed_at=advisory.forecast_date,
                    note=f"{km} km to the {bearing}"
                    + (f", {depth_note}" if depth_note else ""),
                )
            )

        confidence = 0.7 if advisory.stale else 0.9
        return AgentResult(
            agent=self.name,
            summary=summary,
            evidence=evidence,
            confidence=confidence,
            is_stub=False,
        )

    async def _derived_result(self, latitude: float, longitude: float) -> AgentResult:
        """ORCA's own zone estimate, used only when INCOIS has issued none.

        Clearly labelled as derived, never as an INCOIS advisory.
        """
        lat_min, lat_max = latitude - SEARCH_SPAN_DEG, latitude + SEARCH_SPAN_DEG
        lon_min, lon_max = longitude - SEARCH_SPAN_DEG, longitude + SEARCH_SPAN_DEG

        grid = [
            (
                round(lat_min + (lat_max - lat_min) * i / (GRID_STEPS - 1), 4),
                round(lon_min + (lon_max - lon_min) * j / (GRID_STEPS - 1), 4),
            )
            for i in range(GRID_STEPS)
            for j in range(GRID_STEPS)
        ]

        try:
            sst_points = await fetch_sst_points(grid)
            chlorophyll = await fetch_chlorophyll_grid(lat_min, lat_max, lon_min, lon_max)
        except OceanDataError as exc:
            return AgentResult(agent=self.name, summary="", confidence=0.0, error=str(exc))

        if not sst_points:
            return AgentResult(
                agent=self.name,
                summary="",
                confidence=0.0,
                error="No sea points found near this location — it may be inland.",
            )
        if not chlorophyll:
            return AgentResult(
                agent=self.name,
                summary="",
                confidence=0.0,
                error="No chlorophyll data was available for this area.",
            )

        zones = build_zones(latitude, longitude, sst_points, chlorophyll)
        if not zones:
            return AgentResult(
                agent=self.name,
                summary="",
                confidence=0.0,
                error="Could not match temperature and chlorophyll data for this area.",
            )

        best = zones[0]
        others = zones[1:3]

        summary = (
            "No INCOIS advisory was issued for this coast today, so this is ORCA's "
            "own estimate from satellite chlorophyll and temperature — not a "
            "government advisory. "
            f"Best estimated ground is about {best.distance_km} km to the {best.bearing}: "
            f"{', '.join(best.reasons)}, water {best.sst} degC."
        )
        if others:
            summary += " Alternatives: " + "; ".join(
                f"{z.distance_km} km {z.bearing} ({z.chlorophyll} mg/m3)" for z in others
            )

        observed = (
            f"{chlorophyll[0].observed_at:%Y-%m-%d}"
            if chlorophyll and chlorophyll[0].observed_at
            else None
        )

        evidence: list[Evidence] = []
        for rank, zone in enumerate([best, *others], start=1):
            label = "Best fishing zone" if rank == 1 else f"Alternative zone {rank - 1}"
            evidence.extend(
                [
                    Evidence(
                        source=SOURCE_CHL,
                        label=f"{label} — position",
                        value=f"{zone.latitude:.3f}, {zone.longitude:.3f}",
                        note=f"{zone.distance_km} km to the {zone.bearing}",
                    ),
                    Evidence(
                        source=SOURCE_CHL,
                        label=f"{label} — chlorophyll",
                        value=str(zone.chlorophyll),
                        unit="mg/m3",
                        observed_at=observed,
                    ),
                    Evidence(
                        source=SOURCE_SST,
                        label=f"{label} — sea temperature",
                        value=str(zone.sst),
                        unit="degC",
                    ),
                    Evidence(
                        source=SOURCE_SST,
                        label=f"{label} — thermal front strength",
                        value=str(zone.front_strength_c),
                        unit="degC across 30 km",
                        note="fish gather where water masses meet",
                    ),
                ]
            )

        evidence.append(
            Evidence(
                source=f"{SOURCE_CHL}; {SOURCE_SST}",
                label="Area searched",
                value=f"{GRID_STEPS}x{GRID_STEPS} grid, +/-{SEARCH_SPAN_DEG} degrees",
                note=f"{len(sst_points)} sea points, {len(chlorophyll)} chlorophyll samples",
            )
        )

        # Confidence follows how much of the grid was usable sea.
        coverage = len(sst_points) / len(grid)
        return AgentResult(
            agent=self.name,
            summary=summary,
            evidence=evidence,
            confidence=round(0.5 + 0.45 * coverage, 2),
            is_stub=False,
        )
