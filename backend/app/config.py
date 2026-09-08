"""Runtime configuration, read once from the environment."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Sarvam AI powers the language edges: speech in, speech out, translation.
    sarvam_api_key: str = ""
    sarvam_base_url: str = "https://api.sarvam.ai"
    sarvam_stt_model: str = "saaras:v3"
    sarvam_tts_model: str = "bulbul:v3"
    sarvam_translate_model: str = "mayura:v1"

    # Groq does the planning and reasoning. Optional: without it the
    # orchestrator uses its rule-based planner instead of falling over.
    groq_api_key: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_model: str = "openai/gpt-oss-120b"

    cors_origins: str = (
        "http://localhost:3000,http://127.0.0.1:3000,http://192.168.29.43:3000,"
        "http://localhost:5173,http://127.0.0.1:5173,http://192.168.29.43:5173"
    )
    # Every origin allowed to call this API, kept in the repository rather than
    # only in a hosting dashboard, where nobody reviewing the code can see it
    # and a stale value is invisible until something breaks.
    #
    # Three groups:
    #   - local development and LAN devices;
    #   - the packaged app, which Capacitor serves from https://localhost on
    #     Android and capacitor://localhost on iOS — both cross-origin to this
    #     backend, so an APK that cannot call its own API is what naming them
    #     prevents;
    #   - the deployed web app and its preview builds.
    cors_origin_regex: str = (
        r"^(https?|capacitor|ionic)://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+"
        r"|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+)(:\d+)?$"
        r"|^https://marine-orca\.vercel\.app$"
        r"|^https://[a-z0-9-]*ankangiri05-9229s-projects\.vercel\.app$"
    )

    request_timeout_seconds: float = 60.0

    # External APIs and services — all overridable via .env
    incois_textdata_url: str = "https://incois.gov.in/MarineFisheries/TextData"
    incois_textdata_home_url: str = "https://incois.gov.in/MarineFisheries/TextDataHome"
    incois_pfz_lines_wfs_url: str = (
        "https://incois.gov.in/geoserver/PFZ_Automation/ows"
        "?service=WFS&version=1.1.0&request=GetFeature"
        "&typeName=PFZ_Automation:pfzlines&outputFormat=application/json"
    )
    noaa_erddap_url: str = (
        "https://coastwatch.noaa.gov/erddap/griddap/noaacwNPPN20S3ASCIDINEOF2kmDaily.json"
    )
    open_meteo_marine_url: str = "https://marine-api.open-meteo.com/v1/marine"
    open_meteo_forecast_url: str = "https://api.open-meteo.com/v1/forecast"
    open_meteo_geocoding_url: str = "https://geocoding-api.open-meteo.com/v1/search"
    bigdatacloud_reverse_url: str = (
        "https://api.bigdatacloud.net/data/reverse-geocode-client"
    )
    nominatim_reverse_url: str = "https://nominatim.openstreetmap.org/reverse"

    # Potential Fishing Zone advisories are scraped from INCOIS, which publishes
    # a fresh advisory the afternoon before the forecast day. The scheduled
    # refresh runs once a day at this local (IST) time; change these two numbers
    # to move it. A lazy re-fetch on first access each day backs it up, so a
    # missed run is not a missed advisory.
    pfz_refresh_hour_ist: int = 18
    pfz_refresh_minute_ist: int = 30
    # Turn the background scheduler off entirely (the lazy per-day refresh still
    # works). Useful in tests or when a external cron drives the refresh instead.
    pfz_scheduler_enabled: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def has_groq(self) -> bool:
        return bool(self.groq_api_key)

    @property
    def has_sarvam(self) -> bool:
        return bool(self.sarvam_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
