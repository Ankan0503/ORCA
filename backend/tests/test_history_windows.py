"""Tests for the seasonal windows the historical comparison is built on.

The trend is a comparison between years, so it is only worth anything if every
year is given the same span of the same months. Getting that wrong does not
raise — it quietly produces a number, and the number is a fabricated trend.

This is not hypothetical. The first implementation centred each window on today
and clipped the current year to whatever the archive had published, which left
2026 with eleven days of late August against thirty-one days of late August into
September for every other year. Off Bengal that is peak monsoon against the
easing after it, and it manufactured an anomaly of +10 km/h of wind and
+15 mm/day of rain out of nothing but the calendar.
"""

from datetime import date, timedelta

from app.tools.history import ERA5_LAG_DAYS, WINDOW_DAYS, _windows


def test_every_year_gets_an_identical_span():
    windows = _windows(10, date(2026, 9, 8))
    lengths = {(end - start).days for _, start, end in windows}
    assert len(lengths) == 1, f"windows differ in length: {lengths}"
    assert lengths.pop() == 2 * WINDOW_DAYS


def test_every_year_covers_the_same_calendar_days():
    windows = _windows(10, date(2026, 9, 8))
    starts = {(s.month, s.day) for _, s, _ in windows}
    ends = {(e.month, e.day) for _, _, e in windows}
    assert len(starts) == 1, f"windows start on different dates: {starts}"
    assert len(ends) == 1, f"windows end on different dates: {ends}"


def test_the_window_stops_at_published_data():
    today = date(2026, 9, 8)
    windows = _windows(10, today)
    _, _, newest_end = windows[-1]
    assert newest_end == today - timedelta(days=ERA5_LAG_DAYS)


def test_one_window_per_year_requested_plus_the_current_one():
    windows = _windows(10, date(2026, 9, 8))
    years = [year for year, _, _ in windows]
    assert years == sorted(years), "windows should run oldest to newest"
    assert len(years) == 11
    assert years[-1] == 2026


def test_a_window_crossing_new_year_keeps_its_width():
    # Mid January: 6 days of archive lag then 30 days back lands in December.
    windows = _windows(5, date(2026, 1, 20))
    lengths = {(end - start).days for _, start, end in windows}
    assert lengths == {2 * WINDOW_DAYS}
    _, start, end = windows[-1]
    assert start.year == end.year - 1


def test_a_leap_day_anchor_does_not_raise():
    windows = _windows(8, date(2028, 3, 5))  # window reaches back over 29 Feb
    assert len(windows) == 9
    assert {(end - start).days for _, start, end in windows} == {2 * WINDOW_DAYS}
