"""The English pivot: a question in any language is planned, routed and timed in English."""

import asyncio

import pytest

from app.agents import timeframe
from app.agents.base import Agent, AgentResult, QueryContext
from app.agents.orchestrator import Orchestrator
from app.agents.registry import default_agents
from app.language import localise as localise_module
from app.language.localise import to_english
from app.providers.llm import UnavailableLLM
from app.providers.sarvam import SarvamError

BENGALI_TOMORROW = "কাল সকালে সমুদ্রে যাওয়া কি নিরাপদ?"


class FakeSarvam:
    available = True

    def __init__(self, english: str = "", native: str = "", fail: bool = False) -> None:
        self.english, self.native, self.fail = english, native, fail
        self.calls: list[tuple[str, str, str]] = []

    async def translate(self, text, target_language_code, source_language_code="auto"):
        self.calls.append((text, target_language_code, source_language_code))
        if self.fail:
            raise SarvamError("translator down")
        return self.english if target_language_code == "en-IN" else self.native


class Recorder(Agent):
    is_stub = False

    def __init__(self, name: str, handles: tuple[str, ...]) -> None:
        self.name, self.handles = name, handles
        self.seen: list[QueryContext] = []

    async def run(self, context: QueryContext) -> AgentResult:
        self.seen.append(context)
        return AgentResult(agent=self.name, summary=f"{self.name} reports calm seas.")


@pytest.fixture(autouse=True)
def fresh_cache():
    localise_module._cache.clear()
    yield
    localise_module._cache.clear()


# The eight questions from the ISRO problem statement, with the agents each one needs.
BENCHMARK = [
    ("Where is the nearest Potential Fishing Zone (PFZ) today?", {"ocean_analytics", "geospatial"}),
    ("Is it safe to venture into the sea tomorrow morning?", {"weather_intelligence", "risk_assessment"}),
    (
        "What are the tide, weather, and sea conditions near my fishing location?",
        {"weather_intelligence", "ocean_analytics"},
    ),
    ("Are there any lightning or cyclone alerts in my area?", {"weather_intelligence", "cyclone_watch"}),
    (
        "Which regions show high chlorophyll concentration and favourable sea surface temperature?",
        {"ocean_analytics"},
    ),
    (
        "What is the safest route for a fishing vessel considering weather and sea-state conditions?",
        {"route_planning", "weather_intelligence", "risk_assessment"},
    ),
    ("Why has fish productivity declined in a particular coastal region?", {"historical_trends", "ocean_analytics"}),
    (
        "Which fishing zones should be avoided due to hazardous marine conditions or geofencing restrictions?",
        {"geospatial", "evidence_retrieval", "weather_intelligence"},
    ),
]


@pytest.mark.parametrize("question, needed", BENCHMARK)
def test_keyword_planner_covers_isro_benchmark(question, needed):
    orchestrator = Orchestrator(agents=default_agents(), llm=UnavailableLLM())
    assert needed <= set(orchestrator._plan_by_keywords(question))


@pytest.mark.parametrize(
    "text, window",
    [
        ("Is it safe to venture into the sea tomorrow morning?", "tomorrow_morning"),
        ("Can I go fishing the day after tomorrow?", "day_after_tomorrow"),
        ("How is the sea tomorrow?", "tomorrow"),
        ("Will it rain tonight?", "tonight"),
        ("Is it safe to go fishing today?", None),
        ("Where is the nearest PFZ?", None),
    ],
)
def test_time_window_is_read_from_english(text, window):
    assert timeframe.infer(text) == window


def test_to_english_names_the_source_when_the_script_agrees():
    sarvam = FakeSarvam(english="Is it safe to go to sea tomorrow morning?")
    assert asyncio.run(to_english(BENGALI_TOMORROW, "bn", sarvam)) == "Is it safe to go to sea tomorrow morning?"
    assert sarvam.calls == [(BENGALI_TOMORROW, "en-IN", "bn-IN")]


def test_to_english_lets_sarvam_judge_romanised_text():
    sarvam = FakeSarvam(english="Will I get fish today?")
    asyncio.run(to_english("aaj machh pabo?", "bn", sarvam))
    assert sarvam.calls[0][2] == "auto"


def test_to_english_keeps_protected_terms_out_of_the_translator():
    sarvam = FakeSarvam(english="Where is the nearest @@0@@?")
    assert asyncio.run(to_english("সবচেয়ে কাছের PFZ কোথায়?", "bn", sarvam)) == "Where is the nearest PFZ?"
    assert "PFZ" not in sarvam.calls[0][0]


def test_to_english_skips_english_and_survives_a_dead_translator():
    assert asyncio.run(to_english("Is it safe?", "en", FakeSarvam(english="x"))) is None
    assert asyncio.run(to_english(BENGALI_TOMORROW, "bn", FakeSarvam(fail=True))) is None


def test_bengali_question_is_planned_and_timed_in_english_and_answered_in_bengali():
    weather = Recorder("weather_intelligence", ("safe", "venture"))
    risk = Recorder("risk_assessment", ("safe",))
    ocean = Recorder("ocean_analytics", ("pfz",))
    sarvam = FakeSarvam(english="Is it safe to venture into the sea tomorrow morning?", native="সমুদ্র শান্ত।")
    orchestrator = Orchestrator(agents=[weather, risk, ocean], llm=UnavailableLLM(), translator=sarvam)

    response = asyncio.run(orchestrator.handle(question=BENGALI_TOMORROW, known_language="bn"))

    assert set(response.agents_used) == {"weather_intelligence", "risk_assessment"}
    seen = weather.seen[0]
    assert seen.question == "Is it safe to venture into the sea tomorrow morning?"
    assert seen.original_question == BENGALI_TOMORROW
    assert seen.params == {"when": "tomorrow_morning"}
    assert response.language == "bn"
    assert "সমুদ্র শান্ত।" in response.answer
    assert any(s.stage == "translation" and "Understood as" in s.detail for s in response.trace)


def test_failed_translation_plans_on_the_original_words():
    weather = Recorder("weather_intelligence", ("safe",))
    orchestrator = Orchestrator(agents=[weather], llm=UnavailableLLM(), translator=FakeSarvam(fail=True))

    response = asyncio.run(orchestrator.handle(question=BENGALI_TOMORROW, known_language="bn"))

    assert weather.seen[0].question == BENGALI_TOMORROW
    assert any("Could not translate" in s.detail for s in response.trace)
