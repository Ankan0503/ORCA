"""Build ORCA's marine protected-area layer from India's own PA dataset.

Input: ``GatiShakti_Wildlife_Sanctuaries_and_National_Parks.geojson`` — the
Ministry of Environment, Forest and Climate Change's national protected-area
layer as published on the PM GatiShakti National Master Plan. 665 features, all
of India's wildlife sanctuaries and national parks, ~48 MB.

This replaces the previous layer, which was built from the WDPA download and
turned out to be the *International*-designations subset (Ramsar sites and World
Heritage sites only, 13 features), supplemented by seven hand-stitched
OpenStreetMap relations. Those were real but neither complete nor statutory.
The GatiShakti layer is the notifying ministry's own geometry, which is the
right provenance for a boundary that carries a criminal penalty.

**Why the selection is a written list rather than a geometric test.** The
obvious approach — keep every PA whose polygon reaches India's EEZ — was tried
and measured: it selected 109 of the 665 in 224 seconds, and it was wrong in
both directions. It pulled in Papikonda National Park, 1,000 km² of inland
Eastern Ghats, and the Wild Ass Sanctuary in the salt desert of the Little Rann;
and it *missed* Mahatma Gandhi Marine National Park, whose geometry is a
GeometryCollection whose sampled vertices happen to sit on island land. A
fisherman warned about the wrong area loses trust in every later warning, and
one not warned about Gahirmatha can lose his boat. So the list is explicit, it
names each area, and it can be audited line by line against the notification.

Every Andaman & Nicobar and Lakshadweep protected area is included wholesale:
they are all islands, every one of them has a shoreline, and all are legally
restricted to approach.

Run:
    python backend/scripts/build_mpa_from_gatishakti.py "<path to the geojson>"
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

OUTPUT = Path(__file__).resolve().parent.parent / "data" / "geo" / "india_mpa.geojson"

#: States whose every protected area is an island, and therefore coastal.
ISLAND_STATES = {"Andaman & Nicobar", "Lakshadweep (UT)"}

#: Mainland marine and coastal protected areas, by exact name as published.
#: Each of these either extends into the sea, sits on the shore, or governs an
#: estuary or lagoon a boat can enter.
MAINLAND_MARINE = {
    # Gulf of Kachchh — India's first marine national park.
    "Marine National Park",
    "Marine Sanctuary",
    # Maharashtra coast.
    "Malvan Marine WLS",
    "Thane Creek Flemingo Sanctuary",
    # Goa estuary.
    "Dr.Salim Ali Bird-Chorao Wildlife Sanctuary",
    # Kerala backwater mangrove.
    "Mangalavanam Bird Sanctuary",
    # Tamil Nadu — Gulf of Mannar's island chain, Palk Bay, Pulicat.
    "Gulf of Mannar Marine National Park",
    "Point Calimere Wildlife Sanctuary A-Block",
    "Point Calimere Wildlife Sanctuary B-Block",
    "Pulicat Lake Bird Wildlife Santuary",
    # Andhra Pradesh — Godavari and Krishna mangroves, Pulicat's north shore.
    "Coringa Wildlife Sanctuary",
    "Krishna Wildlife Sanctuary",
    "Pulicat Bird Sanctuary",
    # Odisha — Gahirmatha is the olive ridley arribada and the one most likely
    # to put a trawler in front of the Coast Guard.
    "Gahiramatha Marine Sanctuary",
    "Bhitarkanika National Park",
    "Bhitarkanika Wildlife Sanctuary",
    "Chilika-Nalaban Wildlife Sanctuary",
    "Balukhanda Konark Wildlife Sanctuary",
    # West Bengal — the Sundarbans complex.
    "Sunderban National Park",
    "Sunderban Wildlife Sanctuary",
    "Sajnakhali Wildlife Sanctuary",
    "Lothian Island Wildlife Sanctuary",
    "Haliday Island Wildlife Sanctuary",
}

SOURCE = (
    "Ministry of Environment, Forest and Climate Change — wildlife sanctuaries "
    "and national parks, via PM GatiShakti National Master Plan"
)


def _polygons(geometry: dict) -> list:
    """Every polygon in a geometry, whatever shape it arrived in.

    Seven features are GeometryCollections pairing a polygon with a stray
    LineString — Mahatma Gandhi Marine National Park among them. Left as a
    collection they are dropped silently by the loader in ``closures.py``, which
    reads ``coordinates`` and finds none. Flattening here is what keeps them.
    """
    kind = geometry.get("type")
    if kind == "Polygon":
        return [geometry["coordinates"]]
    if kind == "MultiPolygon":
        return list(geometry["coordinates"])
    if kind == "GeometryCollection":
        out: list = []
        for inner in geometry.get("geometries", []):
            out.extend(_polygons(inner))
        return out
    # LineStrings and points describe a boundary trace, not an area. A polygon
    # is what a containment test needs, so they are dropped rather than guessed
    # at by closing the ring.
    return []


def _designation(properties: dict) -> str:
    category = (properties.get("category") or "").strip()
    return category or "Protected area"


def build(source_path: Path) -> None:
    with source_path.open(encoding="utf-8") as handle:
        data = json.load(handle)

    features = []
    seen: set[str] = set()
    for feature in data.get("features", []):
        properties = feature.get("properties") or {}
        name = (properties.get("name") or "").strip()
        state = (properties.get("state") or "").strip()

        if state not in ISLAND_STATES and name not in MAINLAND_MARINE:
            continue

        polygons = _polygons(feature.get("geometry") or {})
        if not polygons:
            print(f"  ! {name} ({state}) has no polygon — skipped")
            continue

        seen.add(name)
        area = properties.get("area_sqkm")
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "name": name,
                    "designation": _designation(properties),
                    "state": state,
                    "district": properties.get("district"),
                    # The published figure. For some areas it counts only the
                    # land — Gulf of Mannar is given as 6.23 km² while its
                    # geometry spans the whole island chain — so it is carried
                    # as the source's own number and never recomputed here.
                    "areaSqKm": float(area) if area not in (None, "") else None,
                    "establishedYear": properties.get("esta_year"),
                    "source": SOURCE,
                },
                "geometry": {"type": "MultiPolygon", "coordinates": polygons},
            }
        )

    missing = MAINLAND_MARINE - seen
    if missing:
        print("\n  ! named but not found in the source — check the spelling:")
        for name in sorted(missing):
            print(f"      {name}")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8") as handle:
        json.dump({"type": "FeatureCollection", "features": features}, handle)

    size_mb = OUTPUT.stat().st_size / 1_000_000
    islands = sum(1 for f in features if f["properties"]["state"] in ISLAND_STATES)
    print(
        f"\n  wrote {len(features)} protected areas "
        f"({len(features) - islands} mainland, {islands} island) "
        f"to {OUTPUT.name} — {size_mb:.1f} MB"
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(
            "usage: python backend/scripts/build_mpa_from_gatishakti.py "
            "<GatiShakti_Wildlife_Sanctuaries_and_National_Parks.geojson>"
        )
    build(Path(sys.argv[1]))
