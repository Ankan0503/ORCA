# ORCA backend

Agentic marine intelligence API: an orchestrator plans, specialist agents gather
evidence, and answers come back in the user's own language with the reasoning
attached.

## Running it

```bash
cd backend
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt   # Windows
.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000
```

Interactive API docs: <http://127.0.0.1:8000/docs>

Copy `.env.example` to `.env` and fill in `SARVAM_API_KEY` and `GROQ_API_KEY`.
Without a Groq key the API still works — the orchestrator falls back to a
keyword planner and a templated answer, and says so in the reasoning trace.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Liveness plus which providers are configured |
| GET | `/agents` | The specialist registry and what each one handles |
| POST | `/chat` | Ask a question as text; returns answer, evidence and reasoning |
| POST | `/voice/stt` | Speech to text; detects the language itself |
| POST | `/voice/tts` | Text to speech in an Indian language (WAV) |
| POST | `/voice/translate` | Text translation |
| POST | `/voice/ask` | Full voice turn: speak a question, get a spoken answer |

## How it fits together

```
speech ──► Sarvam STT ──┐
                        ├──► ORCHESTRATOR ──► answer ──► Sarvam TTS ──► speech
typing ─────────────────┘         │
                                  ├─ plan     (Groq picks the agents)
                                  ├─ route    (agents run concurrently)
                                  └─ merge    (one answer, in the user's language)
```

Agents are not separate models or separate keys. They share one LLM and differ
by role, allowed tools and scope.

### Language handling

- **Native script** (`আজ সমুদ্র কেমন?`) — identified from the Unicode block:
  deterministic, instant, free.
- **Romanised / code-mixed** (`aaj samudra kaisa hai`) — script says nothing, so
  the UI's selected language is used as a prior. Frequency-based detectors are
  unreliable here.
- **Voice** — Sarvam returns the detected language itself when asked with
  `language_code="unknown"`, so no separate detector is involved.

Answers are **composed directly in the target language**, not translated from
English, which avoids compounding translation error. Domain vocabulary (species,
gear, place names) is pinned in `app/language/glossary.py` so generic
translation cannot mangle the words that matter most.

## Current state

The four specialist agents are **stubs**. Every stub result is flagged
`is_stub: true` and every evidence source is prefixed `STUB:`, so placeholder
numbers can never be mistaken for real observations. `/health` also reports
`"agents": "stub"`.

Next: replace `WeatherIntelligenceAgent` with a real implementation backed by
the Open-Meteo Marine API.

## Verified

- Sarvam translate, TTS and STT round trip: Bengali in, Bengali out, language
  detected at 0.99 confidence, transcript character-identical to the input.
- Groq planning: routes safety questions to weather, PFZ questions to ocean
  analytics, boundary questions to geospatial.
- Graceful degradation when a provider is unavailable, with the reasoning trace
  reporting which path was actually taken.
