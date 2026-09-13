"""Conversational endpoint — the orchestrator's front door."""

from fastapi import APIRouter, Depends, Response

from ..agents.orchestrator import Orchestrator
from ..config import get_settings
from ..dependencies import get_orchestrator
from ..tools import forecast_correction
from ..schemas import ChatRequest, ChatResponse

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    orchestrator: Orchestrator = Depends(get_orchestrator),
) -> ChatResponse:
    result = await orchestrator.handle(
        question=request.message,
        ui_language=request.language,
        known_language=request.known_language,
        latitude=request.latitude,
        longitude=request.longitude,
        session_id=request.session_id,
    )
    return ChatResponse(**result.to_dict())


@router.get("/agents")
async def list_agents(
    response: Response,
    orchestrator: Orchestrator = Depends(get_orchestrator),
) -> dict:
    """Every agent, what it answers, and the sources behind it.

    Served rather than written into a console by hand. The HackHeritage
    diagnostics panel had drifted badly — naming Gemini as the reasoning engine
    when the LLM is Groq, BGE-M3 and Qdrant for retrieval that is BM25, and an
    XGBoost risk engine that is refused at load — because it described what
    someone believed was wired in rather than what is. A panel reading this
    cannot drift again.
    """
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    settings = get_settings()
    described = orchestrator.describe_agents()

    return {
        "count": len(described),
        "agents": [
            {
                "name": agent["name"],
                # "weather_intelligence" -> "Weather Intelligence"
                "title": agent["name"].replace("_", " ").title(),
                "description": agent["description"],
                "sources": agent["sources"],
                "isStub": agent["is_stub"],
            }
            for agent in described
        ],
        "reasoning": {
            "provider": "Groq" if settings.has_groq else None,
            "model": settings.groq_model if settings.has_groq else None,
            "available": settings.has_groq,
            "note": (
                "The planner calls agents as tools and may call again after seeing a "
                "result. Without it a keyword planner selects agents and the reply is "
                "composed from their summaries."
            ),
        },
        "language": {
            "provider": "Sarvam AI" if settings.has_sarvam else None,
            "speechToText": settings.sarvam_stt_model if settings.has_sarvam else None,
            "textToSpeech": settings.sarvam_tts_model if settings.has_sarvam else None,
            "translation": settings.sarvam_translate_model if settings.has_sarvam else None,
            "note": (
                "Questions are pivoted to English so agent selection is reliable, and "
                "answered in the language they were asked in."
            ),
        },
        "machineLearning": forecast_correction.available(),
    }
