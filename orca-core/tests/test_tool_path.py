"""On the tool path the planned agents always run, once, and their evidence survives a failed model call."""

import asyncio

import pytest

from app.agents.base import Agent, AgentResult, QueryContext
from app.agents.orchestrator import Orchestrator
from app.language import localise as localise_module
from app.providers.llm import LLMError

QUESTION = "কাল সকালে সমুদ্রে যাওয়া কি নিরাপদ?"
NATIVE = "সমুদ্র শান্ত।"


class FakeSarvam:
    available = True

    async def translate(self, text, target_language_code, source_language_code="auto"):
        return "Is it safe to go to sea tomorrow morning?" if target_language_code == "en-IN" else NATIVE


class Recorder(Agent):
    is_stub = False
    handles = ("safe",)

    def __init__(self, name: str) -> None:
        self.name = name
        self.seen: list[QueryContext] = []

    async def run(self, context: QueryContext) -> AgentResult:
        self.seen.append(context)
        return AgentResult(agent=self.name, summary=f"{self.name} reports calm seas.")


class AnsweringLLM:
    """Answers straight away, without calling any agent itself."""

    available = True

    def __init__(self) -> None:
        self.messages: list[dict] = []

    async def complete_with_tools(self, messages, tools, temperature=0.2, max_tokens=1024):
        self.messages = messages
        return {"content": NATIVE, "tool_calls": []}

    async def complete(self, messages, temperature=0.2, max_tokens=1024):
        return NATIVE


class QuotaExhaustedLLM:
    available = True

    async def complete_with_tools(self, *args, **kwargs):
        raise LLMError("Groq call failed (429)")

    async def complete(self, *args, **kwargs):
        raise LLMError("Groq call failed (429)")


@pytest.fixture(autouse=True)
def fresh_cache():
    localise_module._cache.clear()
    yield
    localise_module._cache.clear()


def _setup(llm):
    weather, risk = Recorder("weather_intelligence"), Recorder("risk_assessment")
    return Orchestrator(agents=[weather, risk], llm=llm, translator=FakeSarvam()), weather, risk


def test_planned_agents_run_even_when_the_model_would_not_call_them():
    llm = AnsweringLLM()
    orchestrator, weather, _risk = _setup(llm)

    response = asyncio.run(orchestrator.handle(question=QUESTION, known_language="bn"))

    assert set(response.agents_used) == {"weather_intelligence", "risk_assessment"}
    assert weather.seen[0].params == {"when": "tomorrow_morning"}
    assert any(m.get("role") == "tool" for m in llm.messages)
    assert response.answer == NATIVE


class TaggingSarvam:
    available = True

    async def translate(self, text, target_language_code, source_language_code="auto"):
        return "Is it safe to go to sea tomorrow morning?" if target_language_code == "en-IN" else f"[bn] {text}"


class EstimatingOcean(Agent):
    is_stub = False
    name = "ocean_analytics"
    handles = ("safe",)

    async def run(self, context: QueryContext) -> AgentResult:
        return AgentResult(agent=self.name, summary="Best estimated ground is 20 km S.", data={"estimate": True})


def test_estimated_zone_is_flagged_even_when_the_model_drops_the_caveat():
    orchestrator = Orchestrator(agents=[EstimatingOcean()], llm=AnsweringLLM(), translator=TaggingSarvam())

    response = asyncio.run(orchestrator.handle(question=QUESTION, known_language="bn"))

    assert response.answer.startswith(NATIVE)
    assert "[bn] Note: this fishing zone is ORCA's own estimate" in response.answer


def test_failed_model_call_reuses_the_evidence_instead_of_rerunning_agents():
    orchestrator, weather, risk = _setup(QuotaExhaustedLLM())

    response = asyncio.run(orchestrator.handle(question=QUESTION, known_language="bn"))

    assert len(weather.seen) == 1 and len(risk.seen) == 1
    assert NATIVE in response.answer
