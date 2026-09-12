"""The shipped correction has to earn its place on rows it has never seen.

These are not unit tests of arithmetic. Two of them re-run the claim the model was
accepted on — that it beats the raw forecast on the test period — through the code
that will actually serve it, so a mistake in the inference path cannot hide behind
a good training report.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.tools import forecast_correction as fc

DATA = Path(__file__).resolve().parent.parent / "data" / "ml" / "forecast_error.parquet"

#: Must match ml/train.py. Rows after this took no part in fitting or in any
#: decision about what to ship.
TEST_START = pd.Timestamp("2026-06-30", tz="UTC")


@pytest.fixture(scope="module")
def held_out() -> pd.DataFrame:
    if not DATA.exists():
        pytest.skip("forecast_error.parquet not built")
    frame = pd.read_parquet(DATA)
    frame["time"] = pd.to_datetime(frame["time"], utc=True)
    return frame[frame.time > TEST_START]


def _corrections(rows: pd.DataFrame) -> list[fc.Correction]:
    return [
        fc.correct(
            variable=row.variable,
            forecast=float(row.forecast),
            latitude=float(row.latitude),
            longitude=float(row.longitude),
            lead_days=int(row.lead_days),
            day_of_year=int(row.day_of_year),
            hour=int(row.hour),
        )
        for row in rows.itertuples()
    ]


def test_gust_correction_beats_the_raw_forecast_on_unseen_rows(held_out):
    """The whole justification, checked through the serving path."""
    rows = held_out[held_out.variable == "wind_gusts_10m"].sample(4000, random_state=0)
    results = _corrections(rows)
    applied = [(r, c) for r, c in zip(rows.itertuples(), results) if c.applied]
    assert len(applied) > 1000, "expected most gust rows to have a fitted station"

    truth = np.array([r.truth for r, _ in applied])
    raw = np.array([r.forecast for r, _ in applied])
    corrected = np.array([c.corrected for _, c in applied])

    mae_raw = float(np.mean(np.abs(raw - truth)))
    mae_corrected = float(np.mean(np.abs(corrected - truth)))
    assert mae_corrected < mae_raw, f"correction made it worse: {mae_corrected:.3f} vs {mae_raw:.3f}"
    # Phase 2 measured 24% better than raw at one day out; hold a conservative
    # floor so a regression in the inference path is caught but noise is not.
    assert (mae_raw - mae_corrected) / mae_raw > 0.10


def test_the_bias_is_actually_removed(held_out):
    """Gusts were under-forecast by ~4.5 km/h. The correction should centre that."""
    rows = held_out[held_out.variable == "wind_gusts_10m"].sample(4000, random_state=1)
    applied = [(r, c) for r, c in zip(rows.itertuples(), _corrections(rows)) if c.applied]
    truth = np.array([r.truth for r, _ in applied])
    raw_bias = float(np.mean(truth - np.array([r.forecast for r, _ in applied])))
    corrected_bias = float(np.mean(truth - np.array([c.corrected for _, c in applied])))
    assert raw_bias > 2.0, "expected the raw forecast to under-predict gusts"
    assert abs(corrected_bias) < abs(raw_bias) / 2


@pytest.mark.parametrize("variable", ["wind_speed_10m", "wave_height"])
def test_measured_and_left_alone_variables_are_returned_untouched(variable):
    """Their corrections did not clear the floor, so nothing is applied — and it says so."""
    result = fc.correct(
        variable=variable, forecast=12.0, latitude=21.63, longitude=87.51,
        lead_days=1, day_of_year=200, hour=6,
    )
    assert result.applied is False
    assert result.corrected == result.forecast
    assert "too small" in result.reason
    assert result.exceedance_probability(15.0) is None


def test_far_from_every_station_is_left_alone():
    """A bias measured off Bengal is not the bias in the mid-Indian Ocean."""
    result = fc.correct(
        variable="wind_gusts_10m", forecast=40.0, latitude=-5.0, longitude=70.0,
        lead_days=1, day_of_year=200, hour=6,
    )
    assert result.applied is False
    assert "km away" in result.reason


def test_nearest_station_picks_the_right_coast():
    assert fc.nearest_station(21.63, 87.51)[0] == "Digha"
    assert fc.nearest_station(9.95, 76.25)[0] == "Kochi"
    # Offshore of Chennai, still Chennai.
    name, km = fc.nearest_station(13.0, 81.2)
    assert name == "Chennai" and km < 150


def test_exceedance_probability_is_bounded_and_monotonic():
    result = fc.correct(
        variable="wind_gusts_10m", forecast=34.0, latitude=21.63, longitude=87.51,
        lead_days=1, day_of_year=200, hour=6,
    )
    assert result.applied
    probabilities = [result.exceedance_probability(t) for t in (10, 20, 30, 40, 50, 80)]
    assert all(0.0 <= p <= 1.0 for p in probabilities)
    # A higher bar is harder to clear.
    assert all(a >= b for a, b in zip(probabilities, probabilities[1:]))
    assert probabilities[0] > 0.8 and probabilities[-1] < 0.2


def test_exceedance_probabilities_are_calibrated(held_out):
    """When it says 30%, it should happen about 30% of the time.

    A probability nobody has checked is decoration. This bins predictions and
    compares each bin against how often the threshold was really exceeded.
    """
    rows = held_out[held_out.variable == "wind_gusts_10m"].sample(6000, random_state=2)
    predicted: list[float] = []
    happened: list[bool] = []
    for row, correction in zip(rows.itertuples(), _corrections(rows)):
        if not correction.applied:
            continue
        # A threshold near each row's own forecast, so the probabilities spread
        # across the range instead of piling up at 0 and 1.
        threshold = correction.corrected
        probability = correction.exceedance_probability(threshold)
        if probability is None:
            continue
        predicted.append(probability)
        happened.append(bool(row.truth > threshold))

    assert len(predicted) > 1000
    predicted_arr, happened_arr = np.array(predicted), np.array(happened)
    for low, high in ((0.2, 0.4), (0.4, 0.6), (0.6, 0.8)):
        mask = (predicted_arr >= low) & (predicted_arr < high)
        if mask.sum() < 100:
            continue
        observed = happened_arr[mask].mean()
        expected = predicted_arr[mask].mean()
        assert abs(observed - expected) < 0.15, (
            f"bin {low}-{high}: said {expected:.2f}, happened {observed:.2f}"
        )


def test_missing_model_file_degrades_quietly(monkeypatch, tmp_path):
    """No coefficients is a reason to pass the forecast through, not to fail."""
    monkeypatch.setattr(fc, "MODEL_PATH", tmp_path / "absent.json")
    fc._model.cache_clear()
    try:
        result = fc.correct(
            variable="wind_gusts_10m", forecast=30.0, latitude=21.63, longitude=87.51,
            lead_days=1, day_of_year=100, hour=12,
        )
        assert result.applied is False
        assert result.corrected == 30.0
    finally:
        fc._model.cache_clear()


def test_available_reports_what_is_actually_shipped():
    summary = fc.available()
    assert summary["shipped_variables"] == ["wind_gusts_10m"]
    assert summary["groups"] > 0
    assert "reanalysis" in (summary["truth"] or "")


def test_the_module_works_without_numpy():
    """The deployed host has no numpy, and importing it there took the service down.

    numpy is present locally only as a transitive dependency of the Copernicus
    pipeline, which the live service does not install — so a local test suite
    cannot notice its absence. This blocks the import explicitly and re-runs the
    correction, which must give the same answer it gives with numpy present.
    """
    import builtins
    import importlib
    import sys

    blocked = {"numpy", "pandas", "xarray", "netCDF4", "copernicusmarine"}
    real_import = builtins.__import__

    def guarded(name, *args, **kwargs):
        if name.split(".")[0] in blocked:
            raise ModuleNotFoundError(f"No module named '{name}'")
        return real_import(name, *args, **kwargs)

    saved = {m: sys.modules[m] for m in list(sys.modules) if m.split(".")[0] in blocked}
    for module in saved:
        del sys.modules[module]
    builtins.__import__ = guarded
    try:
        reloaded = importlib.reload(fc)
        result = reloaded.correct(
            variable="wind_gusts_10m", forecast=33.0, latitude=21.63, longitude=87.51,
            lead_days=1, day_of_year=200, hour=6,
        )
        assert result.applied
        assert abs(result.corrected - 36.1) < 0.5
        assert 0.55 < result.exceedance_probability(35.0) < 0.75
    finally:
        builtins.__import__ = real_import
        sys.modules.update(saved)
        importlib.reload(fc)
