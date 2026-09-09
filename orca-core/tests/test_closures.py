"""Tests for fishing closures.

The ban dates are quoted from the Department of Fisheries via PIB (25 Mar 2025):
East Coast 15 April - 14 June, West Coast 1 June - 31 July. They are legal
dates, not estimates, so the boundaries are tested exactly — being wrong by one
day on either edge either tells a fisherman he may sail when he may not, or
costs him a legal day at sea.
"""

from datetime import date

from app.tools.closures import ban_status, coast_for, protected_areas_near

# Digha (east) and Kochi (west).
EAST_LON = 87.5
WEST_LON = 76.0


def test_coast_is_chosen_by_longitude():
    assert coast_for(EAST_LON) == "East Coast"
    assert coast_for(WEST_LON) == "West Coast"
    # Andamans follow the east-coast dates, Lakshadweep the west.
    assert coast_for(92.8) == "East Coast"
    assert coast_for(72.6) == "West Coast"


def test_east_coast_ban_boundaries_are_exact():
    """15 April to 14 June inclusive, per the order."""
    assert ban_status(EAST_LON, date(2026, 4, 14)).active is False  # day before
    assert ban_status(EAST_LON, date(2026, 4, 15)).active is True   # first day
    assert ban_status(EAST_LON, date(2026, 6, 14)).active is True   # last day
    assert ban_status(EAST_LON, date(2026, 6, 15)).active is False  # day after


def test_west_coast_ban_boundaries_are_exact():
    """1 June to 31 July inclusive, per the order."""
    assert ban_status(WEST_LON, date(2026, 5, 31)).active is False
    assert ban_status(WEST_LON, date(2026, 6, 1)).active is True
    assert ban_status(WEST_LON, date(2026, 7, 31)).active is True
    assert ban_status(WEST_LON, date(2026, 8, 1)).active is False


def test_coasts_have_different_windows():
    """On 20 April the east coast is closed while the west is still open."""
    on = date(2026, 4, 20)
    assert ban_status(EAST_LON, on).active is True
    assert ban_status(WEST_LON, on).active is False


def test_days_remaining_counts_to_the_last_legal_day():
    status = ban_status(EAST_LON, date(2026, 6, 10))
    assert status.active is True
    assert status.days_remaining == 4  # 10th -> 14th


def test_after_the_window_it_points_at_next_year():
    """In August the east-coast ban is over, so the next one is in the new year."""
    status = ban_status(EAST_LON, date(2026, 8, 1))
    assert status.active is False
    assert status.start == date(2027, 4, 15)
    assert status.days_until > 0


def test_upcoming_ban_is_counted_down():
    status = ban_status(EAST_LON, date(2026, 4, 1))
    assert status.active is False
    assert status.days_until == 14
    assert status.start == date(2026, 4, 15)


def test_exemption_is_always_stated():
    """The ban does not apply to traditional non-motorized craft, and ORCA must
    never quietly decide that it does."""
    active = ban_status(EAST_LON, date(2026, 5, 1))
    assert "non-motorized" in active.message
    assert "non-motorized" in active.to_dict()["exemption"]


def test_open_sea_is_not_inside_a_protected_area():
    """A point far offshore must not match any sanctuary."""
    assert protected_areas_near(18.0, 88.0, within_km=5.0) == []
