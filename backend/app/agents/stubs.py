"""Placeholder specialists.

These exist so the orchestrator's plan -> route -> merge -> explain loop can be
built and tested before any real data source is wired up. Every result is
flagged `is_stub=True` and every Evidence source is prefixed "STUB:", so
placeholder numbers can never be mistaken for real observations — in the API
response or on stage during a demo.

Each of these gets replaced one at a time. WeatherIntelligenceAgent has already been replaced with a real
implementation in weather.py; the three below are still placeholders.
"""

from .base import Agent, AgentResult, Evidence, QueryContext
from .weather import WeatherIntelligenceAgent


class OceanAnalyticsAgent(Agent):
    name = "ocean_analytics"
    description = "Sea surface temperature, chlorophyll and potential fishing zones."
    handles = ("fish", "pfz", "fishing zone", "chlorophyll", "temperature", "catch")

    async def run(self, context: QueryContext) -> AgentResult:
        return AgentResult(
            agent=self.name,
            summary="A thermal front with raised chlorophyll sits about 12 km offshore.",
            evidence=[
                Evidence(
                    source="STUB: INCOIS PFZ advisory",
                    label="Nearest potential fishing zone",
                    value="12",
                    unit="km",
                ),
                Evidence(
                    source="STUB: Sea surface temperature",
                    label="SST",
                    value="27.5",
                    unit="degC",
                ),
            ],
            confidence=0.5,
            is_stub=True,
        )


class GeospatialAgent(Agent):
    name = "geospatial"
    description = "Maritime boundaries, restricted waters and geofencing."
    handles = ("boundary", "border", "eez", "restricted", "protected", "geofence", "allowed")

    async def run(self, context: QueryContext) -> AgentResult:
        return AgentResult(
            agent=self.name,
            summary="Inside India's EEZ, with no restricted area nearby.",
            evidence=[
                Evidence(
                    source="STUB: Marine Regions EEZ v12",
                    label="Distance to EEZ boundary",
                    value="180",
                    unit="km",
                ),
            ],
            confidence=0.5,
            is_stub=True,
        )


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
