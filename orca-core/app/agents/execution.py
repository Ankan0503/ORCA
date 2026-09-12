"""A dependency-ordered execution plan, and a runner for it.

Why this exists, given the orchestrator already reasons in rounds
-----------------------------------------------------------------
``Orchestrator._reason_with_tools`` is the good path: the model picks agents,
reads what they found, and picks again. It already replans, and already runs a
round's calls through ``asyncio.gather``.

But it needs the model. When Groq is absent, rate-limited or simply slow, the
orchestrator drops to its fallback — plan once, run every selected agent in a
single flat gather, synthesise — and that path has two problems this module
fixes.

The first is honesty. In a flat gather a failed agent becomes an ``AgentResult``
carrying an error string, and the answer is composed from whatever survived
without ever saying which branch was lost or why. A plan with stated
dependencies can say "the brief was skipped because every source it summarises
failed" instead of quietly producing a thin one.

The second is load. Every agent fetches its own data — ``risk_assessment`` calls
``fetch_marine_conditions`` itself rather than reading what ``weather_intelligence``
found — so a flat gather fires every request at the providers at once. That is
what earned a 429 from Open-Meteo before, and the 429 took a layer down with it
that had nothing to do with the agent that caused it. Waves stagger the load for
free.

**The dependency edges here are ordering and degradation semantics, not data
flow.** Nothing downstream reads an upstream result today, because agents are
self-sufficient by design. Saying ``risk_assessment`` depends on
``weather_intelligence`` means "run it after, and if weather is gone, say the
risk view is degraded" — it does not mean risk consumes weather's numbers. That
distinction is written down because a reader would otherwise reasonably assume
the stronger claim.

The shape is ported from HackHeritage's ``agenticPlanner.ts`` and
``agenticExecutor.ts``, which had the right idea: an explicit task graph with
required and optional edges, wave execution, and deterministic recovery that
costs no model call. What is *not* carried across is that planner's several
hundred characters of regular expressions for guessing intent — ORCA already
chooses agents with an LLM planner and a keyword fallback, and a second,
divergent intent matcher would be one more thing to keep in agreement.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Awaitable, Callable

# A task that fails, and every task that then cannot run, must not be able to
# spin the executor. Three attempts is enough to route around a couple of dead
# connectors and small enough that a pathological plan still terminates.
MAX_REPLANS = 3

PENDING = "pending"
RUNNING = "running"
COMPLETED = "completed"
FAILED = "failed"
SKIPPED = "skipped"


@dataclass
class Task:
    """One agent to run, and what has to happen before it."""

    id: str
    label: str
    depends_on: list[str] = field(default_factory=list)
    # A required dependency failing takes its dependents down with it. An
    # optional one failing is dropped from their dependency lists, and they run
    # in degraded mode with the loss recorded.
    required: bool = False
    enabled: bool = True
    status: str = PENDING
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "dependsOn": list(self.depends_on),
            "required": self.required,
            "status": self.status,
            "reason": self.reason,
        }


@dataclass
class Plan:
    """A run of tasks with the edges between them."""

    plan_id: str
    intent: str
    rationale: str
    tasks: list[Task]
    generated_at: str

    def task(self, task_id: str) -> Task | None:
        return next((t for t in self.tasks if t.id == task_id), None)

    def to_dict(self) -> dict:
        return {
            "planId": self.plan_id,
            "intent": self.intent,
            "rationale": self.rationale,
            "generatedAt": self.generated_at,
            "tasks": [t.to_dict() for t in self.tasks],
        }


# --- What depends on what ----------------------------------------------------
#
# Read as "run me after these, and tell the user if they are missing".
#
# The four gatherers at the top have no dependencies: each reaches its own
# source and none of them needs another's answer. Everything below them is
# either a judgement over what was gathered or a rendering of it, and running
# those first would mean judging nothing.
_EDGES: dict[str, list[str]] = {
    "weather_intelligence": [],
    "ocean_analytics": [],
    "geospatial": [],
    "cyclone_watch": [],
    "historical_trends": [],
    "data_discovery": [],
    # Retrieval reads documents, not conditions, so it waits for nothing.
    "evidence_retrieval": [],
    # Plans its passage from its own fetches, so it waits for nothing.
    "route_planning": [],
    # Risk is the combination step — "the worst factor decides" — so it belongs
    # after the two agents whose factors it weighs, even though it fetches its
    # own copy of the conditions.
    "risk_assessment": ["weather_intelligence", "ocean_analytics"],
    # These two have nothing to say until something has been found.
    "visualization": ["weather_intelligence", "ocean_analytics", "risk_assessment"],
    "reporting": [
        "weather_intelligence",
        "ocean_analytics",
        "risk_assessment",
        "geospatial",
        "cyclone_watch",
        "evidence_retrieval",
    ],
}

# Agents that produce, rather than summarise, what other agents produced. If
# every one of a summariser's dependencies is gone there is nothing left to
# summarise, and emitting an empty brief would be worse than saying so.
_SUMMARISERS = frozenset({"visualization", "reporting"})


def _new_id(prefix: str) -> str:
    return f"{prefix}-{int(time.time())}-{uuid.uuid4().hex[:5]}"


def build_plan(selected: list[str], intent: str = "marine_intelligence") -> Plan:
    """Turn the planner's flat list of agents into a graph.

    Only edges between agents that were actually selected are kept. A question
    about historical trends alone should not acquire a weather dependency it has
    no use for, and pruning here is what stops the graph from quietly widening
    the plan the orchestrator chose.
    """
    chosen = [name for name in dict.fromkeys(selected) if name in _EDGES or True]
    present = set(chosen)

    tasks: list[Task] = []
    for name in chosen:
        deps = [d for d in _EDGES.get(name, []) if d in present]
        tasks.append(
            Task(
                id=name,
                label=name.replace("_", " "),
                depends_on=deps,
                # A gatherer is required only where something depends on it;
                # that is decided per-edge below rather than declared here, so
                # a plan that selected one agent has no phantom requirements.
                required=False,
                reason=(
                    f"Runs after {', '.join(deps)}." if deps else "No prerequisites."
                ),
            )
        )

    # A summariser's dependencies are required *collectively*: it can lose some
    # and still be worth running, but not all of them.
    for task in tasks:
        if task.id in _SUMMARISERS and task.depends_on:
            task.reason = f"Summarises {', '.join(task.depends_on)}."

    rationale = "Dependency order: " + " | ".join(
        f"{t.id}<-{','.join(t.depends_on) or 'none'}" for t in tasks
    )
    return Plan(
        plan_id=_new_id("plan"),
        intent=intent,
        rationale=rationale,
        tasks=tasks,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


def runnable_tasks(plan: Plan) -> list[Task]:
    """Tasks whose turn it is: enabled, pending, prerequisites resolved.

    A dependency counts as resolved when it completed *or* when it is no longer
    enabled, because a branch that was dropped should not hold up the rest of
    the plan forever.
    """
    ready: list[Task] = []
    for task in plan.tasks:
        if not task.enabled or task.status != PENDING:
            continue
        if all(
            (dep := plan.task(dep_id)) is not None
            and (dep.status == COMPLETED or not dep.enabled)
            for dep_id in task.depends_on
        ):
            ready.append(task)
    return ready


def mark_blocked(plan: Plan) -> bool:
    """Skip anything that can no longer run, and say why.

    Two cases. A required dependency that failed blocks its dependents
    outright. A summariser whose dependencies have *all* gone is skipped too:
    it would otherwise run against nothing and produce a confident, empty
    brief, which is the sort of output that looks like an answer and is not.
    """
    changed = False
    for task in plan.tasks:
        if not task.enabled or task.status != PENDING:
            continue

        blocked = any(
            (dep := plan.task(dep_id)) is not None
            and dep.status in (FAILED, SKIPPED)
            and dep.required
            for dep_id in task.depends_on
        )

        # "Every source is gone" means gone, not merely not-yet-run. Testing
        # for "not completed" fires on the first pass, before anything has had
        # a turn, and skips the summariser at the moment the plan is built.
        starved = False
        if task.id in _SUMMARISERS and task.depends_on:
            starved = all(
                (dep := plan.task(dep_id)) is not None
                and (dep.status in (FAILED, SKIPPED) or not dep.enabled)
                for dep_id in task.depends_on
            )

        if blocked or starved:
            task.status = SKIPPED
            task.enabled = False
            task.reason = (
                "Skipped: a required prerequisite failed."
                if blocked
                else "Skipped: every source it summarises is unavailable."
            )
            changed = True
    return changed


def replan_after_failure(plan: Plan, failed_id: str, reason: str) -> Plan:
    """Route around a failure, without asking a model how.

    This is the point of the whole module. The orchestrator's own replanning
    goes back to the LLM, which is precisely what is unavailable when the
    fallback path is running. Dropping a dead optional edge is a decision that
    can be made from the graph alone.
    """
    tasks = [
        Task(
            id=t.id,
            label=t.label,
            depends_on=list(t.depends_on),
            required=t.required,
            enabled=t.enabled,
            status=t.status,
            reason=t.reason,
        )
        for t in plan.tasks
    ]
    rebuilt = Plan(
        plan_id=_new_id("replan"),
        intent=plan.intent,
        rationale=f"{plan.rationale} | replanned after {failed_id}: {reason}",
        tasks=tasks,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )

    failed = rebuilt.task(failed_id)
    if failed is not None:
        failed.status = FAILED
        failed.enabled = False
        failed.reason = f"Failed: {reason}"

    for task in rebuilt.tasks:
        if not task.enabled or task.id == failed_id:
            continue
        if failed_id not in task.depends_on:
            continue
        if failed is not None and failed.required:
            task.status = SKIPPED
            task.enabled = False
            task.reason = f"Skipped: required prerequisite {failed_id} failed."
        else:
            task.depends_on = [d for d in task.depends_on if d != failed_id]
            task.reason = (
                f"{task.reason} Running degraded: {failed_id} unavailable."
            ).strip()
    return rebuilt


@dataclass
class ExecutionOutcome:
    plan: Plan
    results: dict[str, object]
    failures: list[dict[str, str]]
    replans: int
    waves: int

    @property
    def degraded(self) -> bool:
        return bool(self.failures) or any(
            t.status == SKIPPED for t in self.plan.tasks
        )

    def to_dict(self) -> dict:
        return {
            "plan": self.plan.to_dict(),
            "failures": self.failures,
            "replans": self.replans,
            "waves": self.waves,
            "degraded": self.degraded,
        }


Handler = Callable[[str], Awaitable[object]]


async def execute_plan(
    plan: Plan,
    handler: Handler,
    max_replans: int = MAX_REPLANS,
) -> ExecutionOutcome:
    """Run the graph, one wave of ready tasks at a time.

    ``handler`` is given a task id and returns whatever that agent produced;
    raising is how it reports failure. Everything ready starts together, so
    within a wave this is no slower than the flat gather it replaces, while the
    edges between waves keep a summariser from running before there is anything
    to summarise and keep six agents from hitting the providers in the same
    instant.
    """
    current = plan
    results: dict[str, object] = {}
    failures: list[dict[str, str]] = []
    replans = 0
    waves = 0

    while True:
        mark_blocked(current)
        ready = runnable_tasks(current)
        if not ready:
            break

        waves += 1
        for task in ready:
            task.status = RUNNING

        outcomes = await asyncio.gather(
            *(handler(task.id) for task in ready), return_exceptions=True
        )

        for task, outcome in zip(ready, outcomes):
            if isinstance(outcome, BaseException):
                message = f"{type(outcome).__name__}: {outcome}"
                task.status = FAILED
                task.enabled = False
                task.reason = f"Failed: {message}"
                failures.append({"taskId": task.id, "reason": message})
            else:
                task.status = COMPLETED
                results[task.id] = outcome

        # Only the wave that just ran is inspected. Scanning the whole plan
        # would find failures that a previous replan already disabled and
        # replan them again, burning the budget without changing the graph —
        # a trap the original implementation hit and left a note about.
        failed_optional = next(
            (t for t in ready if t.status == FAILED and not t.required), None
        )
        if failed_optional is not None and replans < max_replans:
            reason = next(
                (f["reason"] for f in failures if f["taskId"] == failed_optional.id),
                failed_optional.reason,
            )
            current = replan_after_failure(current, failed_optional.id, reason)
            replans += 1
            continue

        if not any(t.enabled and t.status == PENDING for t in current.tasks):
            break

    # A task still pending here could only be waiting on something that never
    # completed. Marking it explicitly is what lets the response state the gap
    # rather than leave it as silence.
    mark_blocked(current)
    return ExecutionOutcome(
        plan=current,
        results=results,
        failures=failures,
        replans=replans,
        waves=waves,
    )
