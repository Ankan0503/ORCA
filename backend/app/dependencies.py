"""Shared singletons, wired once and injected into routes."""

from functools import lru_cache

from .agents.orchestrator import Orchestrator
from .agents.registry import default_agents
from .config import get_settings
from .providers.llm import build_llm
from .providers.sarvam import SarvamClient


@lru_cache
def get_sarvam() -> SarvamClient:
    return SarvamClient(get_settings())


@lru_cache
def get_orchestrator() -> Orchestrator:
    settings = get_settings()
    return Orchestrator(agents=default_agents(), llm=build_llm(settings))
