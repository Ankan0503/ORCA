"""The forecast survives a rate-limited host, and refuses rather than inventing calm.

Open-Meteo meters a free caller by the day and per subdomain. A shared address --
a campus, a hackathon hall -- can spend the day's allowance before noon, after
which every request returns 429. These tests pin the behaviour that matters when
that happens, because it happened.
"""

import asyncio
import time
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from app.tools import marine as M


QUOTA_BODY = '{"error":true,"reason":"Daily API request limit exceeded."}'
IST_OFFSET = 19800
#: What the marine host's own note looks like, for seeding the stale store.
_LIVE_MARINE = M.SourceNote("Open-Meteo Marine", live=True)


def _times() -> list[str]:
    """Local hours from today's midnight, the way Open-Meteo returns them."""
    local = (datetime.now(timezone.utc) + timedelta(seconds=IST_OFFSET)).replace(tzinfo=None)
    start = local.replace(hour=0, minute=0, second=0, microsecond=0)
    return [(start + timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M") for h in range(72)]


def _weather_payload(times: list[str]) -> dict:
    n = len(times)
    return {
        "latitude": 21.62,
        "longitude": 87.52,
        "timezone": "Asia/Kolkata",
        "utc_offset_seconds": IST_OFFSET,
        "hourly": {
            "time": times,
            "wind_speed_10m": [18.0] * n,
            "wind_gusts_10m": [40.0] * n,
            "wind_direction_10m": [225.0] * n,
            "precipitation": [0.0] * n,
            "visibility": [10000.0] * n,
            "temperature_2m": [29.0] * n,
            "weather_code": [1] * n,
        },
        "daily": {"time": [times[0][:10]], "sunrise": [], "sunset": []},
    }


def _marine_payload(times: list[str]) -> dict:
    n = len(times)
    return {
        "latitude": 21.62,
        "longitude": 87.52,
        "timezone": "Asia/Kolkata",
        "utc_offset_seconds": IST_OFFSET,
        "hourly": {
            "time": times,
            "wave_height": [1.8] * n,
            "wave_period": [7.0] * n,
            "sea_surface_temperature": [28.0] * n,
        },
    }


@pytest.fixture(autouse=True)
def _clean_state():
    """Both stores are module-level, so one test must not inherit another's."""
    M._cache.clear()
    M._last_good.clear()
    yield
    M._cache.clear()
    M._last_good.clear()


def _router(monkeypatch, handler):
    """Answer every request from ``handler(url) -> (status, json or text)``."""

    async def fake_get(self, url, params=None, **kwargs):
        status, body = handler(str(url))
        request = httpx.Request("GET", str(url))
        if isinstance(body, str):
            return httpx.Response(status, text=body, request=request)
        return httpx.Response(status, json=body, request=request)

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)


def test_ensemble_host_carries_the_weather_when_the_forecast_host_is_rate_limited(monkeypatch):
    """A 429 on the forecast host must not cost us the wind."""
    times = _times()
    seen: list[str] = []

    def handler(url):
        seen.append(url)
        if "marine-api" in url:
            return 200, _marine_payload(times)
        if "ensemble-api" in url:
            return 200, _weather_payload(times)
        return 429, QUOTA_BODY

    _router(monkeypatch, handler)
    conditions = asyncio.run(M.fetch_marine_conditions(21.62, 87.52))

    now = conditions.hourly[conditions.index_at(conditions.local_now)]
    assert now.wind_gusts_kmh == 40.0, "the wind came through the ensemble host"
    assert now.wave_height_m == 1.8, "and the waves came through untouched"
    assert any("ensemble-api" in u for u in seen), "the ensemble host was actually tried"
    assert conditions.degraded, "and the answer admits it is not from first choice"
    assert "ensemble" in conditions.provenance.lower()


def test_missing_waves_are_refused_rather_than_served_as_calm(monkeypatch):
    """The one degradation that must never happen quietly.

    A wave height of None reads as 0.0 downstream, which scores as a smooth sea --
    so an outage would dress itself up as good weather. With no cached waves to
    stand in, refusing is the only honest answer.
    """
    times = _times()

    def handler(url):
        if "marine-api" in url:
            return 429, QUOTA_BODY
        return 200, _weather_payload(times)

    _router(monkeypatch, handler)
    with pytest.raises(M.MarineDataError) as raised:
        asyncio.run(M.fetch_marine_conditions(21.62, 87.52))
    assert "Marine forecast unavailable" in str(raised.value)


def test_a_half_that_answered_is_kept_even_when_the_other_half_fails(monkeypatch):
    """Banking every success before judging any of them.

    Resolving one half at a time discarded a good weather response whenever the
    marine half was the one that failed, so the next question refetched something
    that was already in hand.
    """
    times = _times()

    def handler(url):
        if "marine-api" in url:
            return 429, QUOTA_BODY
        return 200, _weather_payload(times)

    _router(monkeypatch, handler)
    with pytest.raises(M.MarineDataError):
        asyncio.run(M.fetch_marine_conditions(21.62, 87.52))

    assert any(k.startswith("weather:") for k in M._last_good), "the weather half was kept"


def test_cached_waves_stand_in_and_are_labelled_with_their_age(monkeypatch):
    """Real figures, honestly aged, beat both zeroes and a blank screen."""
    times = _times()
    M._last_good["marine:21.62,87.52,3"] = (
        time.time() - 2 * 3600, _marine_payload(times), _LIVE_MARINE
    )

    def handler(url):
        if "marine-api" in url:
            return 429, QUOTA_BODY
        return 200, _weather_payload(times)

    _router(monkeypatch, handler)
    conditions = asyncio.run(M.fetch_marine_conditions(21.62, 87.52))

    assert conditions.hourly[0].wave_height_m == 1.8
    assert conditions.marine_source is not None
    assert conditions.marine_source.live is False
    assert 115 <= conditions.marine_source.age_minutes <= 125
    assert "cached" in conditions.provenance
    assert conditions.degraded


def test_waves_older_than_half_a_day_are_refused(monkeypatch):
    """A forecast fetched yesterday describes a sea that has already happened."""
    times = _times()
    M._last_good["marine:21.62,87.52,3"] = (
        time.time() - 20 * 3600, _marine_payload(times), _LIVE_MARINE
    )

    def handler(url):
        if "marine-api" in url:
            return 429, QUOTA_BODY
        return 200, _weather_payload(times)

    _router(monkeypatch, handler)
    with pytest.raises(M.MarineDataError) as raised:
        asyncio.run(M.fetch_marine_conditions(21.62, 87.52))
    assert "too stale" in str(raised.value)


def test_a_degraded_answer_is_not_short_cached(monkeypatch):
    """So the next question retries the real service instead of being told stale news."""
    times = _times()
    M._last_good["marine:21.62,87.52,3"] = (
        time.time() - 600, _marine_payload(times), _LIVE_MARINE
    )

    def handler(url):
        if "marine-api" in url:
            return 429, QUOTA_BODY
        return 200, _weather_payload(times)

    _router(monkeypatch, handler)
    asyncio.run(M.fetch_marine_conditions(21.62, 87.52))
    assert not M._cache, "a degraded answer must not occupy the fifteen-minute cache"


def test_a_fully_live_answer_is_cached_and_claims_no_degradation(monkeypatch):
    """The ordinary path, unchanged."""
    times = _times()

    def handler(url):
        if "marine-api" in url:
            return 200, _marine_payload(times)
        if "ensemble-api" in url:
            raise AssertionError("the ensemble host must not be touched when the primary answers")
        return 200, _weather_payload(times)

    _router(monkeypatch, handler)
    conditions = asyncio.run(M.fetch_marine_conditions(21.62, 87.52))

    assert not conditions.degraded
    assert conditions.provenance == "Open-Meteo forecast; Open-Meteo Marine"
    assert M._cache, "a clean answer earns the short cache"


def test_a_429_is_not_retried_on_the_same_host(monkeypatch):
    """Hammering a spent quota neither helps nor is polite."""
    times = _times()
    calls: list[str] = []

    def handler(url):
        calls.append(url)
        if "marine-api" in url:
            return 200, _marine_payload(times)
        if "ensemble-api" in url:
            return 200, _weather_payload(times)
        return 429, QUOTA_BODY

    _router(monkeypatch, handler)
    asyncio.run(M.fetch_marine_conditions(21.62, 87.52))

    primary = [u for u in calls if "//api.open-meteo.com" in u]
    assert len(primary) == 1, f"the rate-limited host was asked {len(primary)} times"


def test_the_ensemble_stand_in_is_marked_as_not_the_calibrated_model(monkeypatch):
    """The gust correction must not be applied to a model it was not fitted on.

    ORCA's gust bias was measured against the deterministic forecast. The
    ensemble control run is a coarser model, so a correction measured on one is
    not a correction on the other -- and the flag that says so has to survive
    into whatever reads it.
    """
    times = _times()

    def handler(url):
        if "marine-api" in url:
            return 200, _marine_payload(times)
        if "ensemble-api" in url:
            return 200, _weather_payload(times)
        return 429, QUOTA_BODY

    _router(monkeypatch, handler)
    conditions = asyncio.run(M.fetch_marine_conditions(21.62, 87.52))

    assert conditions.weather_source is not None
    assert conditions.weather_source.calibrated is False
    assert conditions.marine_source.calibrated is True, "the waves came from their usual host"


def test_a_banked_ensemble_response_does_not_later_claim_to_be_the_usual_model(monkeypatch):
    """Served from cache, the stand-in must still admit what it is.

    Rebuilding the note from the store key instead of keeping it would have
    relabelled a cached ensemble response as the deterministic forecast, and the
    gust correction would then have been applied to figures it does not fit.
    """
    times = _times()

    # First call: the primary is rate limited, so the ensemble answers and is banked.
    def ensemble_answers(url):
        if "marine-api" in url:
            return 200, _marine_payload(times)
        if "ensemble-api" in url:
            return 200, _weather_payload(times)
        return 429, QUOTA_BODY

    _router(monkeypatch, ensemble_answers)
    asyncio.run(M.fetch_marine_conditions(21.62, 87.52))
    M._cache.clear()

    # Second call: nothing answers, so the banked copy is served.
    def nothing_answers(url):
        if "marine-api" in url:
            return 200, _marine_payload(times)
        return 429, QUOTA_BODY

    _router(monkeypatch, nothing_answers)
    conditions = asyncio.run(M.fetch_marine_conditions(21.62, 87.52))

    assert conditions.weather_source.live is False
    assert conditions.weather_source.calibrated is False, "still the coarser model"
    assert "ensemble" in conditions.weather_source.label.lower()
