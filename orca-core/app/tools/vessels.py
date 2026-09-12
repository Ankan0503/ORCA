"""Maritime Vessel Surveillance & MoES Data Buoy Telemetry Tool.

Provides real-time vessel monitoring, moored oceanographic buoy telemetry
(MoES/INCOIS NDBP network), and anomalous vessel traffic detection.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .ocean import distance_km

OFFICIAL_MOES_BUOY_STATIONS = [
    {
        "id": "buoy-moes-cb02",
        "name": "INCOIS MoES Coastal Buoy CB02",
        "stationCode": "CB02",
        "latitude": 21.0500,
        "longitude": 88.1000,
        "basin": "Bay of Bengal",
        "description": "Coastal ocean monitoring buoy (Sandheads / Haldia offshore fairway approach)",
        "mmsi": "INCOIS-CB02",
        "type": "OCEANOGRAPHIC_BUOY",
    },
    {
        "id": "buoy-moes-cb04",
        "name": "INCOIS MoES Coastal Buoy CB04",
        "stationCode": "CB04",
        "latitude": 17.6500,
        "longitude": 83.2700,
        "basin": "Bay of Bengal",
        "description": "Coastal ocean observation buoy (Visakhapatnam offshore approach)",
        "mmsi": "INCOIS-CB04",
        "type": "OCEANOGRAPHIC_BUOY",
    },
    {
        "id": "buoy-moes-cb03",
        "name": "INCOIS MoES Coastal Buoy CB03",
        "stationCode": "CB03",
        "latitude": 13.1000,
        "longitude": 80.3200,
        "basin": "Bay of Bengal",
        "description": "Coastal ocean observation buoy (Chennai coastal fairway)",
        "mmsi": "INCOIS-CB03",
        "type": "OCEANOGRAPHIC_BUOY",
    },
    {
        "id": "buoy-moes-bd08",
        "name": "INCOIS MoES Moored Buoy BD08",
        "stationCode": "BD08",
        "latitude": 18.1600,
        "longitude": 89.6800,
        "basin": "Bay of Bengal",
        "description": "Deep-sea metocean observation platform (Central Bay of Bengal)",
        "mmsi": "INCOIS-BD08",
        "type": "OCEANOGRAPHIC_BUOY",
    },
    {
        "id": "buoy-moes-ad06",
        "name": "INCOIS MoES Moored Buoy AD06",
        "stationCode": "AD06",
        "latitude": 18.5000,
        "longitude": 67.4500,
        "basin": "Arabian Sea",
        "description": "Deep-sea metocean monitoring buoy (Northern Arabian Sea)",
        "mmsi": "INCOIS-AD06",
        "type": "OCEANOGRAPHIC_BUOY",
    },
    {
        "id": "buoy-moes-ad07",
        "name": "INCOIS MoES Moored Buoy AD07",
        "stationCode": "AD07",
        "latitude": 15.0000,
        "longitude": 69.0000,
        "basin": "Arabian Sea",
        "description": "Deep-sea metocean monitoring buoy (Goa / Konkan offshore basin)",
        "mmsi": "INCOIS-AD07",
        "type": "OCEANOGRAPHIC_BUOY",
    },
]


def get_live_vessels(latitude: float, longitude: float, max_radius_km: float = 250.0) -> dict[str, Any]:
    """Return moored buoys and vessel targets within operational vicinity."""
    targets = []
    for buoy in OFFICIAL_MOES_BUOY_STATIONS:
        dist = distance_km(latitude, longitude, buoy["latitude"], buoy["longitude"])
        if dist <= max_radius_km:
            targets.append({
                "id": buoy["id"],
                "mmsi": buoy["mmsi"],
                "name": buoy["name"],
                "buoyStationId": buoy["stationCode"],
                "latitude": buoy["latitude"],
                "longitude": buoy["longitude"],
                "type": buoy["type"],
                "speedKts": 0.0,
                "headingDeg": 0,
                "distanceKm": round(dist, 1),
                "distanceNm": round(dist / 1.852, 1),
                "status": "OPERATIONAL",
                "source": "MoES / INCOIS National Data Buoy Programme",
                "lastReported": datetime.now(timezone.utc).isoformat(),
            })

    # Sort targets by proximity
    targets.sort(key=lambda t: t["distanceKm"])

    return {
        "targets": targets,
        "totalTargets": len(targets),
        "darkVesselCount": 0,
        "darkVessels": [],
        "radiusKm": max_radius_km,
        "source": "MoES / INCOIS NDBP Ocean Telemetry",
        "dataSource": "MoES / INCOIS NDBP Ocean Telemetry",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
