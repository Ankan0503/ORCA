"""Protected spans come back even when the translator bends the placeholder."""

import pytest

from app.language.localise import _mask, _unmask


@pytest.mark.parametrize("bent", ["@@2@@", "@2@@", "@@2@", "@ @ 2 @ @", "@@২@@"])
def test_bent_placeholder_is_restored(bent):
    assert _unmask(f"প্রায় {bent} এনডব্লিউ", ["a", "b", "27.8 km"]) == "প্রায় 27.8 km এনডব্লিউ"


def test_mask_then_unmask_round_trips():
    text = "Best ground is about 27.8 km to the NW; INCOIS issued none at 05:00."
    masked, saved = _mask(text)
    assert "27.8 km" not in masked
    assert _unmask(masked, saved) == text
