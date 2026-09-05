"""Ocean Analytics — finds where the fish are likely to be.

Nobody publishes Potential Fishing Zones as an API. INCOIS derives them from
satellite sea surface temperature and chlorophyll, and so does this agent:

- Chlorophyll marks plankton, which is the base of the food chain. Water with
  nothing growing in it holds nothing worth catching.
- Thermal fronts — sharp temperature boundaries between water masses —
  concentrate that food and the fish feeding on it. A front is where the
  gradient is steep, not where the water is warm.

So a zone scores well when productive water sits beside a temperature boundary,
close enough to reach. The agent reports the numbers behind each zone, because
"go here" is worth nothing to a fisherman who cannot see why.
"""

from dataclasses import dataclass

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
            f"Best fishing ground is about {best.distance_km} km to the {best.bearing}: "
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
