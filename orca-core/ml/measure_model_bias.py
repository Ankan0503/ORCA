"""Measure what each forecast model actually gets wrong. See ``docs/ml-plan.md``.

``ml_calibration.py`` carried per-model bias constants commented *"as measured in
orca-core over 1,104 hours at Digha"*, and ``agreement.py`` repeated the figures
in prose. No script in either repository measured them. This is that script, so
the numbers stop being a claim.

Truth is reused from ``forecast_error.parquet`` — the same ERA5 series, already
fetched — so this only has to pull the per-model forecasts.

    python ml/measure_model_bias.py
"""

from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "ml"
CACHE = OUT / "cache"
TRUTH = OUT / "forecast_error.parquet"

URL = "https://historical-forecast-api.open-meteo.com/v1/forecast"
MODELS = ("ecmwf_ifs025", "gfs_seamless", "icon_seamless", "gem_seamless")
VARIABLES = ("wind_speed_10m", "wind_gusts_10m")

START = date(2025, 9, 1)
CHUNK_DAYS = 120
THROTTLE = 2.0

STATIONS: dict[str, tuple[float, float]] = {
    "Digha": (21.6266, 87.5074),
    "Paradip": (20.2644, 86.6947),
    "Visakhapatnam": (17.6868, 83.2185),
    "Chennai": (13.0827, 80.2707),
    "Rameswaram": (9.2880, 79.3130),
    "Kochi": (9.9312, 76.2673),
    "Mangaluru": (12.8698, 74.8430),
    "Veraval": (20.9077, 70.3677),
}


def _fetch(params: dict[str, str]) -> dict:
    full = URL + "?" + "&".join(f"{k}={v}" for k, v in params.items())
    CACHE.mkdir(parents=True, exist_ok=True)
    cached = CACHE / f"{hashlib.sha256(full.encode()).hexdigest()[:24]}.json"
    if cached.exists():
        return json.loads(cached.read_text(encoding="utf-8"))
    time.sleep(THROTTLE)
    try:
        with urllib.request.urlopen(full, timeout=120) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code}: {exc.read().decode('utf-8', 'replace')[:160]}") from exc
    if "error" in payload:
        raise RuntimeError(payload.get("reason", "unknown"))
    cached.write_text(json.dumps(payload), encoding="utf-8")
    return payload


def main() -> int:
    if not TRUTH.exists():
        print("build the dataset first: python ml/build_dataset.py")
        return 1

    truth = pd.read_parquet(TRUTH, columns=["time", "station", "variable", "truth"])
    truth["time"] = pd.to_datetime(truth["time"], utc=True)
    truth = truth[truth.variable.isin(VARIABLES)].drop_duplicates(["time", "station", "variable"])

    today = datetime.now(timezone.utc).date()
    spans, cursor = [], START
    while cursor < today:
        stop = min(cursor + timedelta(days=CHUNK_DAYS - 1), today - timedelta(days=1))
        spans.append((cursor, stop))
        cursor = stop + timedelta(days=1)

    frames = []
    for index, (station, (lat, lon)) in enumerate(STATIONS.items(), start=1):
        print(f"[{index}/{len(STATIONS)}] {station} …", end="", flush=True)
        for start, end in spans:
            payload = _fetch(
                {
                    "latitude": f"{lat}",
                    "longitude": f"{lon}",
                    "start_date": start.isoformat(),
                    "end_date": end.isoformat(),
                    "hourly": ",".join(VARIABLES),
                    "models": ",".join(MODELS),
                    "timezone": "UTC",
                }
            )
            hourly = payload.get("hourly") or {}
            if not hourly.get("time"):
                continue
            frame = pd.DataFrame(hourly)
            frame["time"] = pd.to_datetime(frame["time"], utc=True)
            frame["station"] = station
            frames.append(frame)
        print(" ok")

    wide = pd.concat(frames, ignore_index=True)

    rows = []
    for variable in VARIABLES:
        actual = truth[truth.variable == variable][["time", "station", "truth"]]
        for model in MODELS:
            column = f"{variable}_{model}"
            if column not in wide.columns:
                continue
            part = wide[["time", "station", column]].dropna()
            merged = part.merge(actual, on=["time", "station"], how="inner")
            if merged.empty:
                continue
            merged["error"] = merged[column] - merged["truth"]
            rows.append(
                {
                    "variable": variable,
                    "model": model,
                    "hours": int(len(merged)),
                    # Positive means the model reads high against ERA5.
                    "bias": round(float(merged["error"].mean()), 4),
                    "mae": round(float(merged["error"].abs().mean()), 4),
                    "by_station": {
                        station: round(float(group["error"].mean()), 4)
                        for station, group in merged.groupby("station")
                    },
                }
            )

    frame = pd.DataFrame(rows)
    print("\n=== measured bias against ERA5 (positive = model reads high) ===")
    print(frame[["variable", "model", "hours", "bias", "mae"]].to_string(index=False))

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "model_bias.json").write_text(
        json.dumps(
            {
                "measured_at": datetime.now(timezone.utc).isoformat(),
                "truth": "ERA5 reanalysis via Open-Meteo archive, not in-situ buoy",
                "period": {"start": START.isoformat(), "end": (today - timedelta(days=1)).isoformat()},
                "stations": sorted(STATIONS),
                "note": (
                    "bias = mean(model - truth). Subtract it to de-bias a model's "
                    "forecast. Replaces constants that were previously asserted "
                    "without any script that measured them."
                ),
                "measurements": rows,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nwrote {OUT/'model_bias.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
