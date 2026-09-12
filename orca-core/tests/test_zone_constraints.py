"""The join that makes a constrained zone question answerable.

Where the fish are, where the border and the sanctuaries are, and how far a boat
gets in an hour lived in three places and were never intersected. A fisherman who
asked for all three got three lists.
"""

from __future__ import annotations

from app.agents.ocean import Candidate, filter_candidates
from app.tools.routing import DEFAULT_BOAT_SPEED_KMH


def _candidate(lat: float, lon: float, km: float, label: str = "zone") -> Candidate:
    return Candidate(latitude=lat, longitude=lon, distance_km=km, label=label)


def test_range_excludes_and_says_why():
    out = filter_candidates(
        [_candidate(21.37, 87.67, 33.0, "near"), _candidate(21.0, 88.0, 70.0, "far")],
        max_distance_km=45.0,
    )
    near, far = out
    assert near.kept
    assert not far.kept
    assert "beyond" in far.rejected_because


def test_hours_are_converted_with_the_router_speed():
    """Two assumptions about the same boat is how a route and a zone disagree."""
    assert _candidate(0, 0, DEFAULT_BOAT_SPEED_KMH, "one hour").hours_away == 1.0
    assert _candidate(0, 0, DEFAULT_BOAT_SPEED_KMH * 3, "three hours").hours_away == 3.0


def test_land_is_never_a_fishing_ground():
    """Well inland — Kolkata. A zone there is a bug, not a suggestion."""
    out = filter_candidates([_candidate(22.57, 88.36, 10.0, "inland")])
    assert not out[0].kept
    assert "navigable" in out[0].rejected_because


def test_open_sea_inside_the_eez_is_kept():
    out = filter_candidates([_candidate(21.0, 88.0, 60.0, "bay of bengal")])
    assert out[0].kept
    assert out[0].rejected_because is None


def test_rejections_are_kept_rather_than_dropped():
    """"Nothing within three hours" is an answer; silence is not."""
    out = filter_candidates([_candidate(21.0, 88.0, 200.0, "distant")], max_distance_km=20.0)
    assert len(out) == 1, "a filtered-out candidate must still be reported"
    assert not out[0].kept and out[0].rejected_because
