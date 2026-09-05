"""Place search, so a fisherman can set where they actually are.

Everything ORCA says is tied to a coordinate — waves, wind, fishing zones,
distance to a boundary. Until now that coordinate was hardcoded to Digha, which
made every answer wrong for anyone else on the coast.

Open-Meteo's geocoding service backs this and needs no API key, matching the
forecast source already in use. Results are biased to India, since that is who
the platform serves.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

import httpx

from ..config import get_settings

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
REVERSE_URL = "https://api.bigdatacloud.net/data/reverse-geocode-client"

router = APIRouter(prefix="/location", tags=["location"])


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
    params: dict[str, object] = {"name": q, "count": limit, "language": "en", "format": "json"}
    if country:
        params["countryCode"] = country

    timeout = get_settings().request_timeout_seconds
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
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
            name=item.get("name", ""),
            latitude=item["latitude"],
            longitude=item["longitude"],
            admin=item.get("admin1"),
            country=item.get("country"),
            country_code=item.get("country_code"),
            timezone=item.get("timezone"),
        )
        for item in (payload.get("results") or [])
        if item.get("latitude") is not None and item.get("longitude") is not None
    ]
    return PlaceSearchResponse(results=places)


@router.get("/reverse", response_model=ReverseResponse)
async def reverse_geocode(
    latitude: float = Query(ge=-90, le=90),
    longitude: float = Query(ge=-180, le=180),
) -> ReverseResponse:
    """Name a coordinate that came from the device's GPS.

    Naming is a convenience: the forecast only needs the coordinate, so if this
    lookup fails the caller still has a usable position and simply shows the
    numbers instead.
    """
    timeout = get_settings().request_timeout_seconds
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(
                REVERSE_URL,
                params={
                    "latitude": latitude,
                    "longitude": longitude,
                    "localityLanguage": "en",
                },
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Reverse lookup unavailable: {exc}") from exc

    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail="Reverse lookup failed")

    data = response.json() or {}
    name = data.get("locality") or data.get("city") or data.get("principalSubdivision") or ""
    return ReverseResponse(
        name=name,
        latitude=latitude,
        longitude=longitude,
        admin=data.get("principalSubdivision"),
        country=data.get("countryName"),
    )
