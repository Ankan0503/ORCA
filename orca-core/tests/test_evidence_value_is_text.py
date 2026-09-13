"""One mis-typed evidence row must not cost the whole answer.

``Evidence.value`` is annotated ``str`` and leaves through a Pydantic response
model, so a row built from a number failed validation for the entire reply --
and the app, catching that as a failed request, told the fisherman it could not
reach ORCA while the data sat complete on the other side of the serialiser.

``round()`` returns a float, which is how it happened: two rows in the weather
agent were built with ``round(...)`` and only appeared once the upstream feeds
were reachable, so the break surfaced the moment the data started flowing.
"""

import pytest

from app.agents.base import Evidence


def test_a_number_becomes_text_rather_than_a_validation_error():
    """round() returns a float, and that must not reach the response model."""
    assert Evidence(source="s", label="l", value=round(2.04, 1)).value == "2.0"
    assert Evidence(source="s", label="l", value=7).value == "7"


def test_text_is_left_exactly_as_written():
    """Coercion must not reformat a value that was already correct."""
    for written in ("2.00", "unavailable", "—", "120 km/h", ""):
        assert Evidence(source="s", label="l", value=written).value == written


def test_a_missing_value_becomes_empty_rather_than_the_word_none():
    """"None" in a value cell would read as a measurement, not as an absence."""
    assert Evidence(source="s", label="l", value=None).value == ""


def test_the_chat_response_model_accepts_a_numeric_row():
    """The end the bug actually broke: serialising an answer that holds one."""
    from app.api.chat import ChatResponse

    row = Evidence(source="Open-Meteo sea grid", label="Strongest current", value=round(2.0, 2))
    response = ChatResponse(
        answer="ok",
        language="en",
        agents_used=["weather_intelligence"],
        evidence=[
            {
                "agent": "weather_intelligence",
                "summary": "ok",
                "confidence": 0.9,
                "is_stub": False,
                "evidence": [row.to_dict()],
            }
        ],
        reasoning=[],
        used_stub_data=False,
    )
    assert response.evidence[0].evidence[0].value == "2.0"


@pytest.mark.parametrize("value", [2.0, 0, -1.5, True])
def test_every_scalar_a_row_might_be_built_from_survives(value):
    assert isinstance(Evidence(source="s", label="l", value=value).value, str)
