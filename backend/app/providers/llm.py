"""The reasoning LLM behind the orchestrator.

Groq (OpenAI-compatible) does the planning, routing and synthesis. It is kept
behind a tiny protocol so the provider can change without the orchestrator
noticing, and so the API still runs end to end when no key is configured — the
rule-based planner takes over instead of the service failing.
"""

from typing import Any, Protocol

import httpx

from ..config import Settings


class LLMError(RuntimeError):
    pass


class LLMClient(Protocol):
    """Minimal surface the orchestrator depends on."""

    @property
    def available(self) -> bool: ...

    async def complete(
        self,
        messages: list[dict[str, Any]],
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> str: ...


class GroqClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def available(self) -> bool:
        return self._settings.has_groq

    async def complete(
        self,
        messages: list[dict[str, Any]],
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> str:
        if not self.available:
            raise LLMError("GROQ_API_KEY is not set")

        body = {
            "model": self._settings.groq_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        async with httpx.AsyncClient(timeout=self._settings.request_timeout_seconds) as client:
            response = await client.post(
                f"{self._settings.groq_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._settings.groq_api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
            )

        if response.status_code >= 400:
            raise LLMError(f"Groq call failed ({response.status_code}): {response.text}")

        payload = response.json()
        try:
            return payload["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError) as exc:  # pragma: no cover - defensive
            raise LLMError(f"Unexpected Groq response shape: {payload}") from exc


class UnavailableLLM:
    """Stands in when no LLM key is configured.

    It never pretends to answer — callers check `available` and fall back to
    deterministic logic, so the absence of a key degrades quality rather than
    breaking the API.
    """

    @property
    def available(self) -> bool:
        return False

    async def complete(self, *args: Any, **kwargs: Any) -> str:
        raise LLMError("No LLM provider is configured")


def build_llm(settings: Settings) -> LLMClient:
    return GroqClient(settings) if settings.has_groq else UnavailableLLM()
