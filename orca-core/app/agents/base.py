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
    """Everything an agent is given about the request.

    `params` carries the arguments the planner chose for *this* invocation —
    which time window to assess, which position to look at. Without it an agent
    can only ever answer about the caller's here-and-now, so a question like
    "is it safe the day after tomorrow?" would route correctly and then answer
    about today. Agents read the keys they declare in `Agent.parameters` and
    ignore the rest.
    """

    question: str
    language: str = "en"
    latitude: float | None = None
    longitude: float | None = None
    session_id: str | None = None
    params: dict[str, Any] = field(default_factory=dict)
    # The user's own words when `question` is their English translation.
    original_question: str | None = None

    def with_params(self, params: dict[str, Any]) -> "QueryContext":
        """A copy aimed at one specific invocation.

        Latitude and longitude are overridden when the planner supplied them, so
        the model can ask about a place other than where the user is standing.
        """
        latitude = params.get("latitude", self.latitude)
        longitude = params.get("longitude", self.longitude)
        return QueryContext(
            question=self.question,
            language=self.language,
            latitude=latitude if latitude is not None else self.latitude,
            longitude=longitude if longitude is not None else self.longitude,
            session_id=self.session_id,
            params=params,
            original_question=self.original_question,
        )


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
    # Structured findings, for callers that need to render figures rather than
    # prose. Evidence stays the record of *what was observed*; this is the
    # agent's own conclusion in machine-readable form, so a screen never has to
    # parse a sentence to get a number.
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent": self.agent,
            "summary": self.summary,
            "evidence": [item.to_dict() for item in self.evidence],
            "confidence": self.confidence,
            "is_stub": self.is_stub,
            "error": self.error,
            "data": self.data,
        }


class Agent(ABC):
    """A specialist. Distinguished by role, tools and scope — not by model."""

    name: str = "agent"
    description: str = ""
    # Plain-language triggers the planner matches against.
    handles: tuple[str, ...] = ()
    # Placeholder until a real data source is wired in. Surfaced through the API
    # so stub numbers can never be mistaken for observations.
    is_stub: bool = True

    # JSON Schema for the arguments this agent accepts, in the shape an
    # OpenAI-compatible tool definition expects. This is what turns an agent
    # from something the planner merely *selects* into something it can
    # *configure* — the difference between answering the right question and
    # answering the right question about the wrong day.
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "latitude": {
                "type": "number",
                "description": "Only if asking about somewhere other than the user's position.",
            },
            "longitude": {
                "type": "number",
                "description": "Only if asking about somewhere other than the user's position.",
            },
        },
    }

    def as_tool(self) -> dict[str, Any]:
        """This agent as a function the planner can call."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    @abstractmethod
    async def run(self, context: QueryContext) -> AgentResult:
        """Do this agent's one job and report what it observed."""

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "handles": list(self.handles),
            "is_stub": self.is_stub,
        }
