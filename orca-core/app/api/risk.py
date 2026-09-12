"""Overall trip risk, ML inference and 24-hour tomorrow forecast endpoints."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field

from ..agents.base import QueryContext
from ..agents.risk import RiskAssessmentAgent
from ..dependencies import get_sarvam
from ..language.localise import localise
from ..providers.sarvam import SarvamClient
from ..tools.marine import fetch_marine_conditions
from ..tools.ml_risk import predict_batch_risk, predict_point_risk

router = APIRouter(tags=["risk"])

_agent = RiskAssessmentAgent()

# Predefined coastal coordinates for Indian fishing centers
COASTAL_LOCATIONS = {
    "digha": (21.626, 87.508, "Digha, West Bengal"),
    "paradip": (20.264, 86.679, "Paradip, Odisha"),
    "vizag": (17.686, 83.218, "Visakhapatnam, Andhra Pradesh"),
    "chennai": (13.082, 80.271, "Chennai, Tamil Nadu"),
    "kochi": (9.931, 76.267, "Kochi, Kerala"),
    "goa": (15.300, 73.800, "Panaji, Goa"),
    "mumbai": (18.922, 72.834, "Mumbai, Maharashtra"),
    "porbandar": (21.642, 69.609, "Porbandar, Gujarat"),
}


class RiskPredictionRequest(BaseModel):
    wind_speed_kts: float | None = Field(default=None, description="Wind speed in knots")
    wind_gust_kts: float | None = Field(default=None, description="Wind gusts in knots")
    wave_height_m: float | None = Field(default=None, description="Wave height in meters")
    wave_period_s: float | None = Field(default=6.0, description="Wave period in seconds")
    wind_direction_deg: float | None = Field(default=0.0)
    wave_direction_deg: float | None = Field(default=0.0)
    latitude: float = Field(default=21.626)
    longitude: float = Field(default=87.508)
    air_pressure_hpa: float | None = Field(default=1012.0)
    air_temperature_c: float | None = Field(default=28.0)
    water_temperature_c: float | None = Field(default=28.0)
    month: int | None = Field(default=None)
    hour: int | None = Field(default=None)


@router.get("/risk")
async def assess_risk(
    response: Response,
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    lang: str = Query("en"),
    sarvam: SarvamClient = Depends(get_sarvam),
) -> dict:
    """Sea safety, boundary proximity, trip reachability and ML scoring as one verdict."""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    result = await _agent.run(
        QueryContext(
            question="What is the overall risk of going out?",
            language=lang,
            latitude=lat,
            longitude=lon,
        )
    )
    return await localise(result.to_dict(), lang, sarvam)


@router.post("/marine/risk")
async def predict_risk_endpoint(
    payload: RiskPredictionRequest = Body(...),
) -> dict:
    """Point-in-time calibrated ML risk evaluation."""
    prediction = predict_point_risk(payload.model_dump())
    return prediction.to_dict()


@router.get("/marine/forecast")
async def get_marine_forecast(
    lat: float | None = Query(None, ge=-90, le=90),
    lon: float | None = Query(None, ge=-180, le=180),
    locationKey: str | None = Query(None),
) -> dict:
    """Tomorrow hourly Open-Meteo weather + marine forecast with evaluated ML risk."""
    place_name = "Custom Location"
    if locationKey and locationKey.lower() in COASTAL_LOCATIONS:
        c_lat, c_lon, name = COASTAL_LOCATIONS[locationKey.lower()]
        lat, lon, place_name = c_lat, c_lon, name
    elif lat is None or lon is None:
        lat, lon, place_name = COASTAL_LOCATIONS["digha"]

    conditions = await fetch_marine_conditions(lat, lon)
    if not conditions or not conditions.hourly:
        raise HTTPException(status_code=502, detail="Forecast service returned no hourly data")

    now = datetime.now(timezone.utc)
    tomorrow_date = (now + timedelta(days=1)).date()

    # Filter for tomorrow's 24 hours
    tomorrow_hourly = [h for h in conditions.hourly if h.time.date() == tomorrow_date]
    if not tomorrow_hourly:
        # Fallback to the next 24 hourly observations if calendar tomorrow is not in window
        tomorrow_hourly = conditions.hourly[:24]

    features_list = []
    for h in tomorrow_hourly:
        features_list.append({
            "wind_speed_kts": h.wind_speed_kmh * 0.539957,
            "wind_gust_kts": h.wind_gusts_kmh * 0.539957,
            "wave_height_m": h.wave_height_m,
            "wave_period_s": h.wave_period_s,
            "mean_wave_period_s": h.wave_period_s,
            "wind_direction_deg": h.wind_direction_deg,
            "wave_direction_deg": h.wave_direction_deg,
            "air_pressure_hpa": h.pressure_hpa,
            "air_temperature_c": h.temperature_c,
            "water_temperature_c": h.sea_surface_temperature_c,
            "latitude": lat,
            "longitude": lon,
            "month": h.time.month,
            "hour": h.time.hour,
        })

    ml_predictions = predict_batch_risk(features_list)

    hourly_timeline = []
    max_risk_score = 0.0
    worst_risk_level = "LOW"
    level_order = {"LOW": 0, "MODERATE": 1, "HIGH": 2, "EXTREME": 3}

    for h, pred in zip(tomorrow_hourly, ml_predictions):
        hourly_timeline.append({
            "time": h.time.isoformat(),
            "waveHeightM": round(h.wave_height_m, 2),
            "wavePeriodS": round(h.wave_period_s, 1),
            "windSpeedKts": round(h.wind_speed_kmh * 0.539957, 1),
            "windGustKts": round(h.wind_gusts_kmh * 0.539957, 1),
            "temperatureC": round(h.temperature_c, 1),
            "riskLevel": pred.risk_level,
            "riskScore": pred.risk_score,
            "confidence": pred.confidence_score,
            "modelVersion": pred.model_version,
            "isFallback": pred.is_fallback,
        })
        if pred.risk_score > max_risk_score:
            max_risk_score = pred.risk_score
        if level_order.get(pred.risk_level, 0) > level_order.get(worst_risk_level, 0):
            worst_risk_level = pred.risk_level

    return {
        "location": {
            "latitude": lat,
            "longitude": lon,
            "name": place_name,
        },
        "sourceType": "FORECAST",
        "forecastDate": tomorrow_date.isoformat(),
        "summary": {
            "worstRiskLevel": worst_risk_level,
            "peakRiskScore": max_risk_score,
            "hourlyCount": len(hourly_timeline),
            "verdict": (
                f"Tomorrow's forecast for {place_name} peaks at {worst_risk_level} risk ({max_risk_score:.0f}/100). "
                + ("Vessel departures should be suspended during peak hours." if worst_risk_level in ("HIGH", "EXTREME") else "Conditions generally permit operations with caution.")
            ),
        },
        "hourly": hourly_timeline,
    }
