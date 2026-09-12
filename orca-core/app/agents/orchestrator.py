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
import re
from dataclasses import dataclass, field
from typing import Any

from ..memory import ConversationStore, Session, get_store
from ..language.detect import LanguageGuess, detect_by_script, detect_language
from ..language.glossary import glossary_for
from ..language.localise import localise, to_english
from ..providers.llm import LLMClient, LLMError
from ..providers.sarvam import SarvamClient
from ..tools import decision_gate, places
from .base import Agent, AgentResult, QueryContext
from . import execution, guardrails, timeframe


#: Emphasis markers the model reaches for out of habit. They are not rendered
#: anywhere in ORCA — the answer card prints plain text and Sarvam speaks it —
#: so a reply about a storm arrives reading "**unsafe**" on screen and, worse,
#: with the asterisks in the spoken version. Stripped once, at the point the
#: answer is finalised, so display and speech both get the clean sentence.
_MARKDOWN_EMPHASIS = re.compile(r"(\*\*|__|(?<![\w*])\*(?!\s))")


def _plain(text: str) -> str:
    """The model's answer with markdown emphasis removed."""
    cleaned = _MARKDOWN_EMPHASIS.sub("", text)
    # Headings and bullet markers at the start of a line read as noise when
    # spoken; the bullet becomes a dash, which a screen reader handles.
    cleaned = re.sub(r"^\s{0,3}#{1,6}\s*", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"^\s{0,3}[*+]\s+", "- ", cleaned, flags=re.MULTILINE)
    return cleaned.strip()


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
    directive: str | None = None
    status: str = "COMPLETE"  # "COMPLETE" | "DEGRADED" | "UNKNOWN" | "BLOCKED"
    degraded_components: list[str] = field(default_factory=list)
    data_freshness: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "answer": self.answer,
            "language": self.language,
            "agents_used": self.agents_used,
            "evidence": [result.to_dict() for result in self.results],
            "reasoning": [step.to_dict() for step in self.trace],
            "used_stub_data": self.used_stub_data,
            "directive": self.directive,
            "status": self.status,
            "degraded_components": self.degraded_components,
            "data_freshness": self.data_freshness,
        }


# Which specialists each kind of question needs; "fewest agents" alone under-selected.
_ROUTING_GUIDE = """Which agents each kind of question needs:
- Is it safe / should I go out / can I venture: weather_intelligence, risk_assessment (add cyclone_watch if storms or several days ahead are mentioned).
- Where to fish / nearest PFZ / fishing zone: ocean_analytics, geospatial.
- Tide, weather and sea conditions: weather_intelligence, ocean_analytics.
- Lightning, storm or cyclone alerts: weather_intelligence, cyclone_watch.
- Chlorophyll or sea surface temperature: ocean_analytics.
- Safest route, path or way to a fishing zone, or when to leave and be back: route_planning, weather_intelligence, risk_assessment.
- Why the catch or fish productivity declined: historical_trends, ocean_analytics.
- Zones to avoid, restricted waters, borders, geofencing: geospatial, evidence_retrieval, weather_intelligence.
- Rules, bans, permits, required equipment: evidence_retrieval.
- A report, brief or summary of everything: reporting.
- Charts, or change over hours, days or years: visualization.
- Data sources, freshness or accuracy: data_discovery."""

_PLANNER_SYSTEM = """You are the planning agent of ORCA, a marine intelligence \
assistant for Indian fishermen.

Given a user's question, choose which specialist agents should run. Reply with \
ONLY a JSON array of agent names, no prose. Choose every agent the answer needs \
and no others. If none clearly apply, choose ["weather_intelligence"].

{routing}

Available agents:
{agents}"""


# How many times the model may call agents before it must answer. Enough for a
# real chain (check weather -> see a storm -> re-check the route), bounded so a
# confused model cannot spin.
MAX_TOOL_ROUNDS = 4


def _user_turn(context: QueryContext) -> str:
    """The user's own words, with the English the plan was made from."""
    if not context.original_question:
        return context.question
    return f"{context.original_question}\n\n(English translation: {context.question})"


class Orchestrator:
    def __init__(
        self,
        agents: list[Agent],
        llm: LLMClient,
        memory: ConversationStore | None = None,
        translator: SarvamClient | None = None,
    ) -> None:
        self._agents = {agent.name: agent for agent in agents}
        self._llm = llm
        self._memory = memory or get_store()
        self._translator = translator

    def describe_agents(self) -> list[dict[str, Any]]:
        return [agent.describe() for agent in self._agents.values()]

    async def _to_english(self, question: str, language: str) -> str | None:
        if self._translator is None:
            return None
        english = await to_english(question, language, self._translator)
        return english if english and english != question.strip() else None

    def _guard(self, english: str, session: Session | None) -> str | None:
        """Why this message should not reach the agents, or None if it should."""
        kind = guardrails.triage(english)
        # A bare "and tomorrow?" mid-conversation is a follow-up, not off-topic.
        if kind == "marine" or (kind == "off_topic" and session and session.turns):
            return None
        return kind

    async def _guarded_reply(
        self, kind: str, language: str, trace: list[ReasoningStep]
    ) -> OrchestratorResponse:
        answer = await self._say(guardrails.REPLIES[kind], language)
        trace.append(
            ReasoningStep(
                stage="guardrail",
                detail=f"Classified as {kind.replace('_', ' ')}, not a marine question; no agents were called.",
            )
        )
        return OrchestratorResponse(
            answer=answer,
            language=language,
            agents_used=[],
            results=[],
            trace=trace,
            used_stub_data=False,
            directive="INFORMATIVE",
            status="BLOCKED" if kind in ("harmful", "off_topic") else "COMPLETE",
            degraded_components=[],
            data_freshness={},
        )

    async def _say(self, text: str, language: str) -> str:
        """A fixed English sentence in the user's language."""
        if self._translator is None or not self._translator.available:
            return text
        return (await localise({"message": text}, language, self._translator))["message"]

    async def _in_language(self, answer: str, language: str) -> str:
        """Translate an answer that came back in English to a question asked in another language."""
        if language == "en" or not answer or detect_by_script(answer) is not None:
            return answer
        if self._translator is None or not self._translator.available:
            return answer
        return (await localise({"message": answer}, language, self._translator))["message"]

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
        session = self._memory.get(session_id)

        # A follow-up that names no place is about the same water as the question
        # before it. Without this, "and further out?" would silently fall back to
        # wherever the device happens to be.
        if latitude is None and session and session.latitude is not None:
            latitude, longitude = session.latitude, session.longitude
            trace.append(
                ReasoningStep(
                    stage="memory",
                    detail=(
                        f"No position in this message; reusing the one from earlier in "
                        f"the conversation ({latitude:.3f}, {longitude:.3f})."
                    ),
                )
            )
        elif session:
            trace.append(
                ReasoningStep(
                    stage="memory",
                    detail=f"Recalled {len(session.turns) // 2} earlier exchange(s) in this session.",
                )
            )

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

        # ---- 1b. Pivot to English: plan, route and search in English; reply in the user's language.
        english = await self._to_english(question, language.code)
        if english:
            trace.append(
                ReasoningStep(
                    stage="translation",
                    detail=f'Understood as: "{english}" (Sarvam, {language.code} → en).',
                )
            )
        elif language.code != "en":
            trace.append(
                ReasoningStep(
                    stage="translation",
                    detail=f"Could not translate from '{language.code}'; planning on the original words.",
                )
            )

        context = QueryContext(
            question=english or question,
            language=language.code,
            latitude=latitude,
            longitude=longitude,
            session_id=session_id,
            original_question=question if english else None,
        )

        # Judged on English only: without a translation, a real question must not be turned away.
        if language.code == "en" or english:
            blocked = self._guard(context.question, session)
            if blocked:
                return await self._guarded_reply(blocked, language.code, trace)

        # A place named in the question beats the device's position.
        named = places.find_place(context.question)
        if named:
            latitude, longitude = named.latitude, named.longitude
            context.latitude, context.longitude = latitude, longitude
            trace.append(
                ReasoningStep(
                    stage="location",
                    detail=f"The question names {named.name}; answering for {latitude:.3f}, {longitude:.3f}.",
                )
            )

        # ---- 2. Reason ----------------------------------------------------
        # Preferred path: let the model call agents as tools, see what they
        # found, and call again if it needs more. That is what lets it choose
        # *how* to ask (which day, which place), react to a result, and consult
        # the same specialist twice — none of which one-shot planning can do.
        answer = ""
        results: list[AgentResult] = []
        selected: list[str] = []
        last_when: str | None = None

        if self._llm.available:
            try:
                answer, results, selected, last_when = await self._reason_with_tools(
                    context, session, language.code, trace
                )
            except (LLMError, json.JSONDecodeError, ValueError) as exc:
                trace.append(
                    ReasoningStep(
                        stage="reasoning",
                        detail=f"Tool-calling reasoning failed ({exc}); falling back to one-shot planning.",
                    )
                )

        if not answer and results:
            directive = decision_gate.extract_decision_directive(results)
            if directive.verdict != "INFORMATIVE":
                trace.append(
                    ReasoningStep(
                        stage="decision_gate",
                        detail=f"Authoritative directive: {directive.verdict} ({directive.rationale})",
                    )
                )
            answer, method = await self._synthesise(context, results, language.code)
            trace.append(
                ReasoningStep(stage="synthesis", detail=f"Composed the reply from agent evidence {method}.")
            )

        # Fallback: the original plan -> route -> synthesise pipeline. Blunter,
        # but it keeps the API answering when the model is absent or misbehaving.
        if not answer:
            selected, planner = await self._plan(context.question)
            trace.append(
                ReasoningStep(
                    stage="plan",
                    detail=f"{planner} selected: {', '.join(selected)}.",
                )
            )
            # The tool path lets the model name the window; here it is read off the English question.
            when = timeframe.infer(context.question)
            if when:
                context = context.with_params({"when": when})
                last_when = when
                trace.append(
                    ReasoningStep(stage="plan", detail=f"Time window from the question: {when}.")
                )
            # Dependency-ordered rather than one flat gather.
            #
            # This branch runs precisely when the model is unavailable, so
            # recovering from a dead connector has to be a decision the code can
            # make on its own. `execution` drops a failed optional edge and
            # carries on, skips a summariser whose every source is gone instead
            # of letting it write an empty brief, and staggers the fetches so
            # six agents no longer hit the providers in the same instant — which
            # is how a 429 once took down a layer that had not caused it.
            plan = execution.build_plan(selected)

            async def run_task(name: str) -> AgentResult:
                # Raising is how the executor is told a branch died, so this
                # deliberately does not use `_run_agent`, which converts a crash
                # into a result and would hide the failure from the graph.
                return await self._agents[name].run(context)

            outcome = await execution.execute_plan(plan, run_task)

            trace.append(
                ReasoningStep(
                    stage="plan",
                    detail=(
                        f"Ran {len(selected)} agent(s) in {outcome.waves} wave(s)"
                        + (f", {outcome.replans} replan(s)" if outcome.replans else "")
                        + "."
                    ),
                )
            )

            # Rebuild the result list in the planner's order, so synthesis and
            # the trace see exactly what they saw before this change — including
            # a failed agent's error, which the graph records separately but
            # which the answer has always been allowed to mention.
            failed_by_id = {f["taskId"]: f["reason"] for f in outcome.failures}
            results = []
            for name in selected:
                found = outcome.results.get(name)
                if isinstance(found, AgentResult):
                    results.append(found)
                    continue
                task = outcome.plan.task(name)
                results.append(
                    AgentResult(
                        agent=name,
                        summary="",
                        confidence=0.0,
                        error=failed_by_id.get(
                            name,
                            (task.reason if task else None) or "did not run",
                        ),
                    )
                )

            for result in results:
                trace.append(
                    ReasoningStep(
                        stage=f"agent:{result.agent}",
                        detail=result.error or result.summary,
                    )
                )

            if outcome.degraded:
                skipped = [
                    t.id for t in outcome.plan.tasks if t.status == execution.SKIPPED
                ]
                trace.append(
                    ReasoningStep(
                        stage="degraded",
                        detail=(
                            "Answered with part of the plan. "
                            + (f"Failed: {', '.join(failed_by_id)}. " if failed_by_id else "")
                            + (f"Skipped: {', '.join(skipped)}." if skipped else "")
                        ).strip(),
                    )
                )

            # _synthesise reports which path it actually took: an LLM call can be
            # configured yet still fail, and a trace that claims otherwise would
            # misrepresent how the answer was produced.
            directive = decision_gate.extract_decision_directive(results)
            if directive.verdict != "INFORMATIVE":
                trace.append(
                    ReasoningStep(
                        stage="decision_gate",
                        detail=f"Authoritative directive: {directive.verdict} ({directive.rationale})",
                    )
                )
            answer, method = await self._synthesise(context, results, language.code)
            trace.append(
                ReasoningStep(
                    stage="synthesis",
                    detail=f"Composed the reply from agent evidence {method}.",
                )
            )

        # A derived fishing zone must never read as an official one, whatever the model wrote.
        if any(r.data.get("estimate") for r in results) and "INCOIS" not in answer.upper():
            answer = f"{answer} {await self._say(guardrails.ESTIMATE_CAVEAT, language.code)}"
            trace.append(ReasoningStep(stage="guardrail", detail="Added the caveat that the fishing zone is an estimate."))

        localised = await self._in_language(answer, language.code)
        if localised != answer:
            trace.append(
                ReasoningStep(
                    stage="guardrail",
                    detail=f"The reply came back in English; translated to '{language.code}'.",
                )
            )
            answer = localised

        # ---- 3. Remember ---------------------------------------------------
        self._memory.remember(
            session_id,
            question=question,
            answer=answer,
            latitude=latitude,
            longitude=longitude,
            last_when=last_when,
        )

        # Extract authoritative operational directive
        gate_directive = decision_gate.extract_decision_directive(results)
        directive_verdict = gate_directive.verdict

        # Collect degraded components and freshness metadata
        degraded = [r.agent for r in results if r.error or r.directive == "UNKNOWN" or r.is_stub]
        freshness: dict[str, str] = {}
        for r in results:
            for ev in r.evidence:
                if ev.observed_at and r.agent not in freshness:
                    freshness[r.agent] = ev.observed_at
        if "marine_conditions" in context.shared_observations:
            cond = context.shared_observations["marine_conditions"]
            if hasattr(cond, "fetched_at"):
                freshness["weather"] = cond.fetched_at.isoformat()

        # Determine overall execution status: "COMPLETE" | "DEGRADED" | "UNKNOWN"
        if any(r.agent in ("weather_intelligence", "risk_assessment") and (r.error or r.directive == "UNKNOWN") for r in results):
            exec_status = "UNKNOWN"
        elif degraded:
            exec_status = "DEGRADED"
        else:
            exec_status = "COMPLETE"

        return OrchestratorResponse(
            answer=answer,
            language=language.code,
            agents_used=selected,
            results=list(results),
            trace=trace,
            used_stub_data=any(result.is_stub for result in results),
            directive=directive_verdict,
            status=exec_status,
            degraded_components=degraded,
            data_freshness=freshness,
        )

    # ------------------------------------------------------- tool-calling loop

    async def _reason_with_tools(
        self,
        context: QueryContext,
        session: Session | None,
        language: str,
        trace: list[ReasoningStep],
    ) -> tuple[str, list[AgentResult], list[str], str | None]:
        """Let the model call agents, read the findings, and call again.

        Returns the final answer, every agent result gathered along the way, the
        agents used, and the last time window the model asked for. An empty
        answer tells `handle` to fall back.

        Nothing is stored on the orchestrator itself: it is a process-wide
        singleton, so per-request state kept on `self` would be clobbered by
        whoever else is asking a question at the same moment.
        """
        last_when: str | None = None
        tools = [agent.as_tool() for agent in self._agents.values()]
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self._tool_system_prompt(context, language)}
        ]
        if session:
            messages.extend(session.as_messages())
        messages.append({"role": "user", "content": _user_turn(context)})

        gathered: list[AgentResult] = []
        used: list[str] = []

        # The plan's agents run first, so the model starts from their evidence rather than choosing them.
        seed = [name for name in self._plan_by_keywords(context.question) if name in self._agents]
        when = timeframe.infer(context.question)
        seed_args = {"when": when} if when else {}
        if when:
            last_when = when
        seed_results = await asyncio.gather(
            *(self._run_agent(self._agents[name], context.with_params(seed_args)) for name in seed)
        )
        seed_calls = [
            {
                "id": f"plan-{i}",
                "type": "function",
                "function": {"name": name, "arguments": json.dumps(seed_args)},
            }
            for i, name in enumerate(seed)
        ]
        trace.append(
            ReasoningStep(
                stage="plan",
                detail=f"Planned from the question: {', '.join(seed)}" + (f" (when={when})." if when else "."),
            )
        )
        messages.append({"role": "assistant", "content": "", "tool_calls": seed_calls})
        for call, result in zip(seed_calls, seed_results):
            gathered.append(result)
            used.append(result.agent)
            trace.append(ReasoningStep(stage=f"agent:{result.agent}", detail=result.error or result.summary))
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "name": call["function"]["name"],
                    "content": self._format_findings([result]) or "no findings",
                }
            )

        for round_number in range(1, MAX_TOOL_ROUNDS + 1):
            try:
                message = await self._llm.complete_with_tools(messages, tools, temperature=0.0)
            except LLMError as exc:
                trace.append(
                    ReasoningStep(
                        stage="reasoning",
                        detail=f"Tool-calling reasoning failed ({exc}); answering from the evidence gathered.",
                    )
                )
                return "", gathered, used, last_when
            calls = message.get("tool_calls") or []

            if not calls:
                # The model is satisfied and has written the answer.
                answer = _plain((message.get("content") or "").strip())
                if answer and gathered:
                    directive = decision_gate.extract_decision_directive(gathered)
                    if directive.verdict != "INFORMATIVE":
                        answer, modified, note = decision_gate.reconcile_and_verify(answer, directive)
                        trace.append(
                            ReasoningStep(
                                stage="decision_gate",
                                detail=note,
                            )
                        )
                    trace.append(
                        ReasoningStep(
                            stage="synthesis",
                            detail=f"Answered using the LLM over the evidence of: {', '.join(used)}.",
                        )
                    )
                return answer, gathered, used, last_when

            # Assistant turn must be echoed back before its tool results.
            messages.append(
                {
                    "role": "assistant",
                    "content": message.get("content") or "",
                    "tool_calls": calls,
                }
            )

            planned: list[tuple[str, dict[str, Any], str]] = []
            for call in calls:
                fn = call.get("function") or {}
                name = fn.get("name", "")
                try:
                    args = json.loads(fn.get("arguments") or "{}")
                except json.JSONDecodeError:
                    args = {}
                # Remember the window the model chose, so a later "and the day
                # after that?" has a reference point in memory.
                if "when" in args:
                    last_when = str(args["when"])
                planned.append((name, args, call.get("id", "")))

            described = ", ".join(
                f"{name}({', '.join(f'{k}={v}' for k, v in args.items()) or 'defaults'})"
                for name, args, _ in planned
            )
            trace.append(
                ReasoningStep(
                    stage=f"plan:round-{round_number}",
                    detail=f"The model called: {described}.",
                )
            )

            # Run this round's calls concurrently; they are independent.
            async def invoke(name: str, args: dict[str, Any]) -> AgentResult:
                agent = self._agents.get(name)
                if agent is None:
                    return AgentResult(
                        agent=name or "unknown",
                        summary="",
                        confidence=0.0,
                        error=f"No such agent: {name!r}",
                    )
                return await self._run_agent(agent, context.with_params(args))

            round_results = await asyncio.gather(
                *(invoke(name, args) for name, args, _ in planned)
            )

            for (name, _args, call_id), result in zip(planned, round_results):
                gathered.append(result)
                if result.agent not in used:
                    used.append(result.agent)
                trace.append(
                    ReasoningStep(
                        stage=f"agent:{result.agent}",
                        detail=result.error or result.summary,
                    )
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call_id,
                        "name": name,
                        "content": self._format_findings([result]) or "no findings",
                    }
                )

        # Out of rounds. Rather than loop forever, ask once for a final answer
        # from what was gathered — the evidence is real even if the model kept
        # wanting more of it.
        trace.append(
            ReasoningStep(
                stage="reasoning",
                detail=(
                    f"Reached the {MAX_TOOL_ROUNDS}-round tool limit; answering from "
                    "the evidence gathered so far."
                ),
            )
        )
        answer, _method = await self._synthesise(context, gathered, language)
        return answer, gathered, used, last_when

    def _tool_system_prompt(self, context: QueryContext, language: str) -> str:
        where = (
            f"The user is at latitude {context.latitude}, longitude {context.longitude}."
            if context.latitude is not None and context.longitude is not None
            else "The user's position is unknown; agents will use their own default."
        )
        glossary = glossary_for(language)
        prompt = (
            "You are ORCA, a marine advisor for Indian fishermen. Only discuss the sea, "
            "fishing, weather and marine safety; politely decline anything else.\n\n"
            f"{where} Never ask the user for their location — you already have it, "
            "and they are often at sea and cannot type.\n\n"
            "Call the specialist agents to get real data before you answer. Choose "
            "the time window the user actually asked about — if they say 'the day "
            "after tomorrow', pass when='day_after_tomorrow', not today. If a "
            "result makes another check worthwhile, call again. If the user is "
            "following up on an earlier message, resolve what they mean from the "
            "conversation above.\n\n"
            f"{_ROUTING_GUIDE}\nIn your first round, call every agent listed for the kind of question asked.\n\n"
            "Answer using ONLY what the agents returned — never invent a number, and "
            "say a limit is exceeded only where an agent said so. Never name the agents or "
            "tools; speak as ORCA. Keep an agent's caveats, "
            "such as a figure being an estimate rather than an official advisory. "
            "Be concrete and brief (2-4 short sentences), say plainly whether it is "
            "safe, and write in simple words a fisherman can act on. If any specialist agent "
            "reports conditions are unsafe, or a cyclone, monsoon ban, or border breach is present, "
            "you MUST issue a clear warning and advise against venturing out; never contradict an "
            "agent's safety verdict. If an agent "
            "reports the forecast does not reach that far, say so rather than "
            "answering about a nearer day.\n\n"
            f"Write your entire reply in this language: {language}. Compose it "
            "directly in that language rather than translating an English answer."
        )
        return prompt + ("\n\n" + glossary if glossary else "")

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
                {
                    "role": "system",
                    "content": _PLANNER_SYSTEM.format(agents=catalogue, routing=_ROUTING_GUIDE),
                },
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
        directive = decision_gate.extract_decision_directive(results)
        directive_prompt = decision_gate.format_directive_for_prompt(directive)

        if not self._llm.available:
            answer, note = await self._localised_template(results, language)
            if directive.verdict != "INFORMATIVE":
                answer, _mod, _gate_note = decision_gate.reconcile_and_verify(answer, directive)
            return answer, f"using a template (no LLM configured){note}"

        glossary = glossary_for(language)
        system = (
            "You are ORCA, a marine advisor for Indian fishermen. Answer using "
            "ONLY the findings provided — never invent numbers, and say a limit is "
            "exceeded only where a finding says so, and keep caveats such as a figure being an "
            "estimate rather than an official advisory. Never name the agents; speak as ORCA. "
            "Be concrete and "
            "brief (2-4 short sentences), say plainly whether it is safe, and "
            "write in simple words a fisherman can act on.\n\n"
            f"Write your entire reply in this language: {language}. "
            "Do not translate an English answer — compose it directly in that "
            "language."
        )
        if directive_prompt:
            system += "\n\n" + directive_prompt
        if glossary:
            system += "\n\n" + glossary

        try:
            answer = await self._llm.complete(
                [
                    {"role": "system", "content": system},
                    {
                        "role": "user",
                        "content": (
                            f"Question: {_user_turn(context)}\n\n"
                            f"Findings from specialist agents:\n{findings}"
                        ),
                    },
                ],
                temperature=0.3,
                max_tokens=400,
            )
            cleaned = _plain(answer)
            if directive.verdict != "INFORMATIVE":
                cleaned, modified, note = decision_gate.reconcile_and_verify(cleaned, directive)
                method = "using the LLM (decision gate reconciled)" if modified else "using the LLM"
                return cleaned, method
            return cleaned, "using the LLM"
        except LLMError as exc:
            answer, note = await self._localised_template(results, language)
            if directive.verdict != "INFORMATIVE":
                answer, _mod, _gate_note = decision_gate.reconcile_and_verify(answer, directive)
            return answer, f"using a template after the LLM call failed ({exc}){note}"

    async def _localised_template(
        self, results: list[AgentResult], language: str
    ) -> tuple[str, str]:
        """The template reply in the user's language, plus a note for the trace."""
        parts = [r.summary for r in results if r.summary] or ["No specialist could answer that yet."]
        if self._translator is None or not self._translator.available:
            return " ".join(parts), ""
        translated = (await localise({"summary": parts}, language, self._translator))["summary"]
        if translated == parts:
            return " ".join(parts), "" if language == "en" else f"; it could not be translated to {language}"
        return " ".join(translated), f", translated to {language} by Sarvam"

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
