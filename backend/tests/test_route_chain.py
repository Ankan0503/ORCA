"""Tests for the stop list a chained trip is built from.

The stops arrive as free text in a query string, so this is the surface where a
malformed request becomes either a clear 422 or a confusing 500 three layers
down inside the router. Each case here is one a real client can send.
"""

import pytest
from fastapi import HTTPException

from app.api.route import MAX_STOPS, _parse_stop


def test_a_well_formed_stop_parses():
    assert _parse_stop("21.4478,87.6069", 0) == (21.4478, 87.6069)
    assert _parse_stop("-8.5,-120.25", 0) == (-8.5, -120.25)
    assert _parse_stop(" 21.4 , 87.6 ", 0) == (21.4, 87.6)


@pytest.mark.parametrize("raw", ["nonsense", "21.4", "21.4,87.6,3", "", "21.4;87.6"])
def test_a_malformed_stop_is_rejected_with_its_position(raw):
    with pytest.raises(HTTPException) as caught:
        _parse_stop(raw, 2)
    assert caught.value.status_code == 422
    # The message names which stop, because a trip has several.
    assert "Stop 3" in caught.value.detail


def test_a_stop_off_the_globe_is_rejected():
    for raw in ("91.0,87.6", "21.4,181.0", "-91,0"):
        with pytest.raises(HTTPException) as caught:
            _parse_stop(raw, 0)
        assert caught.value.status_code == 422
        assert "not on Earth" in caught.value.detail


def test_the_trip_length_cap_is_a_day_of_fishing():
    # Not arbitrary: past this the forecast window it is checked against stops
    # being meaningful, which is the whole point of the endpoint.
    assert MAX_STOPS == 4
