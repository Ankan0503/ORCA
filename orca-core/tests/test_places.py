"""A coastal place named in the question is where the question is answered for."""

import asyncio

import pytest

from app.agents.base import Agent, AgentResult, QueryContext
from app.agents.orchestrator import Orchestrator
from app.language import localise as localise_module
from app.providers.llm import UnavailableLLM
from app.tools.places import find_place


@pytest.mark.parametrize(
    "text, name",
    [
        ("Is it safe to fish near Paradip tomorrow morning?", "Paradip, Odisha"),
        ("How are the waves at Paradeep?", "Paradip, Odisha"),
        ("Where is the nearest fishing zone off Vizag?", "Visakhapatnam, Andhra Pradesh"),
        ("Is Puri safer than Paradip today?", "Puri, Odisha"),
        ("Any cyclone alert for Tuticorin?", "Thoothukudi, Tamil Nadu"),
        ("Should I go fishing in northern Andhra Pradesh?", "North Andhra Pradesh coast (Visakhapatnam)"),
        ("Is the sea calm along the Odisha coast?", "Odisha coast (Paradip)"),
        ("How is fishing in Kerala this week?", "Kerala coast (Kochi)"),
        ("Is it safe to go fishing today?", None),
        ("How do I purify water on a boat?", None),
    ],
)
def test_find_place(text, name):
    place = find_place(text)
    assert (place.name if place else None) == name


class FakeSarvam:
    available = True

    def __init__(self, english: str) -> None:
        self.english = english

    async def translate(self, text, target_language_code, source_language_code="auto"):
        return self.english if target_language_code == "en-IN" else "উত্তর"


class Recorder(Agent):
    is_stub = False
    name = "weather_intelligence"
    handles = ("safe",)

    def __init__(self) -> None:
        self.seen: list[QueryContext] = []

    async def run(self, context: QueryContext) -> AgentResult:
        self.seen.append(context)
        return AgentResult(agent=self.name, summary="Calm seas at that spot.")


def test_named_place_replaces_the_device_position():
    localise_module._cache.clear()
    weather = Recorder()
    sarvam = FakeSarvam("Is it safe to fish near Paradip tomorrow morning?")
    orchestrator = Orchestrator(agents=[weather], llm=UnavailableLLM(), translator=sarvam)

    response = asyncio.run(
        orchestrator.handle(
            question="কাল সকালে পারাদ্বীপের কাছে মাছ ধরা কি নিরাপদ?",
            known_language="bn",
            latitude=21.6266,
            longitude=87.5074,
        )
    )

    assert (weather.seen[0].latitude, weather.seen[0].longitude) == (20.2644, 86.6947)
    assert any(s.stage == "location" and "Paradip" in s.detail for s in response.trace)
