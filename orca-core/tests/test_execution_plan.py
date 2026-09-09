"""The execution graph, tested where it matters: when things are failing.

A runner that works when every agent succeeds is not worth much — a flat gather
already did that. What is being checked here is the behaviour on the bad path,
because this code exists for the case where the model is gone and a connector
is down at the same time.
"""

import asyncio

import pytest

from app.agents import execution


def run(coro):
    return asyncio.run(coro)


def ids(plan, status):
    return sorted(t.id for t in plan.tasks if t.status == status)


# --- Shape -------------------------------------------------------------------


def test_edges_are_pruned_to_the_selected_agents():
    """A narrow plan must not acquire prerequisites it never asked for.

    Asking only about a ten-year trend should not drag in weather: the graph
    describes what to do with the agents that were chosen, and widening the
    plan is the orchestrator's decision, not this module's.
    """
    plan = execution.build_plan(["historical_trends"])
    assert [t.id for t in plan.tasks] == ["historical_trends"]
    assert plan.tasks[0].depends_on == []


def test_risk_is_ordered_after_the_agents_it_weighs():
    plan = execution.build_plan(
        ["risk_assessment", "weather_intelligence", "ocean_analytics"]
    )
    risk = plan.task("risk_assessment")
    assert sorted(risk.depends_on) == ["ocean_analytics", "weather_intelligence"]


def test_a_missing_dependency_is_not_invented():
    """Selecting risk without ocean leaves only the edge that can be honoured."""
    plan = execution.build_plan(["risk_assessment", "weather_intelligence"])
    assert plan.task("risk_assessment").depends_on == ["weather_intelligence"]


# --- Ordering ----------------------------------------------------------------


def test_dependencies_run_in_waves_not_all_at_once():
    plan = execution.build_plan(
        ["weather_intelligence", "ocean_analytics", "risk_assessment"]
    )
    order: list[str] = []

    async def handler(task_id):
        order.append(task_id)
        await asyncio.sleep(0)
        return f"{task_id}-ok"

    outcome = run(execution.execute_plan(plan, handler))
    assert outcome.waves == 2
    assert order.index("risk_assessment") == 2
    assert not outcome.degraded


# --- Failure -----------------------------------------------------------------


def test_an_optional_failure_degrades_rather_than_blocks():
    """Weather dying must not stop risk, which fetches its own conditions."""
    plan = execution.build_plan(
        ["weather_intelligence", "ocean_analytics", "risk_assessment"]
    )

    async def handler(task_id):
        if task_id == "weather_intelligence":
            raise RuntimeError("Open-Meteo timed out")
        return f"{task_id}-ok"

    outcome = run(execution.execute_plan(plan, handler))

    assert "risk_assessment" in outcome.results
    assert ids(outcome.plan, execution.FAILED) == ["weather_intelligence"]
    assert outcome.degraded
    assert outcome.replans == 1
    assert "Open-Meteo timed out" in outcome.failures[0]["reason"]
    # The loss is stated on the task that had to carry on without it.
    assert "degraded" in outcome.plan.task("risk_assessment").reason.lower()


def test_a_summariser_with_nothing_left_is_skipped_not_run_empty():
    """The case that motivated the whole mechanism.

    A brief composed from zero surviving sources reads exactly like a brief
    composed from five. Saying "skipped, every source failed" is the only
    honest output.
    """
    plan = execution.build_plan(
        ["weather_intelligence", "ocean_analytics", "risk_assessment", "reporting"]
    )

    async def handler(task_id):
        if task_id == "reporting":
            return "brief"
        raise RuntimeError("connector down")

    outcome = run(execution.execute_plan(plan, handler))

    assert "reporting" not in outcome.results
    assert "reporting" in ids(outcome.plan, execution.SKIPPED)
    assert "every source" in outcome.plan.task("reporting").reason


def test_a_summariser_still_runs_on_a_partial_view():
    """Losing some sources is not losing all of them."""
    plan = execution.build_plan(
        ["weather_intelligence", "ocean_analytics", "risk_assessment", "visualization"]
    )

    async def handler(task_id):
        if task_id == "ocean_analytics":
            raise RuntimeError("ERDDAP 500")
        return f"{task_id}-ok"

    outcome = run(execution.execute_plan(plan, handler))
    assert "visualization" in outcome.results
    assert outcome.degraded


def test_replanning_is_capped():
    """Every optional branch failing must terminate, not spin."""
    plan = execution.build_plan(
        [
            "weather_intelligence",
            "ocean_analytics",
            "geospatial",
            "cyclone_watch",
            "historical_trends",
        ]
    )

    async def handler(task_id):
        raise RuntimeError("everything is down")

    outcome = run(execution.execute_plan(plan, handler, max_replans=2))
    assert outcome.replans <= 2
    assert len(outcome.failures) == 5
    assert not outcome.results


def test_execution_terminates_when_every_task_fails():
    plan = execution.build_plan(["weather_intelligence"])

    async def handler(task_id):
        raise RuntimeError("down")

    outcome = run(asyncio.wait_for(execution.execute_plan(plan, handler), timeout=5))
    assert ids(outcome.plan, execution.FAILED) == ["weather_intelligence"]


# --- Determinism -------------------------------------------------------------


def test_recovery_needs_no_model():
    """The point of the module: no LLM is consulted to route around a failure.

    The executor is handed nothing but a graph and a callable, so there is no
    seam through which a model call could enter. This test states that as a
    contract rather than leaving it as an accident of the current code.
    """
    plan = execution.build_plan(["weather_intelligence", "ocean_analytics"])
    calls: list[str] = []

    async def handler(task_id):
        calls.append(task_id)
        if task_id == "weather_intelligence":
            raise RuntimeError("no key")
        return "ok"

    outcome = run(execution.execute_plan(plan, handler))
    assert calls == ["weather_intelligence", "ocean_analytics"] or sorted(calls) == [
        "ocean_analytics",
        "weather_intelligence",
    ]
    assert outcome.degraded
    assert outcome.plan.to_dict()["tasks"]


@pytest.mark.parametrize("selected", [[], ["unknown_agent"]])
def test_empty_and_unknown_plans_do_not_crash(selected):
    plan = execution.build_plan(selected)

    async def handler(task_id):
        return "ok"

    outcome = run(execution.execute_plan(plan, handler))
    assert outcome.replans == 0
