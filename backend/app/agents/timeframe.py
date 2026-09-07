"""Turning "tomorrow morning" into an actual slice of the forecast.

The weather agent used to assess a hardcoded "next 12 hours plus tomorrow
morning" for every question ever asked. A user asking about the day after
tomorrow got a confident answer about tomorrow, and nothing in the reply
admitted the substitution.

This module is what the planner configures instead. It resolves a named window
into concrete start and end times in the forecast's own local timezone, and
reports how many forecast days must be fetched to cover it — because asking for
the day after tomorrow inside a three-day forecast quietly returns nothing for
the tail of the window.

Windows are deliberately shaped around a fishing day rather than a calendar one:
"morning" is the pre-dawn-to-late-morning stretch when small boats put out, and
"tonight" spans the evening into the small hours rather than stopping at
midnight.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

# Fishing-day hours, not calendar hours.
_MORNING = (5, 11)
_AFTERNOON = (11, 17)
_EVENING_START = 17
_NIGHT_END = 5


@dataclass(frozen=True)
class Window:
    """A resolved slice of forecast time."""

    label: str
    start: datetime
    end: datetime
    # The "now" this window was resolved against. Forecast length has to be
    # measured from today, not from the window's own start: a six-hour window
    # two days out spans well under a day but still needs three days fetched.
    origin: datetime

    @property
    def forecast_days_needed(self) -> int:
        """Days of forecast that must be fetched for `end` to be covered."""
        days_ahead = (self.end.date() - self.origin.date()).days
        # +1 to include today itself, +1 more for headroom so the final hours of
        # the window are never clipped by an off-by-one at the forecast's edge.
        return max(2, days_ahead + 2)


# Every window the planner may ask for. Kept in one place so the tool schema and
# the resolver cannot drift apart — the schema is generated from these keys.
WINDOW_KEYS = (
    "now",
    "today",
    "today_morning",
    "today_afternoon",
    "tonight",
    "tomorrow",
    "tomorrow_morning",
    "tomorrow_afternoon",
    "tomorrow_night",
    "day_after_tomorrow",
    "day_after_tomorrow_morning",
    "next_3_days",
)

WINDOW_DESCRIPTION = (
    "Which slice of time to assess. Use the window the user actually asked "
    "about: 'tomorrow_morning' for a dawn trip tomorrow, 'day_after_tomorrow' "
    "when they say the day after tomorrow, 'now' for the next few hours. "
    "Defaults to 'now' if the user did not say."
)


def _day(base: datetime, offset: int) -> datetime:
    return (base + timedelta(days=offset)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )


def resolve(window: str | None, now: datetime) -> Window:
    """Resolve a named window against the forecast's local 'now'.

    An unknown or missing name resolves to the next 12 hours rather than
    raising: a planner that invents a window name should still get a usable,
    clearly-labelled answer instead of an error the user would see.
    """
    key = (window or "now").strip().lower()

    def span(offset: int, from_hour: int, to_hour: int, label: str) -> Window:
        start = _day(now, offset) + timedelta(hours=from_hour)
        end = _day(now, offset) + timedelta(hours=to_hour)
        # Never assess time that has already passed.
        return Window(label=label, start=max(start, now), end=end, origin=now)

    if key == "now":
        return Window("the next 12 hours", now, now + timedelta(hours=12), origin=now)
    if key == "today":
        return Window("the rest of today", now, _day(now, 1), origin=now)
    if key == "today_morning":
        return span(0, *_MORNING, "this morning")
    if key == "today_afternoon":
        return span(0, *_AFTERNOON, "this afternoon")
    if key == "tonight":
        return Window(
            "tonight",
            max(_day(now, 0) + timedelta(hours=_EVENING_START), now),
            _day(now, 1) + timedelta(hours=_NIGHT_END),
            origin=now,
        )
    if key == "tomorrow":
        return Window("tomorrow", _day(now, 1), _day(now, 2), origin=now)
    if key == "tomorrow_morning":
        return span(1, *_MORNING, "tomorrow morning")
    if key == "tomorrow_afternoon":
        return span(1, *_AFTERNOON, "tomorrow afternoon")
    if key == "tomorrow_night":
        return Window(
            "tomorrow night",
            _day(now, 1) + timedelta(hours=_EVENING_START),
            _day(now, 2) + timedelta(hours=_NIGHT_END),
            origin=now,
        )
    if key == "day_after_tomorrow":
        return Window("the day after tomorrow", _day(now, 2), _day(now, 3), origin=now)
    if key == "day_after_tomorrow_morning":
        return span(2, *_MORNING, "the morning of the day after tomorrow")
    if key == "next_3_days":
        return Window("the next 3 days", now, _day(now, 3), origin=now)

    return Window("the next 12 hours", now, now + timedelta(hours=12), origin=now)
