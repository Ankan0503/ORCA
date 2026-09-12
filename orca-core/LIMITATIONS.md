# What ORCA does not know

A record of every gap that is currently papered over, approximated, or absent, so nobody has to
rediscover one in a demo. Each entry says what is missing, what is shown instead, and what it would
take to close.

The rule this file exists to protect: **ORCA may be incomplete, but it must not be misleading.** A
layer that is absent is fine. A layer that looks authoritative and is invented is not — the version
of this console that preceded orca-core drew a line labelled *"Designated Fairway Channel, dredged
depth 16 m, channel width 150 m"* from four hardcoded offsets around the boat's own position, and
that is the failure mode every entry below is written to avoid.

Last reviewed: 10 September 2026.

---

## 1. No bathymetry — the big one

**Missing:** depth. ORCA holds no soundings, no chart datum, no shoals, no sandbars, no dredged
channels.

**Consequence:** three things the console can draw are affected.

- The **safe corridor** is a passage computed over the sea grid. It stays in water and routes
  around lightning, and that is *all* it does. It is marked `surveyed: false, bathymetry: "none"`
  in its own properties and its description says "sound your own water". It must never be styled or
  described as a fairway.
- The **precaution zone** is not a shoaling zone. It is ORCA's caution margin around a legal line
  (see §2).
- **Route planning** cannot avoid running a keel aground. It assumes any cell the marine model
  answers for is navigable, which is true of open water and not of an estuary at low tide.

**To close:** GEBCO 2024 global bathymetry is open and gridded at 15 arc-seconds (~450 m), which is
enough to exclude shoal water from routing but *not* enough for pilotage. Indian National
Hydrographic Office charts are the real answer for anything near a harbour and are not freely
redistributable. A realistic first step is GEBCO as a hard "do not route shallower than X" mask,
with the corridor still labelled unsurveyed.

## 2. Caution margins are circular approximations

**Shown:** `precaution_zone` polygons — a 20 km ring around the nearest treaty boundary point and
around the nearest protected-area vertex.

**Approximation, twice over:** the margin around an irregular coastline or treaty line is not
circular, and the ring is generated on a flat lon/lat grid rather than as a geodesic. At 20 km off
the Indian coast the distortion is small relative to the margin itself, which is a caution band and
not a legal limit — the limit is the line, which *is* drawn accurately from Marine Regions v12.

**To close:** a proper geodesic buffer of the line and polygon geometry. `shapely` plus `pyproj`
would do it; both are heavier dependencies than the current tree carries, and the gain is cosmetic
until bathymetry exists.

## 3. No AIS — vessels are empty

**Shown:** `/vessels/live` returns an empty target list with a stated reason.

**Why not filled:** there is no AIS feed behind ORCA. The implementation this replaced returned ten
hardcoded MoES buoy stations relabelled as vessel targets, each with an `mmsi` of
`INCOIS-<station>` and a type of `OCEANOGRAPHIC_BUOY`. A map showing no vessels is correct; a map
showing buoys drawn as vessels is not.

**To close:** AISStream.io (free, websocket, needs an account) or MarineTraffic (paid). Both are
plain integrations once a key exists.

## 4. No buoy stations layer

**Missing:** the console has a `buoy_station` layer and ORCA supplies nothing for it.

**Why:** INCOIS's open ERDDAP carries ARGO floats and gridded satellite products — checked, 17
datasets — and **no moored wave buoys**. The OMNI buoy network sits behind a data-request portal.
The ten coordinates in the previous implementation could not be verified against any live source, so
they were not copied.

**To close:** submit the INCOIS data request for OMNI buoy positions and telemetry. Until then the
layer stays empty rather than plausible.

## 5. Coast Guard dispatch does not dispatch

**Shown:** `/alerts/dispatch` returns `status: NOT_TRANSMITTED` with a message pointing at VHF
Channel 16.

**Why:** ORCA has no link to Coast Guard Command Control. The previous implementation logged a line
to its own console and returned `DISPATCHED`, which is a success status for a message nobody sent.

**To close:** a real integration would need an authorised channel and almost certainly an MoU. This
is a policy gap, not a technical one.

## 6. The evidence corpus holds almost nothing

**Shown:** retrieval works; the corpus is nearly empty, so most rule questions honestly return "no
document in ORCA's collection covers this — ask the harbour authority".

**Why:** a document only enters through a fetch that returned 200, with its status code, byte count
and content hash recorded. Of five real government sources attempted live, one stored and four were
refused — `dof.gov.in` returned 200 with zero extractable text (a JavaScript shell), INCOIS's OSF
page 404'd, the Indian Coast Guard failed certificate verification, and an IndiaCode PDF 404'd.

**To close:** patient, one-at-a-time ingestion of documents that actually resolve — state Marine
Fishing Regulation Acts, MoEFCC protected-area notifications, Coast Guard SOPs. `seed_from_archive`
also fills it from IMD and RSMC bulletins as they accumulate.

## 7. The archive does not survive a redeploy

**Shown:** `/archive/*` works and accumulates while the process lives.

**Why:** the free hosting tier has an ephemeral filesystem. `data/archive.sqlite3` is emptied by a
restart or a deploy.

**To close:** attach a persistent disk (the block is written and commented out in `render.yaml`), or
point `archive_path` at one. Until then, PFZ history cannot build up and §6's archive seeding stays
shallow.

## 8. Deterministic outlook and model answer reconciliation *(resolved)*

**Previous symptom:** the operational directive could read "Good to go — clear for the next 7 h" while the chat
reply said "it is unsafe to go out now". Same data, different conservatism: the outlook counted the
clear hours before the storms, while the model rounded the presence of storms to "don't".

**Resolution:** Resolved in Phase A via `app/tools/decision_gate.py` and orchestrator enforcement:
1. An **Authoritative Decision Gate** extracts the deterministic stance (`PROCEED`, `CAUTION`, or `AVOID`)
   from the statutory bulletins (IMD/INCOIS) and physical marine thresholds before synthesis.
2. The synthesis prompt is injected with non-negotiable instructions requiring strict alignment with the
   computed operational verdict and safe time window.
3. Post-synthesis contradiction verification audits the output text and automatically reconciles direct
   contradictions, logging the enforcement in the `decision_gate` reasoning trace step.

## 9. Satellite observations are days old, by nature

**Shown:** SST and chlorophyll from NOAA CoastWatch, with `observationAgeHours` reported.

**Why:** these are gap-filled composite products, typically around 11 days behind. That is a
property of the source, not a bug, and Oceansat-3 was tested as an alternative and rejected —
measured release lag of at least 12 days, with every recent granule returning
`404 NOT_RELEASED`.

**To close:** nothing available improves on it today. The age is displayed so nobody reads a
week-old field as a nowcast.

## 10. Hazard cells are a forecast, at ~10 km

**Shown:** `hazard_zone` polygons drawn from the sea grid's thunderstorm and rain classification.

**Limits worth stating:** the resolution is the forecast model's, about 10 km, so a cell means
"conditions favour this in this box" rather than "a storm is at this point". Beyond 12 hours the map
should speak to likelihood rather than position; nothing is drawn at all past 48 hours. For actual
storm position inside 3 hours the only real source is IMD Doppler radar, which publishes images
rather than data — and the station covering Digha was serving a frame from May when last checked,
while its HTTP `Last-Modified` header updated every few minutes.

**To close:** radar ingestion, server-side, with a freshness gate that reads the timestamp burned
into the image rather than the HTTP header.

---

## Cross-cutting rule for anyone adding a layer

If a layer cannot be sourced, leave it out and add an entry here. Do not fill it with geometry
derived from the user's own position — a shape that follows the boat around is not a hazard, a
channel, or a zone, however authoritative its label reads.

## 11. The risk model was a rulebook, and is no longer loaded *(resolved)*

**Previous symptom:** `data/models/orca_xgb_risk.json` shipped as the "ML risk engine". Its own
metadata reports test accuracy `1.0`, macro F1 `1.0`, and `0.999` on stations held out of training
entirely.

**Why:** target leakage by construction. `label_policy` records it plainly — *"threshold-derived
operational proxy labels"*. The label was computed from each row's wind and wave, and those same
columns were then given back as features, so the model re-learned the IMD/Douglas threshold table
it had been handed. That table is published, authoritative and free; a surrogate for it can only be
less explainable and occasionally wrong.

**Resolution:** the model is refused at load, on its own recorded metrics rather than on a missing
dependency — it was previously inert only because xgboost was not installed, one `pip install` away
from silently driving safety verdicts again. The file is kept. Risk verdicts come from the
deterministic Douglas Sea State path, which is what was actually running all along.

## 12. What the ML does now, and what it does not

**Shown:** gust forecasts carry a bias-corrected figure and `P(gusts exceed 55 km/h)`.

**Why this and not risk classification:** ML earns its place where a mapping exists in data but not
in a rule already held. "Is 30 knots dangerous" is a published rule. "What does Open-Meteo get wrong
at Rameswaram in July" is not, and is measurable. See `docs/ml-plan.md`.

Measured on a chronological test period that took part in no decision: gust MAE 7.349 -> 5.778
(+21.4%), and a +3.9 km/h under-forecast bias reduced to +0.04.

**What it does not do.** Wind speed and wave height are **not** corrected. Their corrections were
measured and did not clear the floor that would change an answer — wind speed gained 0.379 km/h
against a 0.5 km/h floor, waves 0.006 m against 0.05 m. Both return the raw forecast and say so.

**Honest limits:**
- Truth is ERA5 reanalysis, not moored-buoy observation (see §4 — India has no public real-time
  wave buoy feed).
- Eight stations. Beyond 400 km from all of them no correction is applied, and the distance is
  reported rather than hidden.
- The exceedance probabilities are mildly overconfident: binned against observed frequency they say
  54% where 47% occurs.
- Wave coverage in the training data is ten months, so it spans one monsoon rather than several.

## 13. Per-model bias figures were asserted, and are now measured *(resolved)*

**Previous symptom:** `ml_calibration.py` carried per-model bias constants commented *"as measured
in orca-core over 1,104 hours at Digha"*, and `agreement.py` repeated them in prose. No script in
either repository measured anything.

**Why it mattered:** for gusts the invented constants had the wrong sign on three of four models —
GFS was asserted at +4.2 km/h and measures -5.97 — so subtracting them pushed gust forecasts about
10 km/h the wrong way, on the one variable IMD's fishermen's warning is written against.

**Resolution:** `ml/measure_model_bias.py` measures them over 72,192 hours at eight stations against
ERA5, and `data/ml/model_bias.json` is loaded at runtime. When that file is absent the fallback is
zeros, not the old numbers: correcting by a figure nobody measured is worse than not correcting.
