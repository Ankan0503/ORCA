"""ORCA backend — agentic marine intelligence API."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import chat, voice
from .config import get_settings
from .dependencies import get_orchestrator

settings = get_settings()

app = FastAPI(
    title="ORCA Marine Intelligence API",
    description=(
        "Agentic marine decision support: an orchestrator plans, specialist "
        "agents gather evidence, and answers are returned in the user's own "
        "language with the reasoning attached."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(voice.router)


@app.get("/health", tags=["meta"])
async def health() -> dict:
    """Liveness plus which providers are actually configured."""
    return {
        "status": "ok",
        "providers": {
            "sarvam": settings.has_sarvam,
            "groq": settings.has_groq,
        },
        # Says out loud which agents are still placeholder-backed, so nobody
        # mistakes stub numbers for real observations.
        "agents": {
            "real": [a["name"] for a in get_orchestrator().describe_agents() if not a["is_stub"]],
            "stub": [a["name"] for a in get_orchestrator().describe_agents() if a["is_stub"]],
        },
    }
