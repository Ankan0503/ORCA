"""Area conditions — rain, storms and currents across the sea, not at one point.

Backs two map layers: the hazard overlay ("where is the heavy rain and
lightning") and the current arrows ("which way is the water setting"). The
router uses the same grid, so what a fisherman is shown and what the route was
planned around are the same data.
"""

from fastapi import APIRouter, HTTPException, Query, Response

from ..tools import seagrid

router = APIRouter(prefix="/seagrid", tags=["seagrid"])


@router.get("")
async def sea_grid(
    response: Response,
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    span: float = Query(1.5, gt=0, le=4.0, description="Half-width of the box, in degrees"),
    side: int = Query(9, ge=2, le=seagrid.MAX_GRID_SIDE),
) -> dict:
    """Hazards and currents on a grid around a position."""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    try:
        cells = await seagrid.fetch_area(lat, lon, span_deg=span, side=side)
    except seagrid.SeaGridError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    sea = [c for c in cells if c.is_sea]
    return {
        "origin": {"latitude": lat, "longitude": lon},
        "spanDeg": span,
        "cells": [c.to_dict() for c in sea],
        "counts": {
            "total": len(cells),
            "sea": len(sea),
            "thunderstorm": sum(1 for c in sea if c.is_thunderstorm),
            "rain": sum(1 for c in sea if c.rain_band != "none"),
            "suspectCurrents": sum(1 for c in sea if c.current_is_suspect),
        },
        "thresholds": {
            "rainLightMm": seagrid.RAIN_LIGHT_MM,
            "rainModerateMm": seagrid.RAIN_MODERATE_MM,
            "rainHeavyMm": seagrid.RAIN_HEAVY_MM,
            "currentPlausibleMaxMs": seagrid.CURRENT_PLAUSIBLE_MAX_MS,
            "note": (
                "Rain bands are ORCA's own reading of the forecast. Current speeds are "
                "capped at a plausible surface maximum because Open-Meteo warns its "
                "current accuracy is limited close to shore."
            ),
        },
        "source": "Open-Meteo Marine + Forecast API",
    }
