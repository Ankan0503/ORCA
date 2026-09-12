"""Phase 2 — measure baselines, then fit the correction. See ``docs/ml-plan.md``.

The order matters and is not negotiable: baselines are computed first, the model
is fitted second, and it is **kept only where it beats them** on a period it has
never seen. Where it does not, that is written down and nothing is shipped for
that group. A model that cannot beat doing nothing has not earned the right to
sit between a fisherman and a forecast.

Three baselines, each harder than the last:

* **raw** — trust the forecast, correct nothing. Predicts residual = 0.
* **global bias** — one constant per variable, the training-set mean residual.
* **climatology** — a constant per (variable, station, lead, month). This is the
  one that matters: a model that cannot beat a lookup table of monthly averages
  is a lookup table with extra steps, which is precisely the trap the last model
  fell into.

The model itself is a ridge regression per (variable, station, lead) — two
candidate shapes, the simpler one often winning. Deliberately small: its
coefficients ship as JSON and inference is a dot product in numpy, so nothing new
is needed at runtime and the 512 MB host is untouched. It is also legible — a
coefficient can be read and argued with, which a boosted ensemble cannot.

Three separate splits, three separate jobs, and they are not allowed to blur:
**train** fits the coefficients, **validation** chooses the shape and decides what
ships, **test** is only ever read from. Choosing the winner on the rows used to
report it is how a model comes to look better than it is — the subtler cousin of
the leak that invalidated the last one. Splits are chronological throughout;
random splits are how that model scored 1.0.

A variable must also clear an **absolute** gain, not just a relative one. Skill
alone will cheerfully ship a three-millimetre improvement in wave height. The
floors come from the thresholds the answer is graded against, so a correction has
to be worth enough to change what a fisherman is told before it is allowed to
change it.

    python ml/train.py
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "ml" / "forecast_error.parquet"
OUT = ROOT / "data" / "ml"

#: Chronological boundaries. Train on the past, validate on the middle, and
#: report on the most recent stretch, which the fit has never seen.
TRAIN_END = pd.Timestamp("2026-03-31", tz="UTC")
VALID_END = pd.Timestamp("2026-06-30", tz="UTC")

#: Ridge penalty. Small: the design matrix is well conditioned and the point of
#: the penalty is only to stop a thin group (waves have ten months) producing a
#: wild coefficient.
RIDGE_LAMBDA = 1.0

#: A group needs enough history before a fitted correction means anything.
MIN_TRAIN_ROWS = 500

#: How much better than the best baseline a model must be to be worth shipping.
#: One per cent is noise; this asks for a real improvement.
MIN_SKILL = 0.02

#: And how much better in the units a fisherman actually feels. Relative skill
#: alone will happily ship a three-millimetre improvement in wave height.
#:
#: Set from the thresholds the answer is graded against, not tuned to the result:
#: the IMD fishermen's warning bands are about 10 km/h wide (35-45 kmph), so a
#: correction should be worth a meaningful fraction of a band before it is
#: allowed to alter an answer; INCOIS high-wave alerts step in 0.5 m.
MIN_ABSOLUTE_GAIN = {
    "wind_speed_10m": 0.5,   # km/h
    "wind_gusts_10m": 0.5,   # km/h
    "wave_height": 0.05,     # m
}


#: Two candidate shapes, because more features is not automatically better and on
#: this data it is often worse. `linear` corrects an additive and a proportional
#: bias and nothing else. `seasonal` adds annual and daily harmonics, which help
#: where the bias really does turn with the monsoon and overfit where it does not.
#: Which one — or neither — is chosen per group, on validation.
FEATURES: dict[str, list[str]] = {
    "linear": ["intercept", "forecast"],
    "seasonal": ["intercept", "forecast", "sin_year", "cos_year", "sin_day", "cos_day"],
}


def design_matrix(frame: pd.DataFrame, shape: str) -> np.ndarray:
    """Features for the correction.

    The forecast value itself, because bias is usually proportional as well as
    additive — a model that runs 5% low is 0.5 km/h out at 10 and 2 at 40. The
    cycles are harmonics rather than raw numbers, so December sits next to
    January instead of eleven months away.
    """
    forecast = frame["forecast"].to_numpy(dtype=float)
    columns = [np.ones_like(forecast), forecast]
    if shape == "seasonal":
        doy = frame["day_of_year"].to_numpy(dtype=float)
        hour = frame["hour"].to_numpy(dtype=float)
        columns += [
            np.sin(2 * np.pi * doy / 365.25),
            np.cos(2 * np.pi * doy / 365.25),
            np.sin(2 * np.pi * hour / 24.0),
            np.cos(2 * np.pi * hour / 24.0),
        ]
    return np.column_stack(columns)


def fit_ridge(features: np.ndarray, target: np.ndarray, lam: float) -> np.ndarray:
    """Closed-form ridge. The intercept is not penalised."""
    penalty = lam * np.eye(features.shape[1])
    penalty[0, 0] = 0.0
    return np.linalg.solve(features.T @ features + penalty, features.T @ target)


def scores(truth: np.ndarray, predicted_residual: np.ndarray, forecast: np.ndarray) -> dict:
    """Error of the corrected forecast against what actually happened."""
    corrected = forecast + predicted_residual
    error = corrected - truth
    return {
        "mae": float(np.mean(np.abs(error))),
        "rmse": float(np.sqrt(np.mean(error**2))),
        "bias": float(np.mean(error)),
    }


def main() -> int:
    df = pd.read_parquet(DATA)
    df["time"] = pd.to_datetime(df["time"], utc=True)

    train = df[df.time <= TRAIN_END]
    valid = df[(df.time > TRAIN_END) & (df.time <= VALID_END)]
    test = df[df.time > VALID_END]
    print(f"rows  train {len(train):,}  valid {len(valid):,}  test {len(test):,}")
    print(f"train {train.time.min():%Y-%m-%d} → {train.time.max():%Y-%m-%d} | "
          f"test {test.time.min():%Y-%m-%d} → {test.time.max():%Y-%m-%d}\n")

    # --- baseline 2 needs a lookup built from the training period only --------
    climatology = (
        train.groupby(["variable", "station", "lead_days", "month"])["residual"]
        .mean()
        .rename("clim")
    )
    global_bias = train.groupby("variable")["residual"].mean().to_dict()

    models: dict[str, dict] = {}
    report: list[dict] = []

    def baselines(part: pd.DataFrame, variable: str, station: str, lead: int) -> dict[str, dict]:
        truth = part["truth"].to_numpy(dtype=float)
        forecast = part["forecast"].to_numpy(dtype=float)
        lookup = part["month"].map(
            lambda m: climatology.get((variable, station, lead, m), 0.0)
        ).to_numpy(dtype=float)
        return {
            "raw": scores(truth, np.zeros_like(forecast), forecast),
            "global_bias": scores(truth, np.full_like(forecast, global_bias[variable]), forecast),
            "climatology": scores(truth, lookup, forecast),
        }

    for (variable, station, lead), group in train.groupby(["variable", "station", "lead_days"]):
        def slice_of(part: pd.DataFrame) -> pd.DataFrame:
            return part[
                (part.variable == variable) & (part.station == station) & (part.lead_days == lead)
            ]

        tune, held = slice_of(valid), slice_of(test)
        if len(group) < MIN_TRAIN_ROWS or tune.empty or held.empty:
            continue

        target = group["residual"].to_numpy(dtype=float)

        # --- fit every candidate on train, choose between them on validation --
        # The test set takes no part in this decision. Picking the winner on the
        # same rows used to report it is how a model comes to look better than it
        # is, and it is the subtler cousin of the leak that invalidated the last one.
        fitted = {
            shape: fit_ridge(design_matrix(group, shape), target, RIDGE_LAMBDA)
            for shape in FEATURES
        }
        tune_base = baselines(tune, variable, station, lead)
        best_tune_baseline = min(b["mae"] for b in tune_base.values())

        tune_truth = tune["truth"].to_numpy(dtype=float)
        tune_forecast = tune["forecast"].to_numpy(dtype=float)
        tune_mae = {
            shape: scores(tune_truth, design_matrix(tune, shape) @ beta, tune_forecast)["mae"]
            for shape, beta in fitted.items()
        }
        chosen = min(tune_mae, key=tune_mae.get)
        tune_skill = (
            (best_tune_baseline - tune_mae[chosen]) / best_tune_baseline
            if best_tune_baseline
            else 0.0
        )
        keep = tune_skill >= MIN_SKILL

        # --- report on the test period, whatever the decision was -------------
        held_base = baselines(held, variable, station, lead)
        model = scores(
            held["truth"].to_numpy(dtype=float),
            design_matrix(held, chosen) @ fitted[chosen],
            held["forecast"].to_numpy(dtype=float),
        )
        best_test_baseline = min(b["mae"] for b in held_base.values())

        report.append(
            {
                "variable": variable,
                "station": station,
                "lead_days": int(lead),
                "test_rows": int(len(held)),
                "shape": chosen,
                "mae_raw": round(held_base["raw"]["mae"], 4),
                "mae_global_bias": round(held_base["global_bias"]["mae"], 4),
                "mae_climatology": round(held_base["climatology"]["mae"], 4),
                "mae_model": round(model["mae"], 4),
                "valid_skill": round(tune_skill, 4),
                "valid_gain": round(best_tune_baseline - tune_mae[chosen], 4),
                "test_skill": round(
                    (best_test_baseline - model["mae"]) / best_test_baseline
                    if best_test_baseline
                    else 0.0,
                    4,
                ),
                "kept": bool(keep),
            }
        )

        if keep:
            # Residual quantiles *after* correction, measured on validation —
            # rows the coefficients were not fitted on, so the spread is honest.
            # These are what turn a number into "how likely is it worse than the
            # threshold", the one output here a rule cannot produce.
            left = tune["residual"].to_numpy(dtype=float) - (design_matrix(tune, chosen) @ fitted[chosen])
            models[f"{variable}|{station}|{lead}"] = {
                "shape": chosen,
                "feature_names": FEATURES[chosen],
                "coefficients": [float(c) for c in fitted[chosen]],
                "residual_sd": float(np.std(left)),
                "residual_quantiles": {
                    str(q): float(np.quantile(left, q))
                    for q in (0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95)
                },
            }

    frame = pd.DataFrame(report)

    print("=== by variable and lead: mean MAE across stations (lower is better) ===")
    summary = frame.groupby(["variable", "lead_days"])[
        ["mae_raw", "mae_global_bias", "mae_climatology", "mae_model"]
    ].mean().round(4)
    grouped = frame.groupby(["variable", "lead_days"])
    summary["test_skill"] = grouped["test_skill"].mean().round(4)
    summary["kept"] = grouped["kept"].sum().astype(str) + "/" + grouped["kept"].size().astype(str)
    print(summary.to_string())

    # --- variable-level gate, decided on validation --------------------------
    # A handful of groups scraping past the threshold does not make a variable
    # worth correcting. This asks whether the correction helps *on average* for
    # the variable, and it asks validation, so the test numbers below remain a
    # report rather than a choice.
    shipped: set[str] = set()
    print("\n=== which variables are corrected at all (decided on validation) ===")
    for variable, group in frame.groupby("variable"):
        kept_rows = group[group.kept]
        if kept_rows.empty:
            print(f"  {variable:16} left alone     — no group beat its baseline")
            continue
        mean_skill = kept_rows["valid_skill"].mean()
        gain = kept_rows["valid_gain"].mean()
        floor = MIN_ABSOLUTE_GAIN.get(variable, 0.0)
        unit = "m" if variable == "wave_height" else "km/h"
        if mean_skill >= MIN_SKILL and gain >= floor:
            shipped.add(variable)
            print(f"  {variable:16} corrected      skill {mean_skill:+.1%}, "
                  f"gain {gain:.3f} {unit} (floor {floor} {unit})")
        else:
            why = "below the skill floor" if mean_skill < MIN_SKILL else (
                f"gain of {gain:.3f} {unit} is smaller than the {floor} {unit} that would change an answer"
            )
            print(f"  {variable:16} left alone     — {why}")

    print("\n=== verdict by variable ===")
    print("  (kept groups only — selection made on validation, scored on test)\n")
    for variable, group in frame.groupby("variable"):
        kept_rows = group[group.kept]
        total = len(group)
        if kept_rows.empty:
            print(f"  {variable:16}  0/{total} groups  |  DO NOT SHIP — no group beat its baseline")
            continue
        # Honest headline: how the shipped corrections do on rows that took no
        # part in either fitting or selection.
        mae_before = kept_rows[["mae_raw", "mae_global_bias", "mae_climatology"]].min(axis=1).mean()
        mae_after = kept_rows["mae_model"].mean()
        improvement = (mae_before - mae_after) / mae_before if mae_before else 0.0
        verdict = "shipped" if variable in shipped else "not shipped"
        print(
            f"  {variable:16} {len(kept_rows):2}/{total} groups kept  |  "
            f"best baseline {mae_before:.4f} -> model {mae_after:.4f}  |  "
            f"{improvement:+.1%} on unseen data  |  {verdict}"
        )

    models = {key: value for key, value in models.items() if key.split("|")[0] in shipped}

    OUT.mkdir(parents=True, exist_ok=True)
    frame["shipped"] = frame.variable.isin(shipped) & frame.kept
    frame.to_csv(OUT / "evaluation.csv", index=False)
    (OUT / "correction_model.json").write_text(
        json.dumps(
            {
                "trained_at": datetime.now(timezone.utc).isoformat(),
                "kind": "per-group ridge correction of forecast residual",
                "shipped_variables": sorted(shipped),
                "candidate_shapes": FEATURES,
                "ridge_lambda": RIDGE_LAMBDA,
                "min_skill_to_ship": MIN_SKILL,
                "splits": {
                    "train_end": str(TRAIN_END.date()),
                    "valid_end": str(VALID_END.date()),
                    "method": "chronological; no shuffling",
                },
                "target": "residual = truth - forecast (measured, not derived from features)",
                "truth": "ERA5 reanalysis, not in-situ buoy",
                "groups_kept": len(models),
                "groups_evaluated": len(frame),
                "models": models,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nwrote {OUT/'correction_model.json'} — {len(models)} group(s) kept of {len(frame)}")
    print(f"wrote {OUT/'evaluation.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
