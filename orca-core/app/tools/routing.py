"""Getting there: a sea route that goes around the weather and allows for current.

A straight line from a harbour to a fishing ground is the wrong answer twice
over. It can cross land, and it ignores both the thunderstorm sitting in the
middle of it and the current that will push the boat sideways for the whole
trip. This module plans the actual passage.

Three ideas do the work:

**The grid is the sea.** Cells come from :mod:`app.tools.seagrid`, which already
knows which cells are water (the marine model declines to answer over land) and
what the rain, lightning and current are in each. Using one grid for hazards and
for navigation means the route is planned around exactly what the map draws.
The resolution is the grid step — around 8-12 km — so this plans an open-sea
passage, not pilotage through a narrow channel, and it should not be sold as the
latter.

**Cost is time, not distance.** Searching for the shortest path would ignore the
current entirely. Searching for the *quickest* path makes the current fall out
of the arithmetic naturally: a leg with the current behind is cheap, a leg
punching into it is expensive, and the route bends accordingly.

**The current triangle** (``steer_for_current``) is the piece of classical
navigation that turns "the ground bears 148°" into "steer 156° and you will make
good 148° at 13 km/h". A boat that steers straight at its destination in a
cross-current arrives somewhere else; every fisherman knows this by feel, and
this makes it explicit.

Boat speed is an assumption about the vessel, never a measurement, and every
number derived from it is reported as such.
"""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field

from . import geofence
from .ocean import bearing_compass, distance_km
from .seagrid import SeaCell, SeaGridError, fetch_sea_grid

# A typical small mechanised fishing boat, matching the figure the risk agent
# already uses so the two never disagree.
DEFAULT_BOAT_SPEED_KMH = 15.0

# Cells a route will not enter at all. Lightning has no safe crossing speed.
BLOCKED_HAZARDS = {"thunderstorm"}

# Time penalties, as multipliers on a leg's duration. Heavy rain is not fatal but
# it is miserable and blinding, so the router will go a reasonable way around it.
# These are ORCA's own weightings and are reported as such.
HAZARD_TIME_PENALTY = {
    "heavy_rain": 2.5,
    "moderate_rain": 1.4,
    "fog": 2.0,
    "light_rain": 1.05,
    "clear": 1.0,
}

# Below this speed-over-ground a leg is treated as impossible: the current is
# beating the boat.
MIN_PROGRESS_KMH = 1.0

# Spacing of the land checks along a leg; a spit narrower than this can slip through.
WATER_CHECK_KM = 2.0


class RoutingError(RuntimeError):
    """Raised when no usable route can be produced."""


@dataclass
class Leg:
    """One grid-step of the passage."""

    from_lat: float
    from_lon: float
    to_lat: float
    to_lon: float
    distance_km: float
    course_deg: float
    heading_deg: float
    speed_over_ground_kmh: float
    hours: float
    hazard: str
    current_speed_ms: float | None
    current_towards_deg: float | None

    def to_dict(self) -> dict:
        return {
            "from": {"latitude": round(self.from_lat, 4), "longitude": round(self.from_lon, 4)},
            "to": {"latitude": round(self.to_lat, 4), "longitude": round(self.to_lon, 4)},
            "distanceKm": round(self.distance_km, 1),
            "courseDeg": round(self.course_deg),
            "headingDeg": round(self.heading_deg),
            "headingCompass": bearing_compass(
                self.from_lat, self.from_lon, self.to_lat, self.to_lon
            ),
            "speedOverGroundKmh": round(self.speed_over_ground_kmh, 1),
            "hours": round(self.hours, 2),
            "hazard": self.hazard,
            "currentSpeedMs": self.current_speed_ms,
            "currentTowardsDeg": self.current_towards_deg,
        }


@dataclass
class Route:
    legs: list[Leg] = field(default_factory=list)
    total_distance_km: float = 0.0
    total_hours: float = 0.0
    boat_speed_kmh: float = DEFAULT_BOAT_SPEED_KMH
    avoided: list[str] = field(default_factory=list)
    detour_km: float = 0.0
    direct_km: float = 0.0

    @property
    def waypoints(self) -> list[tuple[float, float]]:
        if not self.legs:
            return []
        points = [(self.legs[0].from_lat, self.legs[0].from_lon)]
        points.extend((leg.to_lat, leg.to_lon) for leg in self.legs)
        return points

    def to_dict(self) -> dict:
        return {
            "waypoints": [{"latitude": round(a, 4), "longitude": round(b, 4)} for a, b in self.waypoints],
            "legs": [leg.to_dict() for leg in self.legs],
            "totalDistanceKm": round(self.total_distance_km, 1),
            "totalHours": round(self.total_hours, 2),
            "directDistanceKm": round(self.direct_km, 1),
            "detourKm": round(self.detour_km, 1),
            "boatSpeedKmh": self.boat_speed_kmh,
            "avoided": self.avoided,
            "assumption": (
                f"Times assume a boat making {self.boat_speed_kmh:.0f} km/h through the water. "
                "A slower boat takes longer and has less margin."
            ),
        }


# --- The current triangle ----------------------------------------------------


def steer_for_current(
    course_deg: float,
    boat_speed_kmh: float,
    current_towards_deg: float | None,
    current_speed_kmh: float | None,
) -> tuple[float, float]:
    """Heading to steer, and the speed actually made good over the ground.

    Given the course you want to make good and the current setting across it,
    this returns the heading that cancels the sideways push, and the resulting
    speed over the ground — faster with the current behind, slower against it.

    Bearings are degrees clockwise from north; the current bearing is where the
    water is *going*, which is how Open-Meteo reports it. Returns a speed of
    zero when the current is too strong to hold the course at all, which is a
    real outcome and must not be rounded away into a plausible-looking number.
    """
    # Tested against `is None`, not truthiness: a current setting due north is
    # 0 degrees, which is falsy, and treating that as "no current" would have
    # silently ignored the East India Coastal Current — which sets almost due
    # north off this coast for most of the year.
    if current_towards_deg is None or current_speed_kmh is None or current_speed_kmh <= 0:
        return course_deg % 360, boat_speed_kmh

    course = math.radians(course_deg)
    setting = math.radians(current_towards_deg)

    # Current split into the part along the course and the part across it.
    along = current_speed_kmh * math.cos(setting - course)
    cross = current_speed_kmh * math.sin(setting - course)

    if abs(cross) >= boat_speed_kmh:
        # The sideways set exceeds what the boat can crab into: the course
        # cannot be held.
        return course_deg % 360, 0.0

    drift = math.asin(-cross / boat_speed_kmh)
    heading = (math.degrees(course + drift)) % 360
    speed_over_ground = boat_speed_kmh * math.cos(drift) + along
    return heading, max(0.0, speed_over_ground)


def initial_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle bearing in degrees from north."""
    dlon = math.radians(lon2 - lon1)
    y = math.sin(dlon) * math.cos(math.radians(lat2))
    x = math.cos(math.radians(lat1)) * math.sin(math.radians(lat2)) - math.sin(
        math.radians(lat1)
    ) * math.cos(math.radians(lat2)) * math.cos(dlon)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


# --- Grid plumbing -----------------------------------------------------------


def _bbox_grid(
    origin: tuple[float, float],
    destination: tuple[float, float],
    side: int,
    pad_deg: float,
) -> list[tuple[float, float]]:
    """A grid covering both ends of the passage, with room to detour around it."""
    lat_min = min(origin[0], destination[0]) - pad_deg
    lat_max = max(origin[0], destination[0]) + pad_deg
    lon_min = min(origin[1], destination[1]) - pad_deg
    lon_max = max(origin[1], destination[1]) + pad_deg
    return [
        (
            round(lat_min + (lat_max - lat_min) * i / (side - 1), 4),
            round(lon_min + (lon_max - lon_min) * j / (side - 1), 4),
        )
        for i in range(side)
        for j in range(side)
    ]


def _index_of(cells: list[SeaCell], side: int) -> dict[tuple[int, int], SeaCell]:
    return {(i // side, i % side): cell for i, cell in enumerate(cells)}


def _leg_between(
    a: SeaCell, b: SeaCell, boat_speed_kmh: float
) -> Leg | None:
    """Build one leg, allowing for the current in the cell being entered."""
    km = distance_km(a.latitude, a.longitude, b.latitude, b.longitude)
    if km <= 0:
        return None

    course = initial_bearing(a.latitude, a.longitude, b.latitude, b.longitude)
    current_kmh = (
        b.current_speed_trusted_ms * 3.6 if b.current_speed_trusted_ms is not None else None
    )
    heading, sog = steer_for_current(course, boat_speed_kmh, b.current_direction_deg, current_kmh)
    if sog < MIN_PROGRESS_KMH:
        return None

    hours = km / sog
    return Leg(
        from_lat=a.latitude,
        from_lon=a.longitude,
        to_lat=b.latitude,
        to_lon=b.longitude,
        distance_km=km,
        course_deg=course,
        heading_deg=heading,
        speed_over_ground_kmh=sog,
        hours=hours,
        hazard=b.hazard,
        current_speed_ms=b.current_speed_trusted_ms,
        current_towards_deg=b.current_direction_deg,
    )


def _leg_in_water(a: SeaCell, b: SeaCell) -> bool:
    """Whether the straight run between two water cells stays off land and inside Indian waters."""
    km = distance_km(a.latitude, a.longitude, b.latitude, b.longitude)
    steps = max(2, math.ceil(km / WATER_CHECK_KM))
    return all(
        geofence.is_navigable(
            a.latitude + (b.latitude - a.latitude) * k / steps,
            a.longitude + (b.longitude - a.longitude) * k / steps,
        )
        for k in range(1, steps)
    )


async def plan_route(
    origin: tuple[float, float],
    destination: tuple[float, float],
    boat_speed_kmh: float = DEFAULT_BOAT_SPEED_KMH,
    side: int = 11,
    pad_deg: float = 0.35,
) -> Route:
    """Quickest safe passage from origin to destination.

    A* over the sea grid, minimising *time* rather than distance so the current
    is accounted for, refusing to enter cells with lightning in them, and paying
    a time penalty to skirt heavy rain and fog.
    """
    grid_points = _bbox_grid(origin, destination, side, pad_deg)
    try:
        cells = await fetch_sea_grid(grid_points)
    except SeaGridError as exc:
        raise RoutingError(str(exc)) from exc

    lookup = _index_of(cells, side)
    # The forecast model's cells spill over the coast; the EEZ polygon is the real shoreline.
    sea = {
        rc: c
        for rc, c in lookup.items()
        if c.is_sea and c.hazard not in BLOCKED_HAZARDS and geofence.is_navigable(c.latitude, c.longitude)
    }
    if not sea:
        raise RoutingError("No navigable water was found between these points.")

    def nearest_node(lat: float, lon: float) -> tuple[int, int]:
        return min(sea, key=lambda rc: distance_km(lat, lon, sea[rc].latitude, sea[rc].longitude))

    start = nearest_node(*origin)
    goal = nearest_node(*destination)
    goal_cell = sea[goal]

    def heuristic(rc: tuple[int, int]) -> float:
        cell = sea[rc]
        km = distance_km(cell.latitude, cell.longitude, goal_cell.latitude, goal_cell.longitude)
        # Optimistic: assume the best possible push from the current.
        return km / (boat_speed_kmh + 3.0)

    open_set: list[tuple[float, tuple[int, int]]] = [(heuristic(start), start)]
    came_from: dict[tuple[int, int], tuple[int, int]] = {}
    best: dict[tuple[int, int], float] = {start: 0.0}
    hazards_met: set[str] = set()
    steered_off_land = False

    while open_set:
        _, current = heapq.heappop(open_set)
        if current == goal:
            break

        row, col = current
        for drow in (-1, 0, 1):
            for dcol in (-1, 0, 1):
                if drow == 0 and dcol == 0:
                    continue
                neighbour = (row + drow, col + dcol)
                if neighbour not in sea:
                    continue

                leg = _leg_between(sea[current], sea[neighbour], boat_speed_kmh)
                if leg is None:
                    continue
                if not _leg_in_water(sea[current], sea[neighbour]):
                    steered_off_land = True
                    continue

                penalty = HAZARD_TIME_PENALTY.get(leg.hazard, 1.0)
                cost = best[current] + leg.hours * penalty
                if cost < best.get(neighbour, float("inf")):
                    best[neighbour] = cost
                    came_from[neighbour] = current
                    heapq.heappush(open_set, (cost + heuristic(neighbour), neighbour))

    if goal not in came_from and goal != start:
        raise RoutingError(
            "No route avoiding the weather could be found — the way through may be "
            "blocked by thunderstorms, land or the maritime border."
        )

    # Walk the path back and rebuild it as real legs.
    path = [goal]
    while path[-1] != start:
        path.append(came_from[path[-1]])
    path.reverse()

    legs: list[Leg] = []
    for a, b in zip(path, path[1:]):
        leg = _leg_between(sea[a], sea[b], boat_speed_kmh)
        if leg is not None:
            legs.append(leg)
            if leg.hazard not in ("clear",):
                hazards_met.add(leg.hazard)

    direct = distance_km(origin[0], origin[1], destination[0], destination[1])
    total_km = sum(leg.distance_km for leg in legs)

    # What the route steered around: blocked cells that lay near the direct line.
    avoided = sorted(
        {
            cell.hazard
            for cell in cells
            if cell.is_sea and cell.hazard in BLOCKED_HAZARDS
        }
        | ({"land"} if steered_off_land else set())
    )

    return Route(
        legs=legs,
        total_distance_km=total_km,
        total_hours=sum(leg.hours for leg in legs),
        boat_speed_kmh=boat_speed_kmh,
        avoided=avoided,
        detour_km=max(0.0, total_km - direct),
        direct_km=direct,
    )
