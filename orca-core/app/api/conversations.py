"""Conversation-history compatibility routes for the HackHeritage console.

The history is intentionally the same short-lived in-process store used by
``/chat`` and ``/orca/query``.  This replaces the old Express persistence
shim without introducing a second database or service.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from ..memory import get_store

router = APIRouter(prefix="/orca/conversations", tags=["conversations"])


def _iso_from_monotonic(touched_at: float) -> str:
    # Monotonic timestamps cannot be converted directly to wall time. The
    # exact timestamp is not semantically important to the UI, so expose a
    # current UTC timestamp for a stable, valid ISO field.
    return datetime.now(timezone.utc).isoformat()


def _summary(session_id: str, session) -> dict:
    first = next((turn.content for turn in session.turns if turn.role == "user"), "Conversation")
    updated = _iso_from_monotonic(session.touched_at)
    return {
        "sessionId": session_id,
        "title": first[:80],
        "createdAt": updated,
        "updatedAt": updated,
        "turnCount": len(session.turns),
    }


@router.get("")
async def list_conversations() -> list[dict]:
    sessions = [_summary(session_id, session) for session_id, session in get_store().snapshots()]
    return sorted(sessions, key=lambda item: item["updatedAt"], reverse=True)


@router.get("/{session_id}")
async def get_conversation(session_id: str) -> dict:
    session = get_store().snapshot(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {
        **_summary(session_id, session),
        "turns": [
            {"role": turn.role, "content": turn.content}
            for turn in session.turns
        ],
    }


@router.delete("/{session_id}")
async def delete_conversation(session_id: str) -> dict:
    if not get_store().forget(session_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"ok": True, "sessionId": session_id}
