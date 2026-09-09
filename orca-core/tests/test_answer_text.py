"""Tests for the plain-text cleanup applied to every synthesised answer.

The model reaches for markdown out of habit, and nothing in ORCA renders it:
the answer card prints plain text and Sarvam speaks the same string. So a reply
about a storm arrived reading "**unsafe**" on screen, and with the asterisks in
the spoken version — which is worse, because the person hearing it has no
screen to check.

The risk in stripping is the opposite mistake: asterisks that are arithmetic,
not emphasis.
"""

from app.agents.orchestrator import _plain


def test_emphasis_markers_are_removed():
    assert _plain("The verdict is **unsafe**.") == "The verdict is unsafe."
    assert _plain("__Do not__ go out") == "Do not go out"


def test_headings_and_bullets_become_speakable():
    cleaned = _plain("## Sea state\n* waves 0.8 m\n+ wind 6 km/h")
    assert cleaned == "Sea state\n- waves 0.8 m\n- wind 6 km/h"


def test_arithmetic_asterisks_survive():
    # The whole reason the emphasis pattern is not a bare "\*".
    for text in ("Waves are 2*3 m", "5 * 2 metres apart", "a 3*3 grid"):
        assert _plain(text) == text


def test_a_clean_answer_is_left_alone():
    text = "It is safe until 14:00, then thunderstorms with lightning."
    assert _plain(text) == text


def test_surrounding_whitespace_goes():
    assert _plain("\n\n  Safe to go out.  \n") == "Safe to go out."
