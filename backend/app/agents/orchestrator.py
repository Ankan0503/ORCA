"""The orchestrator: ORCA's planner and synthesiser.

It does four things, and the reasoning trace records each so the answer can be
explained rather than just asserted:

1. Understand the question and the language it was asked in.
2. Decide which specialists are needed (plan).
3. Run them concurrently and collect their evidence (route).
4. Write one answer, in the user's own language, grounded in that evidence.

Planning uses the LLM when a key is configured and falls back to keyword
matching otherwise, so the whole pipeline still runs without Groq. The
fallback is deliberately transparent: the trace says which planner ran.
"""

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any

from ..language.detect import LanguageGuess, detect_language
from ..language.glossary import glossary_for
from ..providers.llm import LLMClient, LLMError
from .base import Agent, AgentResult, QueryContext


@dataclass
class ReasoningStep:
    stage: str
    detail: str

    def to_dict(self) -> dict[str, str]:
        return {"stage": self.stage, "detail": self.detail}


@dataclass
class OrchestratorResponse:
    answer: str
    language: str
    agents_used: list[str]
    results: list[AgentResult] = field(default_factory=list)
    trace: list[ReasoningStep] = field(default_factory=list)
    used_stub_data: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "answer": self.answer,
            "language": self.language,
            "agents_used": self.agents_used,
            "evidence": [result.to_dict() for result in self.results],
            "reasoning": [step.to_dict() for step in self.trace],
            "used_stub_data": self.used_stub_data,
        }


_PLANNER_SYSTEM = """You are the planning agent of ORCA, a marine intelligence \
assistant for Indian fishermen.

Given a user's question, choose which specialist agents should run. Reply with \
ONLY a JSON array of agent names, no prose. Choose the fewest agents that can \
fully answer the question. If none clearly apply, choose ["weather_intelligence"].

Available agents:
{agents}"""


class Orchestrator:
    def __init__(self, agents: list[Agent], llm: LLMClient) -> None:
        self._agents = {agent.name: agent for agent in agents}
        self._llm = llm

    def describe_agents(self) -> list[dict[str, Any]]:
        return [agent.describe() for agent in self._agents.values()]

    async def handle(
        self,
        question: str,
        ui_language: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        session_id: str | None = None,
        known_language: str | None = None,
    ) -> OrchestratorResponse:
        trace: list[ReasoningStep] = []

        # ---- 1. Language -------------------------------------------------
        if known_language:
            # Voice input arrives with the language Sarvam already identified.
            language = LanguageGuess(
                code=known_language,
                confidence=1.0,
                method="sarvam-speech-to-text",
            )
        else:
            language = detect_language(question, ui_language)

        trace.append(
            ReasoningStep(
                stage="language",
                detail=(
                    f"Identified '{language.code}' via {language.method} "
                    f"(confidence {language.confidence:.2f})."
                ),
            )
        )

        context = QueryContext(
            question=question,
            language=language.code,
            latitude=latitude,
            longitude=longitude,
            session_id=session_id,
        )

        # ---- 2. Plan -----------------------------------------------------
        selected, planner = await self._plan(question)
        trace.append(
            ReasoningStep(
                stage="plan",
                detail=f"{planner} selected: {', '.join(selected)}.",
            )
        )

        # ---- 3. Route (concurrently) -------------------------------------
        results = await asyncio.gather(
            *(self._run_agent(self._agents[name], context) for name in selected)
        )
        for result in results:
            trace.append(
                ReasoningStep(
                    stage=f"agent:{result.agent}",
                    detail=result.error or result.summary,
                )
            )

        # ---- 4. Synthesise ------------------------------------------------
        # _synthesise reports which path it actually took: an LLM call can be
        # configured yet still fail, and a trace that claims otherwise would
        # misrepresent how the answer was produced.
        answer, method = await self._synthesise(context, results, language.code)
        trace.append(
            ReasoningStep(
                stage="synthesis",
                detail=f"Composed the reply from agent evidence {method}.",
            )
        )

        return OrchestratorResponse(
            answer=answer,
            language=language.code,
            agents_used=selected,
            results=list(results),
            trace=trace,
            used_stub_data=any(result.is_stub for result in results),
        )

    # ------------------------------------------------------------------ plan

    async def _plan(self, question: str) -> tuple[list[str], str]:
        """Choose agents with the LLM, falling back to keyword matching."""
        if self._llm.available:
            try:
                selected = await self._plan_with_llm(question)
                if selected:
                    return selected, "LLM planner"
                reason = "the LLM returned no known agent names"
            except (LLMError, json.JSONDecodeError, ValueError) as exc:
                # A planning failure must not take down the request; the
                # keyword planner is a valid, if blunter, answer. The reason is
                # surfaced rather than swallowed so the trace stays honest.
                reason = str(exc)
            return self._plan_by_keywords(question), f"Keyword planner (LLM planner failed: {reason})"

        return self._plan_by_keywords(question), "Keyword planner (no LLM configured)"

    async def _plan_with_llm(self, question: str) -> list[str]:
        catalogue = "\n".join(
            f"- {agent.name}: {agent.description}" for agent in self._agents.values()
        )
        raw = await self._llm.complete(
            [
                {"role": "system", "content": _PLANNER_SYSTEM.format(agents=catalogue)},
                {"role": "user", "content": question},
            ],
            temperature=0.0,
            max_tokens=200,
        )

        # Models like to wrap JSON in prose or fences; take the array.
        start, end = raw.find("["), raw.rfind("]")
        if start == -1 or end == -1:
            raise ValueError(f"Planner returned no JSON array: {raw!r}")

        names = json.loads(raw[start : end + 1])
        return [name for name in names if name in self._agents]

    def _plan_by_keywords(self, question: str) -> list[str]:
        lowered = question.lower()
        selected = [
            agent.name
            for agent in self._agents.values()
            if any(trigger in lowered for trigger in agent.handles)
        ]

        # Safety questions are only meaningful with a risk verdict attached.
        if "risk_assessment" in self._agents and len(selected) > 1:
            if "risk_assessment" not in selected:
                selected.append("risk_assessment")

        return selected or ["weather_intelligence"]

    # ----------------------------------------------------------------- agents

    async def _run_agent(self, agent: Agent, context: QueryContext) -> AgentResult:
        """Run one agent, converting a crash into a reported failure.

        One failing specialist should degrade the answer, not lose the request.
        """
        try:
            return await agent.run(context)
        except Exception as exc:  # noqa: BLE001 - deliberately broad
            return AgentResult(
                agent=agent.name,
                summary="",
                confidence=0.0,
                error=f"{type(exc).__name__}: {exc}",
            )

    # -------------------------------------------------------------- synthesis

    async def _synthesise(
        self,
        context: QueryContext,
        results: list[AgentResult],
        language: str,
    ) -> tuple[str, str]:
        """Return the answer and a description of how it was produced."""
        findings = self._format_findings(results)

        if not self._llm.available:
            return self._template_answer(results), "using a template (no LLM configured)"

        glossary = glossary_for(language)
        system = (
            "You are ORCA, a marine advisor for Indian fishermen. Answer using "
            "ONLY the findings provided — never invent numbers. Be concrete and "
            "brief (2-4 short sentences), say plainly whether it is safe, and "
            "write in simple words a fisherman can act on.\n\n"
            f"Write your entire reply in this language: {language}. "
            "Do not translate an English answer — compose it directly in that "
            "language."
        )
        if glossary:
            system += "\n\n" + glossary

        try:
            answer = await self._llm.complete(
                [
                    {"role": "system", "content": system},
                    {
                        "role": "user",
                        "content": (
                            f"Question: {context.question}\n\n"
                            f"Findings from specialist agents:\n{findings}"
                        ),
                    },
                ],
                temperature=0.3,
                max_tokens=400,
            )
            return answer, "using the LLM"
        except LLMError as exc:
            return (
                self._template_answer(results),
                f"using a template after the LLM call failed ({exc})",
            )

    def _format_findings(self, results: list[AgentResult]) -> str:
        lines: list[str] = []
        for result in results:
            if result.error:
                lines.append(f"- {result.agent}: unavailable ({result.error})")
                continue
            lines.append(f"- {result.agent}: {result.summary}")
            for item in result.evidence:
                unit = f" {item.unit}" if item.unit else ""
                lines.append(f"    * {item.label}: {item.value}{unit} [{item.source}]")
        return "\n".join(lines)

    def _template_answer(self, results: list[AgentResult]) -> str:
        """Deterministic reply used when no LLM is configured."""
        parts = [result.summary for result in results if result.summary]
        return " ".join(parts) or "No specialist could answer that yet."
