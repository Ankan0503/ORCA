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

from ..tools import closures, geofence, pfz, satellite_zones
from ..tools.routing import DEFAULT_BOAT_SPEED_KMH
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


# A "zone" at the harbour itself is the grid point under the user, not somewhere to go.
MIN_ZONE_KM = 5.0


def build_zones(
    origin_lat: float,
    origin_lon: float,
    sst_points: list[GridValue],
    chlorophyll: list[GridValue],
) -> list[Zone]:
    """Rank candidate fishing grounds from the two satellite fields."""
    zones: list[Zone] = []

    for point in sst_points:
        # The temperature grid overlaps the coast and the border; a zone must be Indian water.
        if not geofence.is_navigable(point.latitude, point.longitude):
            continue
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
        if away < MIN_ZONE_KM:
            continue
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


@dataclass
class Candidate:
    """One place a boat might go, and whether it may."""

    latitude: float
    longitude: float
    distance_km: float
    label: str
    kept: bool = True
    rejected_because: str | None = None

    @property
    def hours_away(self) -> float:
        return self.distance_km / DEFAULT_BOAT_SPEED_KMH


def filter_candidates(
    candidates: list[Candidate],
    max_distance_km: float | None = None,
) -> list[Candidate]:
    """Apply the constraints that decide whether a zone is usable at all.

    Three separate agents hold the parts of this question — ocean_analytics
    knows where the fish are, geospatial knows where the border and the
    sanctuaries are, and route_planning knows how far a boat gets in an hour —
    and nothing joined them. A fisherman asking "somewhere inside Indian waters,
    outside the closed area, that I can reach in three hours" got three separate
    lists and had to intersect them himself.

    Rejections are **kept, not dropped**. "There is nothing within three hours"
    is a useful answer, and "the nearest ground is closed" is a more useful one
    than silence. A filter that hides its own exclusions turns an empty result
    into an unexplained one.
    """
    for candidate in candidates:
        if max_distance_km is not None and candidate.distance_km > max_distance_km:
            candidate.kept = False
            candidate.rejected_because = (
                f"{candidate.distance_km:.0f} km away, beyond the {max_distance_km:.0f} km asked for"
            )
            continue

        # Sea, inside India's EEZ, and not over land.
        if not geofence.is_navigable(candidate.latitude, candidate.longitude):
            candidate.kept = False
            candidate.rejected_because = "not navigable Indian water"
            continue

        # Inside a sanctuary is a legal bar, not a preference.
        areas = closures.protected_areas_near(candidate.latitude, candidate.longitude)
        inside = [area for area in areas if area.inside]
        if inside:
            candidate.kept = False
            candidate.rejected_because = f"inside {inside[0].name}, where fishing is restricted"
            continue

    return candidates


class OceanAnalyticsAgent(Agent):
    name = "ocean_analytics"
    description = (
        "Sea surface temperature, chlorophyll and potential fishing zones derived from them."
    )
    handles = (
        "fish", "pfz", "fishing zone", "chlorophyll", "temperature", "catch",
        "where", "spot", "plankton", "productiv",
    )
    is_stub = False

    parameters = {
        "type": "object",
        "properties": {
            "latitude": {
                "type": "number",
                "description": "Only if asking about somewhere other than the user's position.",
            },
            "longitude": {
                "type": "number",
                "description": "Only if asking about somewhere other than the user's position.",
            },
            "within_hours": {
                "type": "number",
                "description": (
                    "Only if the user limits how long they will steam — 'somewhere I can "
                    f"reach in three hours'. Converted to distance at {DEFAULT_BOAT_SPEED_KMH:.0f} "
                    "km/h, the same speed route_planning assumes."
                ),
            },
            "max_distance_km": {
                "type": "number",
                "description": "Only if the user names a distance limit directly.",
            },
        },
    }

    def _reach_limit(self, context: QueryContext) -> float | None:
        """How far this trip may go, if the question said so.

        Hours are converted with the router's own speed constant rather than a
        second one invented here — two different assumptions about the same boat
        is how a route and a zone come to disagree about the same trip.
        """
        params = getattr(context, "params", None) or {}
        km = params.get("max_distance_km")
        if km is not None:
            try:
                return float(km)
            except (TypeError, ValueError):
                return None
        hours = params.get("within_hours")
        if hours is not None:
            try:
                return float(hours) * DEFAULT_BOAT_SPEED_KMH
            except (TypeError, ValueError):
                return None
        return None

    async def run(self, context: QueryContext) -> AgentResult:
        latitude = context.latitude if context.latitude is not None else _DEFAULT_LAT
        longitude = context.longitude if context.longitude is not None else _DEFAULT_LON

        # The real government advisory comes first. Only if INCOIS has issued
        # nothing for this coast today — or cannot be reached — does the agent
        # fall back to deriving zones from satellite fields itself.
        incois = await self._incois_result(latitude, longitude, context.language)
        result = incois if incois is not None else await self._derived_result(latitude, longitude)

        # Both paths put their zones in data["zones"], so the constraints apply
        # once, here, rather than twice in two shapes that could drift apart.
        return self._apply_constraints(result, context)

    def _apply_constraints(self, result: AgentResult, context: QueryContext) -> AgentResult:
        """Keep only the zones a boat may actually use, and say what was dropped.

        This is the join the agents never had. The zones come from here, the
        border and the sanctuaries from geospatial's tools, and the reach from
        the router's speed — and a question carrying all three constraints used
        to return three lists for the fisherman to intersect himself.
        """
        zones = (result.data or {}).get("zones") or []
        if not zones or result.error:
            return result

        limit = self._reach_limit(context)
        candidates = filter_candidates(
            [
                Candidate(
                    latitude=float(z["latitude"]),
                    longitude=float(z["longitude"]),
                    distance_km=float(z.get("distanceKm") or 0.0),
                    label=str(z.get("label") or "zone"),
                )
                for z in zones
                if z.get("latitude") is not None and z.get("longitude") is not None
            ],
            max_distance_km=limit,
        )

        kept = [c for c in candidates if c.kept]
        dropped = [c for c in candidates if not c.kept]
        if not dropped and limit is None:
            return result  # nothing was constrained; leave the answer untouched.

        evidence = list(result.evidence)
        if limit is not None:
            evidence.append(
                Evidence(
                    source=f"ORCA reachability at {DEFAULT_BOAT_SPEED_KMH:.0f} km/h",
                    label="Range asked for",
                    value=f"{limit:.0f}",
                    unit="km",
                    note=(
                        f"about {limit / DEFAULT_BOAT_SPEED_KMH:.1f} h each way at the speed "
                        "route planning assumes; a slower boat reaches less"
                    ),
                )
            )
        for candidate in dropped[:4]:
            evidence.append(
                Evidence(
                    source="ORCA constraint check (EEZ, protected areas, range)",
                    label=f"Excluded — {candidate.label}",
                    value=f"{candidate.latitude:.3f}, {candidate.longitude:.3f}",
                    note=candidate.rejected_because,
                )
            )

        # An empty result must explain itself; silence reads as "nothing found"
        # when the truth is "everything found was closed or too far".
        if kept:
            closest = min(kept, key=lambda c: c.distance_km)
            suffix = (
                f" Of {len(candidates)} ground(s) considered, {len(kept)} meet the limits — "
                f"nearest {closest.distance_km:.0f} km, about {closest.hours_away:.1f} h out."
            )
        else:
            # Each rejection carries its own distance, so listing them verbatim
            # repeats the same sentence five times. What a fisherman needs is the
            # shortest gap between what he asked for and what exists.
            closest = min(dropped, key=lambda c: c.distance_km)
            if limit is not None and closest.distance_km > limit:
                suffix = (
                    f" Nothing lies within {limit:.0f} km: the nearest ground is "
                    f"{closest.distance_km:.0f} km out, about {closest.hours_away:.1f} h. "
                    "Going would mean steaming further than you asked."
                )
            else:
                blocked = ", ".join(
                    dict.fromkeys(
                        c.rejected_because for c in dropped if c.rejected_because and "beyond" not in c.rejected_because
                    )
                )
                suffix = (
                    f" None of the {len(candidates)} ground(s) nearby can be used"
                    + (f" — {blocked}." if blocked else ".")
                )

        data = dict(result.data or {})
        data["zones"] = [
            {
                "latitude": c.latitude,
                "longitude": c.longitude,
                "label": c.label,
                "distanceKm": c.distance_km,
                "hoursAway": round(c.hours_away, 1),
            }
            for c in kept
        ]
        data["excludedZones"] = [
            {
                "latitude": c.latitude,
                "longitude": c.longitude,
                "label": c.label,
                "reason": c.rejected_because,
            }
            for c in dropped
        ]

        return AgentResult(
            agent=result.agent,
            summary=result.summary + suffix,
            evidence=evidence,
            confidence=result.confidence,
            is_stub=result.is_stub,
            data=data,
        )

    def _add_satellite_zones(
        self,
        summary: str,
        evidence: list[Evidence],
        latitude: float,
        longitude: float,
        limit: int = 3,
    ) -> tuple[str, list[Evidence]]:
        """Append the nearest Copernicus fronts, if the pipeline has published any.

        Silent when it has not. The pipeline is a daily background job that needs
        credentials and a working CMEMS connection, and an answer must not depend
        on it having run.
        """
        try:
            zones = satellite_zones.nearest_zones(latitude, longitude, limit=limit)
        except Exception:  # noqa: BLE001 - a background product must never break an answer
            return summary, evidence
        if not zones:
            return summary, evidence

        published = satellite_zones.metadata()
        closest = zones[0]
        summary = (
            f"{summary} Satellite fronts also show productive water about "
            f"{closest.distance_km:.0f} km to the {closest.bearing} "
            f"({closest.confidence.lower()} confidence) — an ORCA estimate, not an advisory."
        )

        for zone in zones:
            detail = [f"{zone.distance_km:.0f} km to the {zone.bearing}", zone.confidence.lower()]
            if zone.sst_c is not None:
                detail.append(f"{zone.sst_c:.1f} degC")
            if zone.chlorophyll_mg_m3 is not None:
                detail.append(f"chlorophyll {zone.chlorophyll_mg_m3:.2f} mg/m3")
            if zone.cloud_bypass:
                hours = zone.advection_hours
                detail.append(
                    f"seen through cloud, carried forward {hours:.0f} h" if hours else "seen through cloud"
                )
            evidence.append(
                Evidence(
                    source=satellite_zones.SOURCE,
                    label="Satellite front (estimate)",
                    value=f"{zone.latitude:.3f}, {zone.longitude:.3f}",
                    observed_at=published.get("forecast_date"),
                    note=", ".join(detail),
                )
            )
        return summary, evidence

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

        # The satellite fronts alongside the advisory, not instead of it.
        #
        # INCOIS publishes one bulletin per sector and misses under cloud; the
        # Copernicus pipeline detects fronts across the whole EEZ and carries
        # through cloud by advecting the last clear view. Where the two agree, a
        # fisherman has two independent reasons to go; where they differ, that is
        # worth seeing rather than hiding. Until now these zones were drawn on
        # the map and invisible to anyone who asked in words.
        summary, evidence = self._add_satellite_zones(summary, evidence, latitude, longitude)

        confidence = 0.7 if advisory.stale else 0.9
        return AgentResult(
            agent=self.name,
            summary=summary,
            evidence=evidence,
            confidence=confidence,
            is_stub=False,
            data={
                "zones": [
                    {
                        "latitude": p.latitude,
                        "longitude": p.longitude,
                        "label": f"INCOIS zone off {p.landing_centre}",
                        "distanceKm": round(distance_km(latitude, longitude, p.latitude, p.longitude), 1),
                    }
                    for p in ranked[:5]
                ]
            },
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

        summary, evidence = self._add_satellite_zones(summary, evidence, latitude, longitude)

        # Confidence follows how much of the grid was usable sea.
        coverage = len(sst_points) / len(grid)
        return AgentResult(
            agent=self.name,
            summary=summary,
            evidence=evidence,
            confidence=round(0.5 + 0.45 * coverage, 2),
            is_stub=False,
            data={
                "estimate": True,
                "zones": [
                    {
                        "latitude": z.latitude,
                        "longitude": z.longitude,
                        "label": f"ORCA-estimated zone {z.distance_km} km {z.bearing}",
                        "distanceKm": z.distance_km,
                    }
                    for z in [best, *others]
                ],
            },
        )
