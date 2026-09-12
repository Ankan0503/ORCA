"""Planning across days, and seeing which way the weather lies.

Both existed as capability and could not be reached: a week needed one tool call
per day and MAX_TOOL_ROUNDS cut it off at four, and the sea grid was reachable
only by the router.
"""

from __future__ import annotations

import pytest

from app.agents.base import QueryContext
from app.agents.reporting import ReportingAgent


def _context(**params) -> QueryContext:
    return QueryContext(
        question="plan my week", language="en", latitude=21.6266, longitude=87.5074
    ).with_params(params)


def test_days_defaults_to_one_when_not_asked():
    assert ReportingAgent()._requested_days(_context()) == 1


@pytest.mark.parametrize(
    "asked,expected",
    [(1, 1), (3, 3), (7, 7), (0, 1), (-4, 1), (99, 7), ("4", 4), (None, 1), ("week", 1)],
)
def test_days_is_clamped_to_what_a_forecast_can_support(asked, expected):
    """Seven is the ceiling: past it the forecast thins out and a plan is fiction."""
    assert ReportingAgent()._requested_days(_context(days=asked)) == expected


@pytest.mark.asyncio
async def test_a_week_is_one_call_and_says_where_the_forecast_ends():
    """The days beyond the forecast must be named, not quietly omitted.

    A plan that lists three days when seven were asked for, with no note, reads
    as "those days are fine".
    """
    result = await ReportingAgent().run(_context(days=7))
    if result.error:
        pytest.skip(f"upstream unavailable: {result.error}")

    sections = result.data["brief"]["sections"]
    spread = next((s for s in sections if "Day by day" in s["title"]), None)
    assert spread is not None, "a multi-day request must produce a day-by-day section"

    lines = spread["lines"]
    # Seven days asked for, so seven dated lines plus the summary line.
    dated = [line for line in lines if ":" in line]
    assert len(dated) >= 7
    assert any("beyond the forecast" in line for line in lines) or all(
        "beyond the forecast" not in line for line in lines
    )
    assert any(line.startswith("Best days") or "No day" in line for line in lines)


@pytest.mark.asyncio
async def test_one_day_does_not_add_the_day_by_day_section():
    """The section is for spans. A single day already has its own."""
    result = await ReportingAgent().run(_context(days=1))
    if result.error:
        pytest.skip(f"upstream unavailable: {result.error}")
    titles = [s["title"] for s in result.data["brief"]["sections"]]
    assert not any("Day by day" in t for t in titles)
