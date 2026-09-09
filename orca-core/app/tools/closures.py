"""When and where fishing is closed — the rules, not the weather.

ORCA could tell a fisherman the sea was calm and the fish were biting on a day
it was illegal for him to sail. Two kinds of closure decide that, and neither is
a measurement:

**The annual monsoon ban.** India closes fishing for 61 days every year so
stocks can spawn. It is the single restriction that touches every mechanised
boat in the country, and the penalty for ignoring it is real. Quoting the
Department of Fisheries through PIB (Ministry of Fisheries, Animal Husbandry &
Dairying, 25 March 2025):

    "The uniform ban on fishing for 61 days is implemented annually by the
    Department of Fisheries, Government of India in the Exclusive Economic Zone
    (EEZ) of India beyond territorial waters on both the coasts for 61 days
    (i.e., 15th April to 14th June in the East Coast, and 1st June to 31st July
    in the West Coast)... The traditional non-motorized units are exempted from
    this uniform fishing ban... Similarly, the coastal States/UTs are also
    implementing the fishing ban within their territorial waters in line with
    the uniform ban implemented in the EEZ."

Two consequences ORCA must not blur. The central order covers the EEZ beyond
territorial waters, while the states mirror it inshore — so in practice the
closure applies at sea either way, but the authority differs and the exact state
notification is what binds a boat close to the coast. And traditional
non-motorized craft are exempt, so the answer depends on the boat as well as the
date; ORCA reports the ban and names the exemption rather than deciding for
someone whether it applies to them.

**Marine protected areas.** Sanctuaries and national parks where fishing is
restricted or forbidden outright. These come from the notifying ministry itself
— MoEFCC's protected-area layer as published on the PM GatiShakti National
Master Plan — via ``scripts/build_mpa_from_gatishakti.py``.

An earlier version of this layer was built from a Protected Planet (WDPA)
download that turned out to be the *International*-designations subset: thirteen
Ramsar and World Heritage sites, with Gahirmatha — the olive ridley arribada,
1,435 km², and the closure most likely to put a trawler in front of the Coast
Guard — absent entirely. The layer still reports how many areas it holds,
because a geofence that silently knows a fraction of the sanctuaries is worse
than one that admits what it does not know.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path

from .geofence import _point_in_polygon, _haversine_km

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "geo"
MPA_PATH = DATA_DIR / "india_mpa.geojson"

BAN_SOURCE = (
    "Department of Fisheries, Government of India — uniform 61-day fishing ban "
    "(via PIB, Ministry of Fisheries, Animal Husbandry & Dairying, 25 Mar 2025)"
)
MPA_SOURCE = (
    "Ministry of Environment, Forest and Climate Change — wildlife sanctuaries "
    "and national parks, via PM GatiShakti National Master Plan"
)

BAN_EXEMPTION = "Traditional non-motorized craft are exempt from this ban."
# Alias used where the note is appended to evidence text.
BAN_EXEMPTION_NOTE = BAN_EXEMPTION

# Longitude that separates the two coasts for the purposes of the ban order.
# India's southern tip sits near 77E; everything east of about 80E fishes the
# Bay of Bengal and follows the east-coast dates. The Andaman & Nicobar Islands
# fall east of this line and Lakshadweep west, which matches how the ban order
# groups them.
EAST_COAST_LONGITUDE = 80.0


@dataclass(frozen=True)
class BanPeriod:
    coast: str
    start: tuple[int, int]  # (month, day)
    end: tuple[int, int]

    def window(self, year: int) -> tuple[date, date]:
        return date(year, *self.start), date(year, *self.end)


# Neither window crosses a year boundary, so plain date comparison is safe.
BAN_PERIODS = (
    BanPeriod("East Coast", (4, 15), (6, 14)),
    BanPeriod("West Coast", (6, 1), (7, 31)),
)


@dataclass
class BanStatus:
    """Whether the annual ban is on, and how that relates to today."""

    coast: str
    active: bool
    start: date
    end: date
    days_remaining: int | None  # while active
    days_until: int | None  # while upcoming
    message: str

    def to_dict(self) -> dict:
        return {
            "coast": self.coast,
            "active": self.active,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "daysRemaining": self.days_remaining,
            "daysUntil": self.days_until,
            "message": self.message,
            "exemption": BAN_EXEMPTION,
            "source": BAN_SOURCE,
        }


@dataclass
class ProtectedArea:
    name: str
    designation: str
    iucn_category: str | None
    marine_area_km2: float | None
    distance_km: float = 0.0
    inside: bool = False

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "designation": self.designation,
            "iucnCategory": self.iucn_category,
            "marineAreaKm2": self.marine_area_km2,
            "distanceKm": round(self.distance_km, 1),
            "inside": self.inside,
            "source": MPA_SOURCE,
        }


def coast_for(longitude: float) -> str:
    return "East Coast" if longitude >= EAST_COAST_LONGITUDE else "West Coast"


def ban_status(longitude: float, on: date | None = None) -> BanStatus:
    """Whether the annual fishing ban applies on a given day at a given coast.

    Reports the upcoming window as well as the current one: a boat planning a
    trip a fortnight out needs to know the ban starts before it returns, not
    only that today happens to be legal.
    """
    today = on or date.today()
    coast = coast_for(longitude)
    period = next(p for p in BAN_PERIODS if p.coast == coast)

    start, end = period.window(today.year)
    if today > end:
        # This year's window has passed; the next one is in the new year.
        start, end = period.window(today.year + 1)

    if start <= today <= end:
        remaining = (end - today).days
        return BanStatus(
            coast=coast,
            active=True,
            start=start,
            end=end,
            days_remaining=remaining,
            days_until=None,
            message=(
                f"The annual {coast.lower()} fishing ban is in force until "
                f"{end:%d %B %Y} — {remaining} day(s) left. {BAN_EXEMPTION}"
            ),
        )

    until = (start - today).days
    return BanStatus(
        coast=coast,
        active=False,
        start=start,
        end=end,
        days_remaining=None,
        days_until=until,
        message=(
            f"No fishing ban today. The annual {coast.lower()} ban runs "
            f"{start:%d %B} to {end:%d %B %Y}, starting in {until} day(s)."
        ),
    )


@lru_cache(maxsize=1)
def _load_mpas() -> list[tuple[dict, list]]:
    """Marine protected areas, with each polygon and a bounding box."""
    if not MPA_PATH.exists():
        return []

    with MPA_PATH.open(encoding="utf-8") as handle:
        data = json.load(handle)

    loaded: list[tuple[dict, list]] = []
    for feature in data.get("features", []):
        geometry = feature.get("geometry") or {}
        polygons = (
            [geometry.get("coordinates")]
            if geometry.get("type") == "Polygon"
            else geometry.get("coordinates") or []
        )
        for polygon in polygons:
            if polygon:
                loaded.append((feature.get("properties") or {}, polygon))
    return loaded


def protected_area_count() -> int:
    """How many marine areas the layer actually holds.

    Surfaced so a thin download is visible rather than mistaken for an empty sea.
    """
    return len(_load_mpas())


def _ring_min_distance_km(latitude: float, longitude: float, ring: list) -> float:
    """Roughly how far a point is from a polygon's edge."""
    best = float("inf")
    # Long coastal rings have thousands of vertices; sampling keeps this cheap
    # while staying accurate enough for a "you are near a sanctuary" warning.
    step = max(1, len(ring) // 400)
    for index in range(0, len(ring), step):
        lon, lat = ring[index][0], ring[index][1]
        best = min(best, _haversine_km(latitude, longitude, lat, lon))
    return best


def protected_areas_near(
    latitude: float, longitude: float, within_km: float = 25.0
) -> list[ProtectedArea]:
    """Protected areas containing this position, or close to it.

    Containment is reported first and always, however large the area. Proximity
    matters too — drifting into a sanctuary is as much of an offence as
    anchoring in one — so anything within `within_km` is returned as well.
    """
    found: list[ProtectedArea] = []

    for properties, polygon in _load_mpas():
        outer = polygon[0]
        lats = [p[1] for p in outer]
        lons = [p[0] for p in outer]
        margin = within_km / 100.0  # generous degrees, cheap rejection
        if not (
            min(lats) - margin <= latitude <= max(lats) + margin
            and min(lons) - margin <= longitude <= max(lons) + margin
        ):
            continue

        inside = _point_in_polygon(latitude, longitude, polygon)
        distance = 0.0 if inside else _ring_min_distance_km(latitude, longitude, outer)
        if not inside and distance > within_km:
            continue

        found.append(
            ProtectedArea(
                name=str(properties.get("name") or "Unnamed protected area"),
                designation=str(properties.get("designation") or "Protected area"),
                iucn_category=properties.get("iucnCategory") or None,
                marine_area_km2=properties.get("marineAreaKm2"),
                distance_km=distance,
                inside=inside,
            )
        )

    # Inside first, then nearest.
    found.sort(key=lambda a: (not a.inside, a.distance_km))
    return found
