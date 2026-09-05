"""The contract every specialist agent implements.

An agent is not a separate model or a separate API key. All agents share one
LLM. What makes them distinct is a role, a set of tools they are allowed to
use, and a narrow scope.

The important part of this contract is `Evidence`. Agents never return a bare
opinion — they return the observations they based it on, with the source
named. That is what lets ORCA explain *why* it said something instead of
asking the user to trust it.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Evidence:
    """One observation, traceable back to where it came from."""

    source: str
    label: str
    value: str
    unit: str | None = None
    observed_at: str | None = None
    note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "label": self.label,
            "value": self.value,
            "unit": self.unit,
            "observed_at": self.observed_at,
            "note": self.note,
        }


@dataclass
class QueryContext:
    """Everything an agent is given about the request."""

    question: str
    language: str = "en"
    latitude: float | None = None
    longitude: float | None = None
    session_id: str | None = None


@dataclass
class AgentResult:
    agent: str
    summary: str
    evidence: list[Evidence] = field(default_factory=list)
    confidence: float = 0.5
    # True while an agent is a placeholder, so stub data can never be mistaken
    # for a real observation in the response or the demo.
    is_stub: bool = False
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent": self.agent,
            "summary": self.summary,
            "evidence": [item.to_dict() for item in self.evidence],
            "confidence": self.confidence,
            "is_stub": self.is_stub,
            "error": self.error,
        }


class Agent(ABC):
    """A specialist. Distinguished by role, tools and scope — not by model."""

    name: str = "agent"
    description: str = ""
    # Plain-language triggers the planner matches against.
    handles: tuple[str, ...] = ()

    @abstractmethod
    async def run(self, context: QueryContext) -> AgentResult:
        """Do this agent's one job and report what it observed."""

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "handles": list(self.handles),
        }
