"""ORCA backend — agentic marine intelligence API."""

import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from . import scheduler
from .api import (
    agreement,
    archive,
    chat,
    closures,
    console,
    conditions,
    cyclone,
    evidence,
    geofence,
    location,
    pfz,
    risk,
    route,
    seagrid,
    trends,
    voice,
)
from .config import get_settings
from .tools import geofence as geofence_tool
from .dependencies import get_orchestrator

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Start the daily INCOIS PFZ refresh loop for the life of the server."""
    # Boundary geometry is parsed once here rather than on the first request.
    try:
        logging.getLogger("orca").info("Geofence data: %s", geofence_tool.preload())
    except Exception:  # noqa: BLE001 — the endpoint reports this properly itself
        logging.getLogger("orca").exception("Could not preload geofence data")

    task = scheduler.start(settings)
    try:
        yield
    finally:
        if task is not None:
            task.cancel()


app = FastAPI(
    title="ORCA Core",
    description=(
        "One backend for both ORCA surfaces. An orchestrator plans, specialist "
        "agents gather evidence, and answers come back in the user's own "
        "language with the reasoning attached. The phone app and the web "
        "console read the same numbers from here and differ only in density."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# The protected-area layer is 1.7 MB of MoEFCC polygons and the national sea
# grid is not much smaller. Uncompressed that is a real cost to a fisherman on a
# phone at the edge of coverage, and it is the kind of weight nobody notices on
# a laptop. Text compresses to roughly a quarter.
app.add_middleware(GZipMiddleware, minimum_size=1024)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=settings.cors_origin_regex or None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_router = APIRouter(prefix="/api")

for router in (
    chat.router,
    voice.router,
    location.router,
    pfz.router,
    conditions.router,
    geofence.router,
    risk.router,
    cyclone.router,
    closures.router,
    seagrid.router,
    route.router,
    trends.router,
    agreement.router,
    archive.router,
    evidence.router,
    console.router,
):
    app.include_router(router)
    api_router.include_router(router)

@app.get("/health", tags=["meta"])
@api_router.get("/health", tags=["meta"])
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


app.include_router(api_router)
