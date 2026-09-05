"""Placeholder specialists.

These exist so the orchestrator's plan -> route -> merge -> explain loop can be
built and tested before any real data source is wired up. Every result is
flagged `is_stub=True` and every Evidence source is prefixed "STUB:", so
placeholder numbers can never be mistaken for real observations — in the API
response or on stage during a demo.

Each of these gets replaced one at a time. The first replacement is
WeatherIntelligenceAgent, backed by the Open-Meteo Marine API.
"""

from .base import Agent, AgentResult, Evidence, QueryContext


class WeatherIntelligenceAgent(Agent):
    name = "weather_intelligence"
    description = "Wind, waves and weather; judges whether it is safe to go out."
    handles = ("safety", "weather", "wind", "wave", "storm", "rain", "go out", "venture")

    async def run(self, context: QueryContext) -> AgentResult:
        return AgentResult(
            agent=self.name,
            summary="Seas are moderate with no active warnings.",
            evidence=[
                Evidence(
                    source="STUB: Open-Meteo Marine",
                    label="Significant wave height",
                    value="1.2",
                    unit="m",
                ),
                Evidence(
                    source="STUB: Open-Meteo Marine",
                    label="Wind speed",
                    value="14",
                    unit="km/h",
                ),
            ],
            confidence=0.5,
            is_stub=True,
        )


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
