"""Fetch marine protected-area polygons from OpenStreetMap and merge them in.

India's Marine Protected Areas are *national* designations (Wildlife Sanctuary,
National Park). A Protected Planet download filtered to international
designations contains none of them, which is how ORCA ended up knowing about six
Ramsar wetlands and no sanctuaries at all.

OpenStreetMap carries some of them as protected-area relations, so this fills
part of the gap from a free, no-key source. It is a supplement, not a
replacement: OSM has no polygon for Gahirmatha, Chilika, Malvan, Point Calimere,
Pulicat, Sajnakhali or Lothian Island, all of which are real sanctuaries. An
unfiltered Protected Planet download remains the way to get the full set.

Merging is by name: an area already present from Protected Planet is not added
again, and every feature records which source it came from so the two can be
told apart afterwards.

    python scripts/fetch_osm_mpa.py
"""

from __future__ import annotations

import json
import pathlib
import sys

import httpx

OVERPASS_MIRRORS = (
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter",
)
USER_AGENT = "ORCA-Marine/0.1 (SIH 26176 marine advisory prototype)"
OSM_SOURCE = "OpenStreetMap contributors (ODbL)"

OUT = pathlib.Path(__file__).resolve().parent.parent / "data" / "geo" / "india_mpa.geojson"

# Relations confirmed present in OSM, found by querying every protected area in
# a coastal-India bounding box and matching against the official MPA list.
# The state and designation come from that official list rather than from OSM's
# free-text tags, so the attributes stay authoritative even where OSM's naming
# differs.
RELATIONS = {
    14697187: ("Coringa", "Andhra Pradesh", "Wildlife Sanctuary", "IV"),
    20066333: ("Krishna", "Andhra Pradesh", "Wildlife Sanctuary", "IV"),
    8334753: ("Marine (Gulf of Kachchh)", "Gujarat", "National Park", "II"),
    8815438: ("Bhitarkanika", "Odisha", "National Park", "II"),
    415570: ("Gulf of Mannar Marine", "Tamil Nadu", "National Park", "II"),
    14937802: ("Sundarbans", "West Bengal", "National Park", "II"),
    19896831: ("Haliday Island", "West Bengal", "Wildlife Sanctuary", "IV"),
}


def fetch(relation_ids: list[int]) -> list[dict]:
    ids = ",".join(str(i) for i in relation_ids)
    query = f"[out:json][timeout:180];relation(id:{ids});out geom;"
    for mirror in OVERPASS_MIRRORS:
        try:
            response = httpx.post(
                mirror,
                data={"data": query},
                headers={"User-Agent": USER_AGENT},
                timeout=240,
            )
        except Exception as exc:  # noqa: BLE001 - try the next mirror
            print(f"  {mirror.split('/')[2]}: {type(exc).__name__}", file=sys.stderr)
            continue
        if response.status_code == 200:
            return response.json().get("elements", [])
        print(f"  {mirror.split('/')[2]}: HTTP {response.status_code}", file=sys.stderr)
    raise SystemExit("Overpass unavailable on every mirror")


def stitch_rings(ways: list[list[tuple[float, float]]]) -> list[list[list[float]]]:
    """Join way fragments end-to-end into closed rings.

    A relation's outer boundary is stored as a set of ways that need not be in
    order or in a consistent direction, so they are walked and reversed as
    needed until each ring closes.
    """
    remaining = [list(w) for w in ways if len(w) >= 2]
    rings: list[list[list[float]]] = []

    while remaining:
        ring = remaining.pop(0)
        extended = True
        while extended and ring[0] != ring[-1]:
            extended = False
            for index, candidate in enumerate(remaining):
                if candidate[0] == ring[-1]:
                    ring.extend(candidate[1:])
                elif candidate[-1] == ring[-1]:
                    ring.extend(list(reversed(candidate))[1:])
                elif candidate[-1] == ring[0]:
                    ring = candidate[:-1] + ring
                elif candidate[0] == ring[0]:
                    ring = list(reversed(candidate))[:-1] + ring
                else:
                    continue
                remaining.pop(index)
                extended = True
                break

        if len(ring) >= 4:
            if ring[0] != ring[-1]:
                ring.append(ring[0])  # force closure
            rings.append([[lon, lat] for lat, lon in ring])
    return rings


def build_feature(element: dict) -> dict | None:
    name, state, designation, iucn = RELATIONS[element["id"]]

    outer: list[list[tuple[float, float]]] = []
    for member in element.get("members", []):
        if member.get("type") != "way" or member.get("role") not in ("outer", ""):
            continue
        geometry = member.get("geometry") or []
        if geometry:
            outer.append([(p["lat"], p["lon"]) for p in geometry])

    rings = stitch_rings(outer)
    if not rings:
        return None

    return {
        "type": "Feature",
        "geometry": {"type": "MultiPolygon", "coordinates": [[r] for r in rings]},
        "properties": {
            "name": f"{name} ({state})",
            "designation": designation,
            "designationType": "National",
            "iucnCategory": iucn,
            "marineAreaKm2": None,
            "status": "Designated",
            "source": OSM_SOURCE,
            "osmRelation": element["id"],
        },
    }


def main() -> None:
    existing = {"type": "FeatureCollection", "features": []}
    if OUT.exists():
        existing = json.loads(OUT.read_text(encoding="utf-8"))

    have = {
        str((f.get("properties") or {}).get("name", "")).lower()
        for f in existing.get("features", [])
    }

    print(f"fetching {len(RELATIONS)} OSM relations...")
    elements = fetch(list(RELATIONS))
    print(f"  got {len(elements)} element(s)")

    added = 0
    for element in elements:
        if element.get("id") not in RELATIONS:
            continue
        feature = build_feature(element)
        if feature is None:
            print(f"  ! no usable rings for relation {element['id']}", file=sys.stderr)
            continue
        if feature["properties"]["name"].lower() in have:
            continue
        existing.setdefault("features", []).append(feature)
        added += 1
        rings = len(feature["geometry"]["coordinates"])
        print(f"  + {feature['properties']['name']}  ({rings} ring(s))")

    existing["orca_source"] = (
        "Protected Planet (WDPA/WDOECM), UNEP-WCMC; OpenStreetMap contributors (ODbL)"
    )
    OUT.write_text(json.dumps(existing), encoding="utf-8")
    print(f"\nadded {added}; layer now holds {len(existing['features'])} areas -> {OUT}")


if __name__ == "__main__":
    main()
