"""The set of specialists the orchestrator routes between.

Every agent here is backed by real data:

- :class:`WeatherIntelligenceAgent` — Open-Meteo marine and forecast APIs.
- :class:`OceanAnalyticsAgent` — INCOIS Potential Fishing Zone advisories.
- :class:`GeospatialAgent` — Marine Regions v12 EEZ and treaty boundaries.
- :class:`CycloneWatchAgent` — IMD/RSMC tropical weather outlook.
- :class:`RiskAssessmentAgent` — combines the three into one verdict.
- :class:`RoutePlanningAgent` — the safest passage to the nearest fishing zone,
  off land and around storms, with when to leave and when to be back.
- :class:`HistoricalTrendsAgent` — ERA5 and NOAA satellite records, years deep.
- :class:`VisualizationAgent` — chooses what to plot, and returns the series.
- :class:`ReportingAgent` — composes a dated, sourced situation brief.
- :class:`DataDiscoveryAgent` — the source catalogue, probed live.
- :class:`EvidenceRetrievalAgent` — official rules, retrieved from documents
  ORCA has actually fetched. The only agent that reads rather than measures,
  and the only one that can answer "am I allowed" rather than "is it safe".

With these three the eight agent roles the problem statement names are all
present: planning (the orchestrator itself), weather intelligence, ocean
analytics, geospatial, risk assessment, visualization, reporting and data
discovery — plus cyclone watch and historical trends, which the statement does
not name but the Disaster Management theme wants.

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
from .route import RoutePlanningAgent
from .discovery import DataDiscoveryAgent
from .evidence import EvidenceRetrievalAgent
from .reporting import ReportingAgent
from .trends import HistoricalTrendsAgent
from .visualization import VisualizationAgent
from .weather import WeatherIntelligenceAgent


def default_agents() -> list[Agent]:
    return [
        WeatherIntelligenceAgent(),
        OceanAnalyticsAgent(),
        GeospatialAgent(),
        CycloneWatchAgent(),
        RiskAssessmentAgent(),
        RoutePlanningAgent(),
        HistoricalTrendsAgent(),
        VisualizationAgent(),
        ReportingAgent(),
        DataDiscoveryAgent(),
        EvidenceRetrievalAgent(),
    ]
