"""Conversational endpoint — the orchestrator's front door."""

from fastapi import APIRouter, Depends

from ..agents.orchestrator import Orchestrator
from ..dependencies import get_orchestrator
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
async def list_agents(orchestrator: Orchestrator = Depends(get_orchestrator)) -> dict:
    """What specialists exist and what each is for."""
    return {"agents": orchestrator.describe_agents()}
