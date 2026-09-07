"""Convert a Protected Planet (WDPA/WDOECM) shapefile download into ORCA's MPA layer.

Run this after downloading India's protected areas from protectedplanet.net and
unzipping the three parts. It writes ``backend/data/geo/india_mpa.geojson``,
keeping only areas with a marine component — a terrestrial sanctuary inland is
not a hazard to a boat.

    python scripts/build_mpa_geojson.py "C:/path/to/WDPA_..._IND_shp"

Two things worth knowing before trusting the output.

**The download must not be filtered to international designations.** A first
attempt produced 63 records that were all Ramsar sites, World Heritage sites and
one Biosphere Reserve — `DESIG_TYPE` was "International" for every one. India's
Marine Protected Areas are *national* designations (Wildlife Sanctuary, National
Park), so none of them were present: no Gulf of Mannar, no Gahirmatha, none of
the 106 island sanctuaries in the Andamans. This script therefore reports the
designation breakdown it found, so a filtered download is obvious rather than
silently producing a near-empty layer.

**The three zip parts share filenames.** Extracting them into one directory
overwrites two thirds of the data, which is easy to do and impossible to notice
afterwards. Each part is read from its own directory here.
"""

from __future__ import annotations

import collections
import json
import pathlib
import sys
import zipfile


def load_parts(source: pathlib.Path, work: pathlib.Path) -> list[pathlib.Path]:
    """Extract each zip into its own directory and return the polygon layers."""
    work.mkdir(parents=True, exist_ok=True)
    layers: list[pathlib.Path] = []

    zips = sorted(source.glob("*.zip"))
    if zips:
        for archive in zips:
            target = work / archive.stem
            target.mkdir(exist_ok=True)
            zipfile.ZipFile(archive).extractall(target)
    else:
        work = source  # already-extracted directory

    for shp in sorted((work if not zips else work).rglob("*-polygons.shp")):
        layers.append(shp)
    return layers


def marine_area(record: dict) -> float:
    for key in ("GIS_M_AREA", "REP_M_AREA"):
        try:
            value = float(record.get(key) or 0)
        except (TypeError, ValueError):
            continue
        if value > 0:
            return value
    return 0.0


def build(source: pathlib.Path, out_path: pathlib.Path) -> dict:
    try:
        import shapefile  # pyshp
    except ImportError:
        print("pyshp is required:  python -m pip install pyshp", file=sys.stderr)
        raise SystemExit(1)

    work = out_path.parent / "_wdpa_work"
    layers = load_parts(source, work)
    if not layers:
        print(f"No *-polygons.shp found under {source}", file=sys.stderr)
        raise SystemExit(1)

    features: list[dict] = []
    designation_types: collections.Counter = collections.Counter()
    total = 0

    for layer in layers:
        reader = shapefile.Reader(str(layer))
        fields = [f[0] for f in reader.fields[1:]]
        for item in reader.iterShapeRecords():
            total += 1
            record = dict(zip(fields, item.record))
            designation_types[record.get("DESIG_TYPE")] += 1

            if marine_area(record) <= 0:
                continue

            geometry = item.shape.__geo_interface__
            if geometry.get("type") not in ("Polygon", "MultiPolygon"):
                continue

            features.append(
                {
                    "type": "Feature",
                    "geometry": geometry,
                    "properties": {
                        "name": record.get("NAME") or record.get("NAME_ENG"),
                        "designation": record.get("DESIG_ENG"),
                        "designationType": record.get("DESIG_TYPE"),
                        "iucnCategory": record.get("IUCN_CAT"),
                        "marineAreaKm2": round(marine_area(record), 2),
                        "noTake": record.get("NO_TAKE"),
                        "status": record.get("STATUS"),
                        "statusYear": record.get("STATUS_YR"),
                        "managingAuthority": record.get("MANG_AUTH"),
                    },
                }
            )

    collection = {
        "type": "FeatureCollection",
        "features": features,
        "orca_source": "Protected Planet (WDPA/WDOECM), UNEP-WCMC",
        "orca_note": "Areas with a marine component only.",
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(collection), encoding="utf-8")

    print(f"records read        : {total}")
    print(f"marine areas written: {len(features)}  -> {out_path}")
    print("designation types   :", dict(designation_types))
    if set(designation_types) <= {"International"}:
        print(
            "\nWARNING: every record is an International designation (Ramsar, World\n"
            "Heritage, Biosphere Reserve). India's Marine Protected Areas are national\n"
            "designations — Wildlife Sanctuary and National Park — so this download is\n"
            "missing them entirely. Re-download from protectedplanet.net without\n"
            "restricting the designation type.",
            file=sys.stderr,
        )
    return collection


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(1)
    root = pathlib.Path(__file__).resolve().parent.parent
    build(pathlib.Path(sys.argv[1]), root / "data" / "geo" / "india_mpa.geojson")
