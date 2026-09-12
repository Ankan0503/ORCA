# ORCA ML & RAG — diagnosis and rebuild plan

Written 2026-09-13. This is the working plan; each phase updates it with what was
actually measured, not what was hoped for.

---

## 1. Why the current ML is not usable

`data/models/orca_xgb_risk.json` is byte-identical (MD5 `8986742010…`) to
`HackHeritage/legacy/ml-service/ml/models/orca_xgb_risk.json`. Its own metadata
records why it cannot be trusted:

| Evidence | What it means |
| --- | --- |
| `test_metrics.accuracy: 1.0`, `macro_f1: 1.0` | Nothing real scores 1.0 |
| `label_policy: "Transparent threshold-derived operational proxy labels; not historical incident outcomes"` | The label was computed from each row's wind and wave — and those same columns were fed back as features |
| `feature_importance`: wave 0.52, gust 0.16, wind 0.13 | Exactly the threshold variables, in threshold order |
| Leave-one-station-out accuracy 0.999 on **unseen stations** | It transfers perfectly to new geography because the rule is geography-independent. A real weather model would not |

This is target leakage by construction. The model is a continuous surrogate for the
IMD/Douglas threshold table it was trained on — it cannot know anything the rule does
not already state, and the rule is published, authoritative and free.

`requirements.txt` already records the conclusion: *"XGBoost is absent because the model
it served learned a rulebook it had been handed."* Removing it was correct.

Two related fabrications, to be replaced rather than deleted:

- `app/tools/ml_calibration.py` carries bias constants commented *"as measured in
  orca-core over 1,104 hours at Digha"*. No script, dataset or notebook in either repo
  measured them. `app/tools/agreement.py:5` repeats the same claim.
- The 315,648-row training dataset described in
  `legacy/ml-service/ml/data/processed/dataset_manifest.json` **is not on disk**. Only
  the manifest survives.

## 2. When ML is justified here

The rule this project should hold to:

> **ML earns its place when a mapping exists in the data but not in a rule we already
> hold.**

| Question | ML? | Why |
| --- | --- | --- |
| "Is 30-knot wind dangerous?" | **No** | IMD and Douglas Sea State publish this. Authoritative, explainable, legally meaningful. Learning it returns the same answer, less explainably, and risks drifting off the official threshold. This is the current mistake |
| "Open-Meteo says 1.9 m at Digha in July — what will it actually be?" | **Yes** | Numerical weather models carry systematic biases from coastline, bathymetry and monsoon regime. No rule expresses them. Ground truth exists. This is Model Output Statistics, a real operational discipline |
| "Forecast says 1.9 m, threshold is 2.0 m — am I safe?" | **Yes** | A deterministic number cannot answer it. The conditional error distribution can: *P(wave > 2.0 m) = 31%*. No rule produces this |

The third is the defensible USP. Not "we ran XGBoost" but **"we tell you the probability
the forecast is wrong in the direction that hurts you."**

## 3. Target

Two outputs, both verifiable:

1. **Bias-corrected forecast** — residual `truth − forecast` learned per variable, per
   lead time, per location and season.
2. **Calibrated exceedance probability** — `P(value > statutory threshold)` from the
   conditional residual distribution.

### Non-negotiable honesty rules

- **Baseline first.** Raw forecast MAE and a climatology correction are computed before
  any model. The model ships **only if it beats both** on a chronological holdout.
  If it does not, that is the finding, and it gets written here and the model dropped.
- **Chronological splits only.** Train on the earliest period, test on the latest. No
  random shuffling — that is how the previous model got 1.0.
- **No threshold-derived labels.** The target is a measured residual, never a class
  computed from the features.
- Measured numbers replace every invented constant, and the metadata records the real
  evaluation, including where the model is weak.

### Runtime constraint

Train offline with scikit-learn; **ship a small JSON of coefficients and infer in pure
numpy.** numpy is already a dependency. No xgboost, no sklearn, no torch at runtime —
Render's 512 MB tier stays safe and no new runtime dependency is added.

## 4. Data sources (all verified reachable 2026-09-13)

| Source | Role | Status |
| --- | --- | --- |
| `historical-forecast-api.open-meteo.com/v1/forecast` | archived past forecasts (what was predicted) | HTTP 200 |
| `archive-api.open-meteo.com/v1/archive` | ERA5 reanalysis (what happened — wind) | HTTP 200 |
| `marine-api.open-meteo.com/v1/marine` | wave truth | HTTP 200 |

Open-Meteo counts multi-point requests per coordinate; the archive quota is separate
from the forecast quota that was exhausted on 2026-09-12. Fetches are cached to disk so
the build is resumable and never refetches.

## 5. Phases

Each phase leaves a verifiable artifact and is committed separately.

- **Phase 0 — plan and quarantine.** This document. Disconnect the fabricated evidence
  corpus from retrieval **without deleting it** (see §6).
- **Phase 1 — dataset.** Fetch forecast/truth pairs for the coastal points, 3 years,
  lead times 6/12/24/48 h. Write `data/ml/forecast_error.parquet` + a manifest with real
  row counts and date ranges. Resumable, cached.
- **Phase 2 — baselines and training.** *(done — see §7)* Compute raw-forecast and
  climatology baselines. Fit the residual model. Chronological holdout. Record every
  number.
- **Phase 3 — export and inference.** *(done)* Coefficients to JSON; pure-numpy inference
  module; unit tests against held-out rows.
- **Phase 4 — wiring.** *(done — see LIMITATIONS.md §11-13)* Refuse the leaky model on its own
  metrics; replace the invented calibration constants with measured ones; surface the corrected
  gust and its exceedance probability through the weather agent.
- **Phase 5 — RAG.** *(done — see LIMITATIONS.md §6, §14, §15)* The hybrid layer is real but
  was mislabelled 'Dense Semantic'; it is subword lexical matching and is now named so.
  Eight real sources attempted, three stored, five refused.

## 6. RAG — what is wrong and what happens to it

`data/evidence/corpus.json` and `data/evidence/statutory_marine_corpus.json` hold the
same 14 documents, with IDs such as `INCOIS-OSF-2026-041` and `IMD-MAR-SQ-89`. They
carry every marker of a real fetch — `http_status: 200`, `content_sha256`, `byte_count`,
`fetched_at` — and none of it is true:

- The `fetched_at` timestamps are **70 microseconds apart** across three different
  government servers. Real HTTP fetches cannot do that. They were written in a loop.
- The URLs are generic homepages (`https://www.cmfri.org.in`,
  `https://indiancoastguard.gov.in`) that do not contain the quoted text.
- `app/tools/evidence.py`'s own docstring warns about this exact corpus by name — the
  fourteen paragraphs with convincing identifiers — as the thing the fetch-only rule
  existed to prevent.

**Decision (2026-09-13): nothing is deleted.** The files stay on disk, and the
retrieval path stops drawing on them. They are marked unverified so that if anything
reads them later it cannot mistake them for fetched documents. The provenance fields
that falsely assert a successful fetch are the specific problem, not the text.

A fisherman acting on a fabricated closure date is worse off than one told nothing,
because a confident wrong answer displaces the instinct to go and ask.

---

## 7. Phase 2 result — one variable earned it, two did not

Dataset: 884,376 rows. Chronological split — train 2025-01-01 → 2026-03-31 (599,328),
validation → 2026-06-30 (157,248), test → 2026-09-11 (127,800). Train fits the
coefficients, validation chooses the model shape and decides what ships, test is read
from and nothing more.

Mean MAE across stations on the **test** period, which took no part in any decision:

| variable | lead | raw forecast | global bias | climatology | model |
| --- | --- | --- | --- | --- | --- |
| wind gusts | 1 d | 7.167 | 6.321 | 6.412 | **5.464** |
| wind gusts | 2 d | 7.326 | 6.485 | 6.734 | **5.869** |
| wind gusts | 3 d | 7.491 | 6.687 | 6.987 | **6.059** |
| wind speed | 1 d | **3.001** | 3.387 | 6.161 | 3.317 |
| wave height | 1 d | **0.049** | 0.052 | 0.049 | 0.055 |

### What ships: wind gusts only

21 of 72 groups, all gusts. On the test period the correction takes MAE from 6.184
(best baseline) to 5.778 — **+6.6% on data used for nothing else**, and 24% better than
trusting the raw forecast at one day out. Gusts were under-forecast by about 4.5 km/h
across every station, so most of that error was bias rather than noise, and bias is the
part a correction can remove.

This is also the variable that matters: the IMD fishermen's warning is written against
gusts, so moving the gust estimate moves the answer.

### What does not ship, and why that is the result

- **Wind speed** — validation gain 0.379 km/h, below the 0.5 km/h floor. Test agrees:
  **+0.2%**, which is noise. The raw forecast is already good here and is left alone.
- **Wave height** — validation gain 0.006 m against a 0.05 m floor. Test shows +3.1%,
  but of a 0.107 m baseline: an improvement of three millimetres. Left alone.

Two guards caught this, and both were needed:

1. **Selection on validation, reporting on test.** An earlier run of this script chose
   which groups to keep using the test set and reported test numbers for them — the same
   circularity, in miniature, that produced the 1.0-accuracy model. Fixed before any
   number here was believed.
2. **An absolute floor, not just relative skill.** Validation skill was +14.1% for gusts
   but also +11.4% for wind speed and +6.5% for waves, which survived to +0.2% and +3mm
   on test. Relative skill alone would have shipped all three. The floors are set from
   IMD warning bands (~10 km/h) and INCOIS wave steps (0.5 m), not tuned to the outcome.

The validation-only decision agreed with the test result on all three variables, which
is the check that the gate is measuring something real.

### Honest limits

- Truth is ERA5 reanalysis, not moored-buoy observation. India has no public real-time
  wave buoy feed (`LIMITATIONS.md` §4); OMNI sits behind a data-request portal.
- Wave coverage is ten months, so it spans one monsoon, not several.
- Eight stations. A boat far from all of them gets the nearest station's correction,
  which is an assumption the inference layer must state rather than hide.
