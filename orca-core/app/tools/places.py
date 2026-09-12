"""Coastal places a question can name, so "near Paradip" is answered about Paradip."""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Place:
    name: str
    latitude: float
    longitude: float


# Harbour-town centres; close enough to pick the right forecast cell and PFZ sector.
_PLACES: tuple[tuple[str, float, float, tuple[str, ...]], ...] = (
    ("Digha, West Bengal", 21.6266, 87.5074, ("digha",)),
    ("Sagar Island, West Bengal", 21.6500, 88.0833, ("sagar island", "kakdwip")),
    ("Puri, Odisha", 19.7983, 85.8249, ("puri",)),
    ("Paradip, Odisha", 20.2644, 86.6947, ("paradip", "paradeep")),
    ("Gopalpur, Odisha", 19.2612, 84.9089, ("gopalpur",)),
    ("Visakhapatnam, Andhra Pradesh", 17.6868, 83.2185, ("visakhapatnam", "vishakhapatnam", "vizag")),
    ("Kakinada, Andhra Pradesh", 16.9891, 82.2475, ("kakinada",)),
    ("Machilipatnam, Andhra Pradesh", 16.1875, 81.1389, ("machilipatnam",)),
    ("Chennai, Tamil Nadu", 13.0827, 80.2707, ("chennai", "madras", "kasimedu")),
    ("Puducherry", 11.9340, 79.8300, ("puducherry", "pondicherry")),
    ("Nagapattinam, Tamil Nadu", 10.7660, 79.8430, ("nagapattinam",)),
    ("Rameswaram, Tamil Nadu", 9.2880, 79.3130, ("rameswaram", "rameshwaram")),
    ("Thoothukudi, Tamil Nadu", 8.7642, 78.1348, ("thoothukudi", "tuticorin")),
    ("Kanyakumari, Tamil Nadu", 8.0780, 77.5410, ("kanyakumari",)),
    ("Kollam, Kerala", 8.8930, 76.6140, ("kollam", "quilon", "neendakara")),
    ("Kochi, Kerala", 9.9312, 76.2673, ("kochi", "cochin")),
    ("Kozhikode, Kerala", 11.2590, 75.7800, ("kozhikode", "calicut", "beypore")),
    ("Mangaluru, Karnataka", 12.8698, 74.8430, ("mangaluru", "mangalore")),
    ("Karwar, Karnataka", 14.8050, 74.1290, ("karwar",)),
    ("Goa", 15.4187, 73.8055, ("goa", "panaji", "mormugao", "vasco")),
    ("Ratnagiri, Maharashtra", 16.9900, 73.3120, ("ratnagiri",)),
    ("Mumbai, Maharashtra", 18.9220, 72.8347, ("mumbai", "bombay", "sassoon dock")),
    ("Veraval, Gujarat", 20.9077, 70.3677, ("veraval",)),
    ("Porbandar, Gujarat", 21.6417, 69.6293, ("porbandar",)),
    ("Okha, Gujarat", 22.4670, 69.0700, ("okha",)),
    ("Port Blair, Andaman and Nicobar", 11.6234, 92.7265, ("port blair",)),
    ("Krishnapatnam, Andhra Pradesh", 14.2500, 80.1200, ("krishnapatnam", "nellore")),
    ("Kavaratti, Lakshadweep", 10.5660, 72.6420, ("kavaratti",)),
    # Regions and states resolve to their main fishing harbour.
    ("West Bengal coast (Digha)", 21.6266, 87.5074, ("west bengal", "bengal coast")),
    ("Odisha coast (Paradip)", 20.2644, 86.6947, ("odisha", "orissa")),
    (
        "North Andhra Pradesh coast (Visakhapatnam)", 17.6868, 83.2185,
        ("northern andhra pradesh", "north andhra pradesh", "northern andhra", "north andhra",
         "north coastal andhra", "uttarandhra", "srikakulam"),
    ),
    (
        "South Andhra Pradesh coast (Krishnapatnam)", 14.2500, 80.1200,
        ("southern andhra pradesh", "south andhra pradesh", "southern andhra", "south andhra"),
    ),
    ("Andhra Pradesh coast (Kakinada)", 16.9891, 82.2475, ("andhra pradesh", "andhra")),
    ("Tamil Nadu coast (Chennai)", 13.0827, 80.2707, ("tamil nadu", "coromandel")),
    ("Kerala coast (Kochi)", 9.9312, 76.2673, ("kerala",)),
    ("Karnataka coast (Mangaluru)", 12.8698, 74.8430, ("karnataka",)),
    ("Maharashtra coast (Mumbai)", 18.9220, 72.8347, ("maharashtra", "konkan")),
    ("Gujarat coast (Veraval)", 20.9077, 70.3677, ("gujarat", "saurashtra")),
    ("Andaman Islands (Port Blair)", 11.6234, 92.7265, ("andaman",)),
    ("Lakshadweep (Kavaratti)", 10.5660, 72.6420, ("lakshadweep",)),
)

_PATTERNS = [
    (re.compile(rf"\b{re.escape(alias)}\b", re.I), Place(name, lat, lon))
    for name, lat, lon, aliases in _PLACES
    for alias in aliases
]


def find_place(text: str) -> Place | None:
    """The first coastal place the text names, or None."""
    hits = [(m.start(), place) for pattern, place in _PATTERNS if (m := pattern.search(text))]
    return min(hits, key=lambda hit: hit[0])[1] if hits else None
