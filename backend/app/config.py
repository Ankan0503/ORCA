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

    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    request_timeout_seconds: float = 60.0

    # Potential Fishing Zone advisories are scraped from INCOIS, which publishes
    # a fresh advisory the afternoon before the forecast day. The scheduled
    # refresh runs once a day at this local (IST) time; change these two numbers
    # to move it. A lazy re-fetch on first access each day backs it up, so a
    # missed run is not a missed advisory.
    pfz_refresh_hour_ist: int = 17
    pfz_refresh_minute_ist: int = 0
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
