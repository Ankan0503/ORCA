"""Place search, so a fisherman can set where they actually are.

Everything ORCA says is tied to a coordinate — waves, wind, fishing zones,
distance to a boundary. Until now that coordinate was hardcoded to Digha, which
made every answer wrong for anyone else on the coast.

Open-Meteo's geocoding service backs this and needs no API key, matching the
forecast source already in use. Results are biased to India, since that is who
the platform serves.
"""

import time
import unicodedata

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

import httpx

from ..config import get_settings

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
REVERSE_URL = "https://api.bigdatacloud.net/data/reverse-geocode-client"
# Fallback naming service. Nominatim asks for an identifying User-Agent.
NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"
NOMINATIM_UA = "ORCA-Marine/0.1 (SIH 26176 marine advisory prototype)"

router = APIRouter(prefix="/location", tags=["location"])

# Geocoding is slow upstream — measured at 1.2 to 4.5 seconds — and a search box
# fires a request per keystroke. Results for a place name do not change, so they
# are held for an hour; retyping and backspacing then cost nothing.
_SEARCH_TTL_SECONDS = 3600
_search_cache: dict[str, tuple[float, list["Place"]]] = {}


def simplify_name(name: str) -> str:
    """Drop transliteration marks from Latin place names: Verāval -> Veraval.

    The geocoding service returns scholarly transliterations, and to someone who
    writes the name every day the macrons read as misspellings rather than
    precision.

    Combining marks are only removed when they sit on a Latin letter. Indic
    scripts use combining marks as vowel signs — stripping those would not tidy
    a name, it would destroy the word.
    """
    out: list[str] = []
    base_is_latin = False
    for char in unicodedata.normalize("NFD", name):
        if unicodedata.combining(char):
            if not base_is_latin:
                out.append(char)
            continue
        base_is_latin = char.isascii() and char.isalpha()
        out.append(char)
    return unicodedata.normalize("NFC", "".join(out))


class Place(BaseModel):
    name: str
    latitude: float
    longitude: float
    admin: str | None = None
    country: str | None = None
    country_code: str | None = None
    timezone: str | None = None

    @property
    def label(self) -> str:
        return ", ".join(part for part in (self.name, self.admin) if part)


class PlaceSearchResponse(BaseModel):
    results: list[Place]


class ReverseResponse(BaseModel):
    name: str
    latitude: float
    longitude: float
    admin: str | None = None
    country: str | None = None


@router.get("/search", response_model=PlaceSearchResponse)
async def search_places(
    q: str = Query(min_length=2, max_length=80, description="Place name to look for"),
    limit: int = Query(8, ge=1, le=20),
    country: str | None = Query("IN", description="ISO country code, or empty for worldwide"),
) -> PlaceSearchResponse:
    cache_key = f"{q.strip().lower()}|{limit}|{country or ''}"
    hit = _search_cache.get(cache_key)
    if hit and (time.monotonic() - hit[0]) < _SEARCH_TTL_SECONDS:
        return PlaceSearchResponse(results=hit[1])

    params: dict[str, object] = {"name": q, "count": limit, "language": "en", "format": "json"}
    if country:
        params["countryCode"] = country

    timeout = get_settings().request_timeout_seconds
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(GEOCODING_URL, params=params)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Place search unavailable: {exc}") from exc

    if response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=f"Place search failed ({response.status_code})",
        )

    payload = response.json() or {}
    places = [
        Place(
            name=simplify_name(item.get("name", "")),
            latitude=item["latitude"],
            longitude=item["longitude"],
            admin=simplify_name(item.get("admin1") or "") or None,
            country=item.get("country"),
            country_code=item.get("country_code"),
            timezone=item.get("timezone"),
        )
        for item in (payload.get("results") or [])
        if item.get("latitude") is not None and item.get("longitude") is not None
    ]
    _search_cache[cache_key] = (time.monotonic(), places)
    return PlaceSearchResponse(results=places)


@router.get("/reverse", response_model=ReverseResponse)
async def reverse_geocode(
    latitude: float = Query(ge=-90, le=90),
    longitude: float = Query(ge=-180, le=180),
) -> ReverseResponse:
    """Name a coordinate that came from the device's GPS.

    Two providers are tried in turn. Naming is what makes a detected position
    useful — "Haldia, West Bengal" tells a fisherman something, "22.048N,
    88.064E" tells them nothing — so a single service being unreachable should
    not cost the name.

    Both are queried with redirects followed: BigDataCloud answers this path
    with a 307, and not following it was why detection silently degraded to
    bare coordinates.
    """
    timeout = get_settings().request_timeout_seconds

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        named = await _try_bigdatacloud(client, latitude, longitude)
        if named is None:
            named = await _try_nominatim(client, latitude, longitude)

    if named is None:
        raise HTTPException(status_code=502, detail="Could not name this location")

    name, admin, country = named
    return ReverseResponse(
        name=simplify_name(name),
        latitude=latitude,
        longitude=longitude,
        admin=simplify_name(admin) if admin else None,
        country=country,
    )


async def _try_bigdatacloud(
    client: httpx.AsyncClient, latitude: float, longitude: float
) -> tuple[str, str | None, str | None] | None:
    try:
        response = await client.get(
            REVERSE_URL,
            params={"latitude": latitude, "longitude": longitude, "localityLanguage": "en"},
        )
        if response.status_code >= 400:
            return None
        data = response.json() or {}
    except (httpx.HTTPError, ValueError):
        return None

    name = data.get("locality") or data.get("city") or data.get("principalSubdivision")
    if not name:
        return None
    return name, data.get("principalSubdivision"), data.get("countryName")


async def _try_nominatim(
    client: httpx.AsyncClient, latitude: float, longitude: float
) -> tuple[str, str | None, str | None] | None:
    try:
        response = await client.get(
            NOMINATIM_URL,
            params={
                "lat": latitude,
                "lon": longitude,
                "format": "jsonv2",
                # Town-level rather than street-level: a fisherman wants the
                # port they are at, not the lane they are standing in.
                "zoom": 12,
                "accept-language": "en",
            },
            headers={"User-Agent": NOMINATIM_UA},
        )
        if response.status_code >= 400:
            return None
        data = response.json() or {}
    except (httpx.HTTPError, ValueError):
        return None

    address = data.get("address") or {}
    name = (
        address.get("town")
        or address.get("city")
        or address.get("municipality")
        or address.get("village")
        or address.get("county")
    )
    if not name:
        return None
    return name, address.get("state"), address.get("country")
