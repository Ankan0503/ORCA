"""Small talk and off-topic messages never reach the marine agents; replies stay in the user's language."""

import asyncio
import uuid

import pytest

from app.agents.base import Agent, AgentResult, QueryContext
from app.agents.guardrails import triage
from app.agents.orchestrator import Orchestrator
from app.language import localise as localise_module
from app.providers.llm import UnavailableLLM


class FakeSarvam:
    available = True

    def __init__(self, english: str, native: str = "উত্তর") -> None:
        self.english, self.native = english, native

    async def translate(self, text, target_language_code, source_language_code="auto"):
        return self.english if target_language_code == "en-IN" else self.native


class Recorder(Agent):
    is_stub = False

    def __init__(self, name: str = "weather_intelligence", handles: tuple[str, ...] = ("safe",)) -> None:
        self.name, self.handles = name, handles
        self.seen: list[QueryContext] = []

    async def run(self, context: QueryContext) -> AgentResult:
        self.seen.append(context)
        return AgentResult(agent=self.name, summary=f"{self.name} reports calm seas.")


class EnglishOnlyLLM:
    """A model that ignores the language instruction and answers in English."""

    available = True

    async def complete_with_tools(self, messages, tools, temperature=0.2, max_tokens=1024):
        return {"content": "The sea is calm today.", "tool_calls": []}

    async def complete(self, messages, temperature=0.2, max_tokens=1024):
        return "The sea is calm today."


@pytest.fixture(autouse=True)
def fresh_cache():
    localise_module._cache.clear()
    yield
    localise_module._cache.clear()


@pytest.mark.parametrize(
    "text, kind",
    [
        ("How are you?", "greeting"),
        ("Hello!", "greeting"),
        ("Who are you?", "greeting"),
        ("Thank you", "thanks"),
        ("Who won the cricket match yesterday?", "off_topic"),
        ("When is the next train?", "off_topic"),
        ("Please open the window", "off_topic"),
        ("Is it safe to go fishing today?", "marine"),
        ("Can I go today?", "marine"),
        ("Where will I find hilsa?", "marine"),
        ("Hello, is it safe to go to sea tomorrow?", "marine"),
        ("How do you know this?", "marine"),
        ("Safe road to the fishing place near me", "marine"),
    ],
)
def test_triage(text, kind):
    assert triage(text) == kind


def _ask(orchestrator: Orchestrator, question: str, session_id: str | None = None):
    return asyncio.run(orchestrator.handle(question=question, known_language="bn", session_id=session_id))


def test_bengali_greeting_gets_a_greeting_not_a_forecast():
    weather = Recorder()
    sarvam = FakeSarvam(english="How are you?", native="আমি ORCA, আপনাকে সাহায্য করতে প্রস্তুত।")
    orchestrator = Orchestrator(agents=[weather], llm=UnavailableLLM(), translator=sarvam)

    response = _ask(orchestrator, "কেমন আছো?")

    assert weather.seen == []
    assert response.agents_used == []
    assert response.answer == "আমি ORCA, আপনাকে সাহায্য করতে প্রস্তুত।"
    assert any(s.stage == "guardrail" for s in response.trace)


def test_off_topic_question_is_declined_without_agents():
    weather = Recorder()
    orchestrator = Orchestrator(agents=[weather], llm=UnavailableLLM(), translator=FakeSarvam("Who won the cricket match?"))

    response = _ask(orchestrator, "ক্রিকেট ম্যাচ কে জিতেছে?")

    assert weather.seen == []
    assert response.agents_used == []


def test_short_follow_up_in_a_conversation_still_reaches_the_agents():
    weather = Recorder(handles=("safe", "tomorrow"))
    session = f"guard-{uuid.uuid4().hex}"
    first = Orchestrator(agents=[weather], llm=UnavailableLLM(), translator=FakeSarvam("Is it safe to go fishing today?"))
    _ask(first, "আজ কি মাছ ধরা নিরাপদ?", session)

    follow_up = Orchestrator(agents=[weather], llm=UnavailableLLM(), translator=FakeSarvam("And tomorrow?"))
    _ask(follow_up, "আর কাল?", session)

    assert len(weather.seen) == 2


def test_english_reply_to_a_bengali_question_is_translated():
    sarvam = FakeSarvam(english="Is the sea calm today?", native="আজ সমুদ্র শান্ত।")
    orchestrator = Orchestrator(agents=[Recorder()], llm=EnglishOnlyLLM(), translator=sarvam)

    response = _ask(orchestrator, "আজ সমুদ্র কি শান্ত?")

    assert response.answer == "আজ সমুদ্র শান্ত।"
    assert any("translated to 'bn'" in s.detail for s in response.trace)
