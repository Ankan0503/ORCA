"""The Copernicus cloud-bypass pipeline: fronts, drift timing and honest labelling."""

from datetime import datetime, timedelta, timezone

import pytest

xr = pytest.importorskip("xarray")
np = pytest.importorskip("numpy")

from app.tools import copernicus_pfz as pipeline  # noqa: E402
from app.tools.copernicus_pfz import PFZAnalyzer, PFZPoint  # noqa: E402


def _grid(values: "np.ndarray", lats=None, lons=None, lat_name="latitude", lon_name="longitude"):
    lats = np.linspace(20.0, 21.0, values.shape[0]) if lats is None else lats
    lons = np.linspace(87.0, 88.0, values.shape[1]) if lons is None else lons
    return xr.DataArray(values, coords={lat_name: lats, lon_name: lons}, dims=(lat_name, lon_name))


def _step_field() -> "xr.DataArray":
    """A sharp temperature step: one front down the middle of the grid."""
    values = np.full((10, 10), 28.0)
    values[:, 5:] = 29.0
    return _grid(values)


def test_resolve_makes_settings_paths_independent_of_the_working_directory():
    assert pipeline._resolve("data/x.json") == pipeline.ROOT / "data" / "x.json"
    absolute = pipeline.ROOT / "data" / "y.json"
    assert pipeline._resolve(absolute) == absolute


def test_kelvin_is_converted_and_celsius_is_left_alone():
    kelvin = _grid(np.full((3, 3), 300.0))
    assert float(pipeline._to_celsius(kelvin).values[0, 0]) == pytest.approx(26.85, abs=0.01)
    celsius = _grid(np.full((3, 3), 28.0))
    assert float(pipeline._to_celsius(celsius).values[0, 0]) == 28.0


def test_surface_slice_drops_time_and_depth_axes():
    da = xr.DataArray(
        np.zeros((1, 1, 3, 3)),
        coords={"time": [0], "depth": [0.5], "latitude": [1, 2, 3], "longitude": [1, 2, 3]},
        dims=("time", "depth", "latitude", "longitude"),
    )
    assert pipeline._surface_slice(da).dims == ("latitude", "longitude")


def test_coord_names_accepts_either_spelling():
    assert pipeline._coord_names(_grid(np.zeros((2, 2)))) == ("latitude", "longitude")
    short = _grid(np.zeros((2, 2)), lat_name="lat", lon_name="lon")
    assert pipeline._coord_names(short) == ("lat", "lon")


def test_thermal_front_found_on_the_temperature_step():
    points, tier = PFZAnalyzer().combine_pfz_layers(sst_da=_step_field())
    assert points and tier == "thermal_fronts_only"
    assert all(p.source == "thermal_front" and p.confidence == "MEDIUM" for p in points)
    # The front sits at the step, not spread across the whole grid.
    assert {round(p.longitude, 3) for p in points} != {round(float(v), 3) for v in np.linspace(87.0, 88.0, 10)}


def test_chlorophyll_on_a_different_grid_is_interpolated_not_index_matched():
    # A coarser 5x5 chlorophyll grid over the same area: productive except the far west.
    # Index-matching this against the 10x10 SST grid would raise, so reaching the
    # assertions at all is the proof that the two grids were actually aligned.
    chl_values = np.full((5, 5), 1.2)
    chl_values[:, 0] = 0.1
    chl = _grid(chl_values, lats=np.linspace(20.0, 21.0, 5), lons=np.linspace(87.0, 88.0, 5))

    points, tier = PFZAnalyzer().combine_pfz_layers(sst_da=_step_field(), chl_da=chl)

    assert tier == "fronts_with_chlorophyll"
    assert points and all(p.confidence == "HIGH" for p in points)
    assert all(p.chlorophyll_mg_m3 == pytest.approx(1.2) for p in points)


def test_cold_eddies_are_flagged_as_cloud_bypass():
    ssha = _grid(np.where(np.eye(4) > 0, -0.2, 0.01))
    points, tier = PFZAnalyzer().combine_pfz_layers(ssha_da=ssha)
    assert tier == "cloud_bypass_only"
    assert points and all(p.source == "cold_eddy" and p.cloud_bypass for p in points)


def test_no_data_is_said_plainly():
    assert PFZAnalyzer().combine_pfz_layers() == ([], "no_data")


def test_last_clear_round_trip_carries_the_time_it_was_seen(tmp_path):
    analyzer = PFZAnalyzer()
    path = tmp_path / "last_clear.json"
    analyzer.save_last_clear(path, [PFZPoint(latitude=20.5, longitude=87.5, source="thermal_front")])

    loaded = PFZAnalyzer()
    loaded.load_last_clear(path)
    assert len(loaded.last_clear_fronts) == 1
    hours = loaded.hours_since_last_clear(datetime.now(timezone.utc) + timedelta(hours=6))
    assert hours == pytest.approx(6.0, abs=0.1)


def test_a_file_without_a_timestamp_still_loads(tmp_path):
    path = tmp_path / "old.json"
    path.write_text('[{"latitude": 20.5, "longitude": 87.5, "source": "thermal_front"}]', encoding="utf-8")
    analyzer = PFZAnalyzer()
    analyzer.load_last_clear(path)
    assert analyzer.hours_since_last_clear() == 24.0


def test_stale_fronts_are_not_drifted(tmp_path):
    path = tmp_path / "last_clear.json"
    analyzer = PFZAnalyzer()
    analyzer.save_last_clear(path, [PFZPoint(latitude=20.5, longitude=87.5, source="thermal_front")])
    analyzer.load_last_clear(path)
    analyzer.last_clear_saved_at = datetime.now(timezone.utc) - timedelta(hours=pipeline.ADVECTION_MAX_HOURS + 5)

    current = _grid(np.full((4, 4), 0.5))
    points, tier = analyzer.combine_pfz_layers(cur_u_da=current, cur_v_da=current)

    assert points == [] and tier == "no_data"


def test_fronts_drift_east_with_an_eastward_current():
    analyzer = PFZAnalyzer()
    analyzer.last_clear_fronts = [PFZPoint(latitude=20.5, longitude=87.5, source="thermal_front")]
    eastward = _grid(np.full((4, 4), 1.0))  # 1 m/s east
    still = _grid(np.zeros((4, 4)))

    drifted = analyzer.advect_fronts(analyzer.last_clear_fronts, eastward, still, hours_elapsed=1.0)

    assert len(drifted) == 1
    moved = drifted[0]
    assert moved.longitude > 87.5 and moved.latitude == pytest.approx(20.5, abs=1e-6)
    # 1 m/s for an hour is 3.6 km, which at this latitude is about 0.035 degrees.
    assert moved.longitude - 87.5 == pytest.approx(0.0345, abs=0.002)
    assert moved.cloud_bypass and moved.advection_hours == 1.0


def test_output_freshness_checks_todays_date(tmp_path, monkeypatch):
    class FakeSettings:
        copernicus_pfz_output = str(tmp_path / "pfz.json")

    ist_today = datetime.now(timezone(timedelta(hours=5, minutes=30))).strftime("%Y-%m-%d")
    assert pipeline.output_is_fresh(FakeSettings) is False

    (tmp_path / "pfz.json").write_text(
        '{"metadata": {"forecast_date": "' + ist_today + '"}}', encoding="utf-8"
    )
    assert pipeline.output_is_fresh(FakeSettings) is True

    (tmp_path / "pfz.json").write_text('{"metadata": {"forecast_date": "1999-01-01"}}', encoding="utf-8")
    assert pipeline.output_is_fresh(FakeSettings) is False
