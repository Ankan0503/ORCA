"""Placeholder specialists.

These exist so the orchestrator's plan -> route -> merge -> explain loop can be
built and tested before any real data source is wired up. Every result is
flagged `is_stub=True` and every Evidence source is prefixed "STUB:", so
placeholder numbers can never be mistaken for real observations — in the API
response or on stage during a demo.

Each of these gets replaced one at a time. WeatherIntelligenceAgent (weather.py) and OceanAnalyticsAgent (ocean.py) are
real, and so is GeospatialAgent (geospatial.py). RiskAssessmentAgent below is
the last placeholder.
"""

from .base import Agent, AgentResult, Evidence, QueryContext
from .geospatial import GeospatialAgent
from .ocean import OceanAnalyticsAgent
from .weather import WeatherIntelligenceAgent


class RiskAssessmentAgent(Agent):
    name = "risk_assessment"
    description = "Combines the other agents' findings into an overall hazard verdict."
    handles = ("risk", "danger", "hazard", "safe", "advice")

    async def run(self, context: QueryContext) -> AgentResult:
        return AgentResult(
            agent=self.name,
            summary="Overall risk is low for a day trip close to shore.",
            evidence=[
                Evidence(
                    source="STUB: Risk model",
                    label="Composite risk level",
                    value="low",
                ),
            ],
            confidence=0.5,
            is_stub=True,
        )


def default_agents() -> list[Agent]:
    return [
        WeatherIntelligenceAgent(),
        OceanAnalyticsAgent(),
        GeospatialAgent(),
        RiskAssessmentAgent(),
    ]
