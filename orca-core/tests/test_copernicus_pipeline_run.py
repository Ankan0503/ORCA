"""The daily run: it takes the most recent day each product has, and says which day that was."""

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

xr = pytest.importorskip("xarray")
np = pytest.importorskip("numpy")
pytest.importorskip("netCDF4")

from app.tools import copernicus_pfz as pipeline  # noqa: E402

# Two days back, like the real near-real-time lag on OSTIA and ocean colour.
LAG_DAYS = 2


def _write_grid(path, name: str, values: "np.ndarray", day: datetime) -> None:
    lats = np.linspace(20.0, 21.0, values.shape[0])
    lons = np.linspace(87.0, 88.0, values.shape[1])
    da = xr.DataArray(
        values[np.newaxis, :, :],
        coords={"time": [np.datetime64(day.strftime("%Y-%m-%d"))], "latitude": lats, "longitude": lons},
        dims=("time", "latitude", "longitude"),
        name=name,
    )
    da.to_dataset().to_netcdf(path)


def _settings(tmp_path) -> SimpleNamespace:
    return SimpleNamespace(
        copernicus_username="user",
        copernicus_password="secret",
        copernicus_output_dir=str(tmp_path / "raw"),
        copernicus_pfz_output=str(tmp_path / "pfz.json"),
        copernicus_last_clear_output=str(tmp_path / "last_clear.json"),
        copernicus_bbox_min_lon=86.5,
        copernicus_bbox_max_lon=89.5,
        copernicus_bbox_min_lat=20.0,
        copernicus_bbox_max_lat=22.5,
    )


@pytest.fixture
def lagging_client(monkeypatch, tmp_path):
    """A CMEMS that only has data from two days ago, as the real one usually does."""
    raw = tmp_path / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    available = (datetime.now(timezone(timedelta(hours=5, minutes=30))) - timedelta(days=LAG_DAYS)).date()

    class FakeClient:
        def __init__(self, username, password, output_dir):
            self.output_dir = raw

        def _day_or_fail(self, day, name, values):
            if day.date() != available:
                raise RuntimeError("subset selection exceeds the dataset coordinates")
            path = raw / f"{name}_{day:%Y%m%d}.nc"
            _write_grid(path, name, values, day)
            return path

        def fetch_daily_sst(self, day, bbox):
            kelvin = np.full((10, 10), 301.15)
            kelvin[:, 5:] = 302.15  # a one-degree step: the front
            return self._day_or_fail(day, pipeline.VAR_SST, kelvin)

        def fetch_daily_chlorophyll(self, day, bbox):
            return self._day_or_fail(day, pipeline.VAR_CHL, np.full((10, 10), 1.2))

        def fetch_daily_currents(self, day, bbox):
            raise RuntimeError("currents unavailable")

        def fetch_daily_ssha(self, day, bbox):
            raise RuntimeError("sea level unavailable")

    monkeypatch.setattr(pipeline, "CopernicusClient", FakeClient)
    return available


def test_run_uses_the_latest_available_day_and_records_it(lagging_client, tmp_path):
    settings = _settings(tmp_path)

    metadata = asyncio.run(pipeline.run_copernicus_pfz_pipeline(settings))

    assert metadata["points_count"] > 0
    assert metadata["tier"] == "fronts_with_chlorophyll"
    # The run happened today, but the data is from the day the satellite actually saw.
    assert metadata["source_dates"]["SST"] == lagging_client.strftime("%Y-%m-%d")
    assert any("SST (" in s for s in metadata["sources_used"])
    # Nothing came from a cloud-penetrating source here, so the flag stays down.
    assert metadata["cloud_bypass_active"] is False
    assert (tmp_path / "pfz.json").exists()


def test_the_seed_for_cloudy_days_carries_the_observation_date(lagging_client, tmp_path):
    settings = _settings(tmp_path)
    asyncio.run(pipeline.run_copernicus_pfz_pipeline(settings))

    analyzer = pipeline.PFZAnalyzer()
    analyzer.load_last_clear(tmp_path / "last_clear.json")

    assert analyzer.last_clear_fronts
    # Drift is measured from the observation, so a two-day-old front reads as ~48 h.
    hours = analyzer.hours_since_last_clear()
    assert hours == pytest.approx(LAG_DAYS * 24, abs=26)


def test_freshness_is_recorded_so_a_restart_does_not_refetch(lagging_client, tmp_path):
    settings = _settings(tmp_path)
    asyncio.run(pipeline.run_copernicus_pfz_pipeline(settings))
    assert pipeline.output_is_fresh(settings) is True
