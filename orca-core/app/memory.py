"""Conversation memory — what makes "what about the day after?" mean anything.

`session_id` was accepted by the API and thrown away, so every question was a
first question. A user could not refine anything: "and further out?" or "what
about tomorrow instead?" arrived with no idea what "that" referred to, and the
orchestrator answered as if asked from scratch.

This keeps a short rolling transcript per session, plus the last position that
was actually used. Both are handed back to the planner on the next turn, so a
follow-up resolves against what was just discussed.

Deliberately in-process and ephemeral. It is a dict with a time-to-live, not a
database: restarting the server forgets every conversation, and a second worker
would not share them. That is an honest limit of the current deployment rather
than something the API pretends otherwise about — `/chat` reports whether the
turn had memory available, so a caller is never left guessing.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

# How much conversation to carry. Long enough to resolve a chain of follow-ups,
# short enough that the planner is not paying for a whole afternoon of chat.
MAX_TURNS = 12

# Sessions idle longer than this are dropped. A fishing trip's worth of
# conversation, not a permanent record.
TTL_SECONDS = 2 * 3600


@dataclass
class Turn:
    role: str  # "user" | "assistant"
    content: str


@dataclass
class Session:
    turns: list[Turn] = field(default_factory=list)
    # The position the last answer was actually about. A follow-up that names no
    # place should be answered about the same water as the question before it.
    latitude: float | None = None
    longitude: float | None = None
    # The last time window the planner chose, so "and the day after that?" has
    # something to be relative to.
    last_when: str | None = None
    touched_at: float = field(default_factory=time.monotonic)

    def as_messages(self) -> list[dict[str, Any]]:
        return [{"role": t.role, "content": t.content} for t in self.turns]


class ConversationStore:
    """Short-lived per-session memory, keyed by the caller's session_id."""

    def __init__(self, max_turns: int = MAX_TURNS, ttl_seconds: int = TTL_SECONDS) -> None:
        self._sessions: dict[str, Session] = {}
        self._max_turns = max_turns
        self._ttl = ttl_seconds

    def _evict_expired(self) -> None:
        cutoff = time.monotonic() - self._ttl
        for key in [k for k, s in self._sessions.items() if s.touched_at < cutoff]:
            del self._sessions[key]

    def get(self, session_id: str | None) -> Session | None:
        """The session's memory, or None when the caller sent no session_id.

        Returning None rather than an empty session is deliberate: it lets the
        orchestrator report truthfully that this turn had no memory, instead of
        implying an empty conversation history.
        """
        if not session_id:
            return None
        self._evict_expired()
        return self._sessions.get(session_id)

    def remember(
        self,
        session_id: str | None,
        *,
        question: str,
        answer: str,
        latitude: float | None = None,
        longitude: float | None = None,
        last_when: str | None = None,
    ) -> None:
        if not session_id:
            return
        self._evict_expired()

        session = self._sessions.setdefault(session_id, Session())
        session.turns.append(Turn("user", question))
        session.turns.append(Turn("assistant", answer))
        # Keep the tail; the newest exchanges are what a follow-up refers to.
        if len(session.turns) > self._max_turns:
            session.turns = session.turns[-self._max_turns :]

        if latitude is not None:
            session.latitude = latitude
        if longitude is not None:
            session.longitude = longitude
        if last_when:
            session.last_when = last_when
        session.touched_at = time.monotonic()

    def forget(self, session_id: str) -> bool:
        return self._sessions.pop(session_id, None) is not None

    def snapshot(self, session_id: str) -> Session | None:
        """Return a session after applying TTL eviction (read-only view)."""
        self._evict_expired()
        return self._sessions.get(session_id)

    def snapshots(self) -> list[tuple[str, Session]]:
        """Return active sessions for the history compatibility API."""
        self._evict_expired()
        return list(self._sessions.items())

    @property
    def active_sessions(self) -> int:
        self._evict_expired()
        return len(self._sessions)


# One store for the process. Injected via app.dependencies so tests can build
# their own rather than reaching for this.
_store = ConversationStore()


def get_store() -> ConversationStore:
    return _store
