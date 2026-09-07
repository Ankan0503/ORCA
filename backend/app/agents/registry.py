"""The set of specialists the orchestrator routes between.

Every agent here is backed by real data:

- :class:`WeatherIntelligenceAgent` — Open-Meteo marine and forecast APIs.
- :class:`OceanAnalyticsAgent` — INCOIS Potential Fishing Zone advisories.
- :class:`GeospatialAgent` — Marine Regions v12 EEZ and treaty boundaries.
- :class:`CycloneWatchAgent` — IMD/RSMC tropical weather outlook.
- :class:`RiskAssessmentAgent` — combines the three into one verdict.
- :class:`HistoricalTrendsAgent` — ERA5 and NOAA satellite records, years deep.

This module was once ``stubs.py`` and held placeholder agents that returned
invented figures. None remain, so the name went with them. The ``is_stub`` flag
on :class:`~app.agents.base.Agent` is kept: it is what the ``/health`` endpoint
reports, and it should stay available for any future agent that is scaffolded
before its data source exists.
"""

from .base import Agent
from .cyclone import CycloneWatchAgent
from .geospatial import GeospatialAgent
from .ocean import OceanAnalyticsAgent
from .risk import RiskAssessmentAgent
from .trends import HistoricalTrendsAgent
from .weather import WeatherIntelligenceAgent


def default_agents() -> list[Agent]:
    return [
        WeatherIntelligenceAgent(),
        OceanAnalyticsAgent(),
        GeospatialAgent(),
        CycloneWatchAgent(),
        RiskAssessmentAgent(),
        HistoricalTrendsAgent(),
    ]
