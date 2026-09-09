# orca-core

One FastAPI backend for both ORCA surfaces — the Android app and the web console — merging what is
worth keeping from the ORCA backend and from HackHeritage.

**Nothing outside this folder is modified.** `backend/` and `HackHeritage/` keep running exactly as
they did. This service listens on **8100**, clear of `backend/` on 8000 and HackHeritage on 3001
(plus its Python services on 8000/8001). The cut-over happens in Phase 5, once there is something
demonstrably better to cut over to.

---

## Why FastAPI and not Express

Measured across both projects:

| | Python | TypeScript |
|---|---|---|
| ORCA `backend/` | 10,775 lines (59 files) | — |
| HackHeritage `ml/` | 17,779 lines | — |
| HackHeritage `server/` | — | 6,103 lines |

About 82% of the combined backend logic is already Python, and several parts cannot be ported to
Node at all: `pypdf` bulletin parsing, the ERA5 and ERDDAP numeric work, point-in-polygon over the
EEZ and 121 protected-area polygons. HackHeritage's Express layer is not a gateway — it is
coordination logic over two Python services — and coordination logic ports cleanly.

Choosing FastAPI also collapses four processes (Express, Vite, and two Python services) into one,
which on a free hosting tier is the difference between one cold start and four.

There is **no Express gateway in front of this**. Vercel's rewrite already gives a single entry
point, both platforms terminate TLS, FastAPI handles CORS and middleware natively, and there is only
one backend to route to. A gateway would add a hop, a second runtime and a second deploy for no
routing gain.

---

## Phases

Each phase leaves the service running and useful. Nothing is half-wired at a phase boundary.

### Phase 0 — Skeleton *(done)*

The service exists, starts, and answers `/health`. Configuration names the archive and corpus paths
that later phases fill in.

### Phase 1 — The proven foundation *(done)*

ORCA's agents, tools, API routes, providers and language handling copied in whole — 10,568 lines
across 56 files, plus the EEZ, boundary and protected-area geometry and the existing tests. Copied
rather than imported, deliberately: a shared import would mean a change here could break `backend/`,
and both must keep running.

What came across: nine agents plus the orchestrator, INCOIS PFZ scraping, IMD and RSMC bulletin
parsing, Open-Meteo marine and forecast, NOAA CoastWatch, ERA5 history, EEZ and protected-area
geofencing, routing, the Sarvam language edge, and multi-turn session memory.

### Phase 2 — Fix the map hazard layer *(done)*

The four defects recorded in `docs/orca-backlog.md`, all reproduced against live data:

- coastal cells are deleted, because a cell counts as sea only if the ocean-current model answers
  for it — 29 raining cells discarded in a single measurement at Digha;
- drizzle below 0.5 mm/h renders as clear even when the weather code says it is drizzling;
- the map reads `hourly[0]`, which is midnight rather than the current hour;
- the grid samples an 11 km model at 42 km spacing.

Then the time dimension: a 48-hour series with hourly steps to 12 hours and three-hourly beyond,
probability shading past 12 hours, and no spatial claim at all past 48.

### Phase 3 — Deterministic execution, from HackHeritage *(done)*

ORCA's orchestrator already replans across rounds and runs a round's tool calls through
`asyncio.gather`. What it lacks is an explicit `dependsOn` DAG and **deterministic** recovery when an
agent fails — recovery that costs no extra model call, which matters when Groq is rate-limited or
down. That is what `agenticExecutor.ts` and `agenticPlanner.ts` contribute, ported to Python as
application logic.

`sourceComparison.ts` came across in the same pass, in `app/tools/agreement.py` and the
`/agreement` route — but with its rule corrected. It flagged disagreement above 25% relative spread
for every variable at every magnitude, which on live data called a flat calm at Digha (four models
between 0.7 and 5.9 km/h) a 173% disagreement. The percentage is now anchored to the published
limits: a difference is reported when the models straddle a line where the advice changes, or when
at least one of them has reached halfway to that line. Both rules use the figures the weather agent
already cites to the user, so the two cannot drift apart.

What shipped: `app/agents/execution.py` (task graph, wave runner, deterministic replanning),
`app/tools/agreement.py` and `app/api/agreement.py`, and 25 tests covering the failure paths.

### Phase 4 — The archive *(done)*

A file-backed store written by the scrapers that already run. ORCA keeps nothing between days, which
is why there is no PFZ history to learn from and no way to answer "what did IMD say last week". No
new fetching — just keeping what already arrives.

`app/archive.py`, hooked into the INCOIS advisory and RSMC bulletin scrapers, read back through
`/archive/stats`, `/archive/history` and `/archive/export`.

Three decisions worth knowing:

**Records are filed under the day they describe, not the day they were collected.** INCOIS publishes
in the afternoon *for the following day*, so filing by fetch date would shift every row by one and
corrupt any dataset built from it later — which is exactly how an earlier trend feature in this
project produced a fabricated result that looked entirely plausible. `_iso_forecast_date` converts
INCOIS's `"9 SEP 2026"` to `2026-09-09`, and returns `None` rather than guessing when the source
states no date, so an undated record falls back to the collection date with the ambiguity visible.

**An empty advisory is stored as an observation, not skipped.** INCOIS answering and issuing nothing
for a sector is a fact; a missing row cannot express it, and a model learning where fishing grounds
appear needs the days they did not.

**The payload has its own schema, versioned, rather than calling the API's `to_dict()`.** That method
serves the frontend and is free to change with it; if history mirrored it, renaming a key for the UI
would silently change what older rows mean.

**On the current host this file does not survive a restart or a redeploy.** Render's free plan has an
ephemeral filesystem. The archive still accumulates while the process lives and works fully on any
host with a persistent disk — but to build a real dataset, attach a disk and point `archive_path` at
it, or export before a deploy. Nothing here fails a request if the disk is unusable: every write
swallows its own errors by design.

### Phase 5 — Retrieval as the tenth agent *(done)*

`evidence_retrieval` sits in the agent catalogue beside `weather_intelligence` and `cyclone_watch`,
selected by the same planner. The orchestrator did **not** become retrieval-shaped: it decides what
to do, and retrieval is one of the things it can do. Routing everything through it would mean asking
for the wave height at Digha performs a document search to answer a number.

This answers a question class ORCA could not touch: the geofence knows *where* a boundary is, but
nothing knew what is prohibited inside it or until when.

`app/tools/evidence.py` (BM25 + verified ingestion), `app/agents/evidence.py`, `/evidence/search`,
`/evidence/ingest`, `/evidence/seed-from-archive`.

**A document cannot enter the corpus without a fetch that returned 200.** `ingest_url` records the
status code, byte count and a SHA-256 of the content, and refuses a 404, an unreachable host, or a
body too short to be a document. There is no code path that accepts typed-in text. That is
structural rather than a convention, because the failure it prevents is not hypothetical — attempting
five real government sources live, **one stored and four were refused**: `dof.gov.in` returned 200
with zero extractable text (a JavaScript shell), INCOIS's OSF page 404'd, the Indian Coast Guard
failed certificate verification, and an IndiaCode PDF path 404'd. Four plausible citations that do
not resolve, from one afternoon's guessing.

`ingest_text` is the one route that does not fetch, for bulletin prose ORCA's own scrapers already
retrieved. It records no content hash and reports `verified = False`: the document is real, but this
module did not witness it arriving, and that difference stays visible rather than being assumed away.

**Retrieval is BM25, not embeddings.** BGE-M3 is ~2.2 GB at fp32 against 512 MB on the current host;
that is not a tuning problem. At a few hundred real passages the quality gap is far smaller than the
gap between real documents and invented ones. HackHeritage's scorer also added a fixed +0.45 for each
of a list of phrases — "gahirmatha", "trawl ban", "signal 3" — which fits the ranking to the fourteen
documents it shipped with and mis-ranks everything added afterwards; a test here asserts no such
bonus exists.

**The corpus is deliberately small and honest.** `seed_from_archive` turns the bulletins Phase 4 now
keeps into retrievable documents, so it grows as real bulletins arrive. Regulatory documents — state
Marine Fishing Regulation Acts, protected-area notifications, Coast Guard procedures — still have to
be ingested by URL, and only ones that actually resolve are stored. When the corpus holds nothing
relevant the agent says so and points at the harbour authority, because silence here is explicitly
not permission.

### Phase 6 — Cut over *(prepared, not thrown)*

Everything needed to switch is in place, and nothing has switched. The app and the console still
talk to `orca-backend` exactly as before.

**The contract audit is what makes this safe.** Both services were run side by side — the original on
8000, this one on 8100 — and every GET the frontend makes was requested from both and compared by
response shape rather than by value, since wave heights differ between two calls a second apart:

```
15 endpoints checked
 0  breaking differences
 3  additive only
12  identical
```

The three additive ones are `/conditions` (gains `safety.outlook`), `/seagrid` (gains `series`,
`worstAhead`, `stepKm`, `counts.rainAhead`) and `/pfz/lines`. No key the frontend reads is missing
anywhere, which is the property that decides whether a screen breaks.

`/route` returned 404 on **both**, with the same body: *"INCOIS issued no fishing zones for West
Bengal today, so there is nowhere to plan a route to."* That is correct behaviour, not a regression —
worth writing down, because a status-code-only audit would have flagged it as a failure on both and
a shape-only audit would have skipped it.

**What changed outside this folder:** one line of frontend behaviour. The development API port was
hardcoded to 8000 in two places, so trying this service meant editing `orcaApi.ts` and remembering
to change it back. It now reads `VITE_API_PORT`, **defaulting to 8000** — a build that sets nothing
behaves exactly as it did.

**To throw the switch**

```bash
# locally, against orca-core on 8100
VITE_API_PORT=8100 npm run dev

# a deployed build, against a deployed orca-core
VITE_API_BASE_URL=https://orca-core-xxxx.onrender.com
```

For Vercel, repoint the `/api/:path*` rewrite in the root `vercel.json`. For the packaged Android
app, `HOSTED_API_BASE` in `orcaApi.ts` is the value to change — it is hardcoded rather than read from
the environment because a missing variable at build time gives an APK that silently reaches nothing,
on a device with no console.

`render.yaml` in this folder is the deployment blueprint. It is **not** at the repository root on
purpose: Render auto-applies a root blueprint, and the existing `orca-backend` was created through
the dashboard, so a root file could try to reconcile — and reconfigure — the service the app is
currently pointed at.

**Run both until this one has been watched under real use.** A cut-over worth doing is one that can
be reversed by changing a single variable back.

---

## Retiring `backend/`

`orca-core` is the successor to `backend/`, not a permanent parallel. When it is retired, the order
matters, because getting it wrong takes the live API down.

Render's build configuration lives in its dashboard, not in this repository — it currently runs
`pip install -r backend/requirements.txt` and `cd backend && uvicorn app.main:app`. **Delete the
folder before repointing that service and the next deploy fails with no files to build.** The root
`vercel.json` points at the Render *URL* rather than the folder, so it survives the deletion; the
service behind it does not.

1. Deploy `orca-core` as its own Render service — `render.yaml` in this folder is the blueprint.
2. Verify `/health`, then re-run the contract audit against the deployed pair rather than the local
   one. A route that agrees on localhost can still differ behind a proxy.
3. Repoint `vercel.json`'s `/api/:path*` rewrite, and `HOSTED_API_BASE` in `frontend/src/services/orcaApi.ts`
   for the packaged Android app.
4. Watch it under real use. Both services can run at once, and that is the point of a cut-over that
   can be reversed.
5. Only then remove `backend/`.

**A note on history.** These two trees are near-identical — 47 of 56 Python files are byte-for-byte
the same — and git will report them as renames when asked directly. But rename detection only works
within a single commit's diff, and `orca-core` was added in its own commits. So once `backend/` is
deleted, `git log --follow` on a file here will stop at the day it was created rather than
continuing into the original's history.

Nothing is lost: the full history of that code remains reachable at its old path, for example
`git log -- backend/app/tools/pfz.py`, and stays reachable forever. This is written down because the
alternative — discovering it while trying to find out why a threshold was chosen — is a bad moment
to learn it.

---

## Running it

```bash
cd orca-core
python -m venv .venv && .venv/Scripts/activate     # Windows
pip install -r requirements.txt
cp .env.example .env                                # then fill in the keys
uvicorn app.main:app --reload --port 8100
```

Check it is alive:

```bash
curl http://localhost:8100/health
```

Tests:

```bash
pytest -q
```

---

## What was deliberately left behind

**The XGBoost risk model.** It learned a rulebook it had been handed: `label_policy.py` defines the
thresholds, `prepare_dataset.py` applies that function to each row's own wind and wave to make the
label, and those same columns are then fed back as features. There is no time shift anywhere —
`RISK_HORIZON_HOURS = 6` is declared and never used — so the target is a deterministic function of
the inputs at the same timestamp, and near-perfect accuracy is arithmetic rather than skill. Its
metadata also records training on NOAA NDBC data, which is US buoys, while the configuration lists
Indian coastal locations. `app/agents/weather.py` already applies the same thresholds, sourced to the
IMD bulletin and citable.

Machine learning earns a place here when it has something real to learn. The candidates, in order:
predicting forecast *error* from inter-model spread (four models disagree by up to 5 km/h in the mean
at Digha, and the app currently shows one number with no uncertainty at all), and calibrating
ensemble probabilities. Both are recorded in `docs/orca-backlog.md` with the measurements.

**The Express layer**, for the reasons above.

**BGE-M3 and Qdrant**, for memory reasons — see the note in `requirements.txt`.
