# 🌊 ORCA — Ocean Risk & Conditions Advisory

![FastAPI](https://img.shields.io/badge/FastAPI-orca--core-009688?style=for-the-badge&logo=fastapi&logoColor=ffffff)
![React](https://img.shields.io/badge/React-19-61dafb?style=for-the-badge&logo=react&logoColor=111827)
![Capacitor](https://img.shields.io/badge/Capacitor-Android-119eff?style=for-the-badge&logo=capacitor&logoColor=ffffff)
![ESP32](https://img.shields.io/badge/ESP32-Xponder-e7352c?style=for-the-badge&logo=espressif&logoColor=ffffff)
![Leaflet](https://img.shields.io/badge/Leaflet-maps-199900?style=for-the-badge&logo=leaflet&logoColor=ffffff)

> **Smart India Hackathon 2026 — PS176**
> **Team Samudra Dristhi** · Heritage Institute of Technology, Kolkata

A marine advisory console for small fishing boats in the Bay of Bengal. It
answers the questions that decide whether a crew goes out: what the sea will do,
where the fish are likely to be, where the boat is not allowed, and when to turn
back.

**Live:** [marine-orca.vercel.app](https://marine-orca.vercel.app)

## What it does

| | |
| --- | --- |
| **Sea state** | Wind, wave and weather on a time-stepped grid — hourly to 12 hours, three-hourly to 48, with probability shading past 12 and no spatial claim past 48 |
| **Cyclone watch** | IMD and RSMC bulletin parsing, track points, severity |
| **Fishing zones** | INCOIS potential-fishing-zone advisories, plus a Copernicus-derived PFZ path |
| **Boundaries** | Point-in-polygon geofencing against India's mainland and Andaman EEZ and protected areas |
| **Routing** | Passage planning that stays in water and routes around hazards |
| **Risk** | Calibrated risk scoring across sources |
| **Agreement** | Flags when forecast models disagree enough to change the advice |
| **Evidence** | BM25 retrieval over ingested advisories — what is prohibited inside a boundary, and until when |
| **Archive** | Keeps what the scrapers already fetch, so history exists to answer "what did IMD say last week" |
| **Voice & IVR** | Spoken advisories and phone access for crews without a smartphone |

Everything is served in the fisherman's own language through a Sarvam language
edge: detection, a marine glossary, and localisation.

## The transponder

`firmware/esp32_xponder` stands in for the S-band MSS terminal ISRO is fitting
to fishing vessels under **Nabhmitra**. The satellite hop is not simulated; the
terminal-to-phone link is, and that link is real on the device too.

What it demonstrates is the payload. A satellite message to a boat is tens of
bytes, not kilobytes, so **no sentence is ever transmitted**. One frame is
**20 bytes**: a magic byte, a version, a message type, a severity, and a
latitude and longitude as `int32` degrees × 1e5. The phone renders and speaks
the warning in the crew's own language from the type code alone.

| offset | size | field |
| --- | --- | --- |
| 0 | 1 | magic `0xA5` |
| 1 | 1 | version `0x01` |
| 2 | 1 | type — `1` cyclone, `2` lightning, `4` track point, `0x10` SOS, `0x11` SOS received |
| 3 | 1 | severity |
| 4 | 4 | latitude, int32, degrees × 1e5 |
| 8 | 4 | longitude, int32, degrees × 1e5 |

`firmware/esp32_xponder` and `frontend/src/services/xponder/frame.ts` implement
the same layout, and the phone pairs to the terminal over Bluetooth LE.

## Architecture

```text
   INCOIS · IMD · RSMC · Open-Meteo · NOAA CoastWatch · ERA5 · Copernicus
                                  │
                                  ▼
            ┌──────────────── orca-core (FastAPI) ────────────────┐
            │  orchestrator → plans, replans, runs a dependsOn    │
            │  DAG with deterministic recovery when an agent      │
            │  fails — no extra model call                        │
            │                                                     │
            │  agents: weather · cyclone · ocean · geospatial ·    │
            │  risk · route · trends · visualization · reporting · │
            │  evidence retrieval                                  │
            │                                                     │
            │  guardrails · timeframe · discovery · execution      │
            │  archive · memory · scheduler · Sarvam language edge │
            └─────────────────────────────────────────────────────┘
                     │                              │
                     ▼                              ▼
          Web console (React + Leaflet)    Android app (Capacitor)
                                                    │
                                                    ▼  Bluetooth LE
                                            ESP32 Xponder (20-byte frames)
```

Retrieval is **one agent among ten**, selected by the same planner as the rest —
not a layer everything is routed through. Asking for the wave height at Digha
returns a number, not a document search.

## Repository layout

```text
.
├── orca-core/        FastAPI service — agents, tools, API routes, providers, language
│   ├── app/
│   │   ├── agents/   orchestrator, weather, cyclone, ocean, geospatial, risk, route,
│   │   │             trends, visualization, reporting, evidence, execution, guardrails
│   │   ├── tools/    seagrid, marine, ocean, pfz, copernicus_pfz, cyclone, geofence,
│   │   │             routing, vessels, oil_spill, satellite_zones, closures, evidence,
│   │   │             agreement, fusion, ml_risk, ml_calibration, forecast_correction
│   │   ├── api/      seagrid, conditions, risk, route, cyclone, pfz, geofence, evidence,
│   │   │             archive, chat, conversations, console, voice, ivr, trends, location
│   │   ├── language/ detect, glossary, localise
│   │   └── providers/ llm, sarvam
│   ├── data/geo/     EEZ, coastline and protected-area geometry
│   └── tests/
├── frontend/         React 19 + Vite + Leaflet console, wrapped for Android via Capacitor
│   └── android/
├── firmware/
│   └── esp32_xponder/  Simulated Nabhmitra S-band terminal
├── extras/           India mainland and Andaman EEZ geometry, WKT and GeoJSON
├── docs/             Architecture diagram and backlog
└── HackHeritage/     Earlier project whose executor and planner were ported into orca-core
```

## Technology

| Layer | Tools |
| --- | --- |
| Service | FastAPI, Uvicorn, Python 3.12, pytest |
| Agents | Custom orchestrator with a `dependsOn` task graph and deterministic replanning |
| Geo | Point-in-polygon geofencing over EEZ and protected-area polygons, Leaflet on the client |
| Retrieval | BM25 over verified-ingested advisories |
| Language | Sarvam for Indic detection, glossary and localisation |
| Web | React 19, TypeScript 5.8, Vite 6, Tailwind CSS 4, Leaflet, Motion, lucide-react |
| Mobile | Capacitor 8 for Android, Bluetooth LE for transponder pairing |
| Firmware | ESP32, Arduino IDE |
| Hosting | Vercel for the console, Render for orca-core |

## Running it

```bash
cd orca-core
python -m venv .venv && .venv/Scripts/activate     # source .venv/bin/activate on macOS/Linux
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

The console:

```bash
cd frontend
npm install
npm run dev                                         # http://localhost:3000
```

## Team Samudra Dristhi

Heritage Institute of Technology, Kolkata.

| Member | GitHub |
| --- | --- |
| Ankan Giri | [@Ankan0503](https://github.com/Ankan0503) |
| Sayan Sinha | [@Sayan260106](https://github.com/Sayan260106) |
| Raunak | [@raunak095](https://github.com/raunak095) |
| Rupkatha Ghosh | [@Rupkatha-Ghosh](https://github.com/Rupkatha-Ghosh) |
| Swarnavo Sen | [@swarnavosen10-byte](https://github.com/swarnavosen10-byte) |
| Shrabani Neogi | [@shrabani-stack](https://github.com/shrabani-stack) |

## Licence

MIT — see [LICENSE](LICENSE).
