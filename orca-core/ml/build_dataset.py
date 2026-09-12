"""Phase 1 — build the forecast-error dataset.

Pairs what Open-Meteo *predicted* against what actually happened, so a model can
learn the forecast's own bias. See ``docs/ml-plan.md``.

The pairing is possible because the archive exposes lead-time variables: for any
hour, ``wind_speed_10m`` is the reanalysis (what happened) and
``wind_speed_10m_previous_day1`` is the forecast for that same hour issued a day
earlier. The residual between them is the target — a measured quantity, never a
class derived from the features, which is precisely what went wrong last time.

Two things this script is careful about:

* **Throttled.** Open-Meteo is free and counts multi-point requests per
  coordinate. One request at a time, with a pause between, well under any limit.
* **Resumable.** Every response is cached to disk by URL. Re-running costs
  nothing and refetches nothing, so an interrupted build simply continues.

Truth here is ERA5 reanalysis, not a moored buoy. Checked against
``archive-api`` over the same hours the two agree to 0.0000 km/h — they are the
same series — so this is the best available truth without buoy telemetry, and it
is a reanalysis, which the metadata records rather than glossing.

    python ml/build_dataset.py              # full build
    python ml/build_dataset.py --dry-run    # show the plan, fetch nothing
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "ml"
CACHE_DIR = OUT_DIR / "cache"

FORECAST_URL = "https://historical-forecast-api.open-meteo.com/v1/forecast"
MARINE_URL = "https://marine-api.open-meteo.com/v1/marine"

#: Seconds between requests. Deliberately generous: this build is not urgent and
#: exhausting the daily quota takes the live map and console down with it.
THROTTLE_SECONDS = 1.5

#: How many days ahead a forecast was issued. The archive offers 1..7; three is
#: where a fisherman's planning actually lives, and each one costs a variable.
LEAD_DAYS = (1, 2, 3)

#: Coverage differs by variable — probed 2026-09-13, recorded rather than assumed.
#: Wind lead-times begin during 2024; waves only from late 2025. Rows outside
#: coverage come back null and are dropped, and the manifest reports what landed.
WIND_START = date(2025, 1, 1)
WAVE_START = date(2025, 11, 1)

#: Requests are chunked so the cache is granular and an interruption loses little.
CHUNK_DAYS = 120


@dataclass(frozen=True)
class Station:
    name: str
    latitude: float
    longitude: float
    coast: str


#: Both coasts, 9°N to 22°N: the monsoon, the cyclone tracks and the shelf
#: bathymetry all differ along it, which is the whole reason a single global bias
#: correction is not good enough.
STATIONS: tuple[Station, ...] = (
    Station("Digha", 21.6266, 87.5074, "north_bay_of_bengal"),
    Station("Paradip", 20.2644, 86.6947, "north_bay_of_bengal"),
    Station("Visakhapatnam", 17.6868, 83.2185, "central_bay_of_bengal"),
    Station("Chennai", 13.0827, 80.2707, "south_bay_of_bengal"),
    Station("Rameswaram", 9.2880, 79.3130, "palk_bay"),
    Station("Kochi", 9.9312, 76.2673, "south_arabian_sea"),
    Station("Mangaluru", 12.8698, 74.8430, "central_arabian_sea"),
    Station("Veraval", 20.9077, 70.3677, "north_arabian_sea"),
)


def _chunks(start: date, end: date, days: int) -> list[tuple[date, date]]:
    spans, cursor = [], start
    while cursor <= end:
        stop = min(cursor + timedelta(days=days - 1), end)
        spans.append((cursor, stop))
        cursor = stop + timedelta(days=1)
    return spans


def _fetch(url: str, params: dict[str, str], throttle: float) -> dict:
    """One request, cached on disk by its full URL.

    A cached response costs nothing and is not re-requested, which is what makes
    the build resumable and keeps a re-run off the provider entirely.
    """
    query = "&".join(f"{k}={v}" for k, v in params.items())
    full = f"{url}?{query}"
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cached = CACHE_DIR / f"{hashlib.sha256(full.encode()).hexdigest()[:24]}.json"

    if cached.exists():
        return json.loads(cached.read_text(encoding="utf-8"))

    time.sleep(throttle)
    try:
        with urllib.request.urlopen(full, timeout=120) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:200]
        raise RuntimeError(f"HTTP {exc.code} from {url}: {detail}") from exc

    if "error" in payload:
        raise RuntimeError(f"{url}: {payload.get('reason')}")

    cached.write_text(json.dumps(payload), encoding="utf-8")
    return payload


def _hourly_frame(payload: dict, station: Station) -> pd.DataFrame:
    hourly = payload.get("hourly") or {}
    if not hourly.get("time"):
        return pd.DataFrame()
    frame = pd.DataFrame(hourly)
    frame["time"] = pd.to_datetime(frame["time"], utc=True)
    frame["station"] = station.name
    return frame


def collect(station: Station, today: date, throttle: float) -> pd.DataFrame:
    """Every forecast/truth pair available for one station."""
    wind_vars = ["wind_speed_10m", "wind_gusts_10m"]
    wind_fields = wind_vars + [
        f"{v}_previous_day{d}" for v in wind_vars for d in LEAD_DAYS
    ]
    wave_fields = ["wave_height"] + [f"wave_height_previous_day{d}" for d in LEAD_DAYS]

    parts: list[pd.DataFrame] = []
    for start, end in _chunks(WIND_START, today - timedelta(days=1), CHUNK_DAYS):
        payload = _fetch(
            FORECAST_URL,
            {
                "latitude": f"{station.latitude}",
                "longitude": f"{station.longitude}",
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "hourly": ",".join(wind_fields),
                "timezone": "UTC",
            },
            throttle,
        )
        parts.append(_hourly_frame(payload, station))

    wind = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()

    parts = []
    for start, end in _chunks(WAVE_START, today - timedelta(days=1), CHUNK_DAYS):
        payload = _fetch(
            MARINE_URL,
            {
                "latitude": f"{station.latitude}",
                "longitude": f"{station.longitude}",
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "hourly": ",".join(wave_fields),
                "timezone": "UTC",
            },
            throttle,
        )
        parts.append(_hourly_frame(payload, station))

    wave = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()

    if wind.empty:
        return pd.DataFrame()
    if wave.empty:
        merged = wind
    else:
        merged = wind.merge(wave.drop(columns=["station"]), on="time", how="left")

    merged["latitude"] = station.latitude
    merged["longitude"] = station.longitude
    merged["coast"] = station.coast
    return merged


def to_long(frame: pd.DataFrame) -> pd.DataFrame:
    """One row per (station, hour, variable, lead) with the residual to learn.

    Long rather than wide because lead time is a feature, not a column: the bias
    at one day out is not the bias at three, and a model that cannot see which it
    is being asked about cannot learn the difference.
    """
    rows: list[pd.DataFrame] = []
    for variable in ("wind_speed_10m", "wind_gusts_10m", "wave_height"):
        if variable not in frame.columns:
            continue
        for lead in LEAD_DAYS:
            column = f"{variable}_previous_day{lead}"
            if column not in frame.columns:
                continue
            piece = frame[["time", "station", "latitude", "longitude", "coast", variable, column]].copy()
            piece = piece.rename(columns={variable: "truth", column: "forecast"})
            piece = piece.dropna(subset=["truth", "forecast"])
            if piece.empty:
                continue
            piece["variable"] = variable
            piece["lead_days"] = lead
            # The target. A measured difference between two observed series —
            # not a class computed from the features it will be predicted from.
            piece["residual"] = piece["truth"] - piece["forecast"]
            rows.append(piece)
    if not rows:
        return pd.DataFrame()

    long = pd.concat(rows, ignore_index=True)
    long["month"] = long["time"].dt.month
    long["hour"] = long["time"].dt.hour
    long["day_of_year"] = long["time"].dt.dayofyear
    return long.sort_values(["station", "variable", "lead_days", "time"]).reset_index(drop=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="show the plan, fetch nothing")
    parser.add_argument("--throttle", type=float, default=THROTTLE_SECONDS)
    args = parser.parse_args()

    today = datetime.now(timezone.utc).date()
    wind_spans = _chunks(WIND_START, today - timedelta(days=1), CHUNK_DAYS)
    wave_spans = _chunks(WAVE_START, today - timedelta(days=1), CHUNK_DAYS)
    requests = len(STATIONS) * (len(wind_spans) + len(wave_spans))

    print(f"stations      : {len(STATIONS)}")
    print(f"wind window   : {WIND_START} to {today - timedelta(days=1)}  ({len(wind_spans)} chunks/station)")
    print(f"wave window   : {WAVE_START} to {today - timedelta(days=1)}  ({len(wave_spans)} chunks/station)")
    print(f"lead times    : {LEAD_DAYS} days")
    print(f"requests      : {requests} (cached ones are free)")
    print(f"throttle      : {args.throttle}s  -> ~{requests * args.throttle / 60:.1f} min worst case")
    if args.dry_run:
        return 0

    frames = []
    for index, station in enumerate(STATIONS, start=1):
        print(f"[{index}/{len(STATIONS)}] {station.name} …", end="", flush=True)
        try:
            wide = collect(station, today, args.throttle)
        except RuntimeError as exc:
            print(f" FAILED: {exc}")
            continue
        long = to_long(wide) if not wide.empty else pd.DataFrame()
        if long.empty:
            print(" no usable rows")
            continue
        frames.append(long)
        print(f" {len(long):,} rows")

    if not frames:
        print("no data collected", file=sys.stderr)
        return 1

    dataset = pd.concat(frames, ignore_index=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    target = OUT_DIR / "forecast_error.parquet"
    dataset.to_parquet(target, index=False)

    coverage = {
        variable: {
            "rows": int(len(group)),
            "start": group["time"].min().isoformat(),
            "end": group["time"].max().isoformat(),
            "stations": sorted(group["station"].unique().tolist()),
            "mean_abs_residual": round(float(group["residual"].abs().mean()), 4),
        }
        for variable, group in dataset.groupby("variable")
    }
    manifest = {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "rows": int(len(dataset)),
        "source": "Open-Meteo historical-forecast-api + marine-api",
        "truth": "ERA5 reanalysis (verified identical to archive-api over the same hours), not in-situ buoy",
        "target": "residual = truth - forecast, per variable per lead time",
        "lead_days": list(LEAD_DAYS),
        "stations": [s.name for s in STATIONS],
        "coverage": coverage,
    }
    (OUT_DIR / "forecast_error_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    print(f"\nwrote {target} — {len(dataset):,} rows")
    for variable, info in coverage.items():
        print(f"  {variable:16} {info['rows']:>8,} rows  {info['start'][:10]} → {info['end'][:10]}  "
              f"mean|residual| {info['mean_abs_residual']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
