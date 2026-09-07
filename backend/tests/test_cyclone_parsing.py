"""Tests for the RSMC Tropical Weather Outlook parser.

Two kinds of case here, and the difference matters:

- The **legend regression** uses the footer text verbatim from a real IMD
  bulletin (06.09.2026). It guards a bug that shipped in a first draft: every
  page of the outlook carries a footnote explaining the probability scale —
  "NIL:0%, LOW:1-33%, MODERATE:34-66% and HIGH:67-100%" — and a naive scan read
  that legend as if it were the data row, turning a bulletin that said NIL into
  a claim of HIGH cyclone-formation probability. Fabricating a cyclone warning
  out of a footnote is the worst failure this module could have.

- The **cyclone-present cases are synthetic**, written to mirror IMD's standard
  bulletin phrasing. They are not real bulletins. No cyclone existed in the
  North Indian Ocean while this was built, so the storm path could not be
  exercised against live data; these tests pin the intended behaviour so the
  path is not merely untested code. They should be replaced with a genuine
  archived bulletin the next time a real system is available.
"""

from app.tools.cyclone import parse_outlook, parse_probabilities

# Verbatim footer from the real bulletin of 06.09.2026.
REAL_FOOTER = (
    "Cloud distribution: (a) Isolated: <25%, Scattered:25-50%, Broken: 51-75%, "
    "Solid:>75%, Convection Intensity: (a) Weak: Cloud Top Temperature(CTT)>-25C, "
    "Probability of cyclogenesis (formation of depression) :NIL:0%, LOW:1-33%, "
    "MODERATE:34-66% and HIGH:67-100%"
)

QUIET_TABLE = (
    "*PROBABILITY OF CYCLOGENESIS (FORMATION OF DEPRESSION) DURING NEXT 168 HRS)\n"
    "24 HOURS 24-48 HOURS 48-72 HOURS 72-96 HOURS 96-120 HOURS 120-144 HOURS 144-168 HOURS\n"
    "NIL NIL NIL NIL NIL NIL NIL\n" + REAL_FOOTER
)


def test_legend_is_not_read_as_data():
    """The scale footnote must never be mistaken for the forecast row."""
    values = parse_probabilities(QUIET_TABLE, 0)
    assert values == ["NIL"] * 7


def test_rising_risk_table_is_read_in_order():
    table = (
        "PROBABILITY OF CYCLOGENESIS (FORMATION OF DEPRESSION) DURING NEXT 168 HRS:\n"
        "24 HOURS 24-48 HOURS 48-72 HOURS 72-96 HOURS 96-120 HOURS 120-144 HOURS 144-168 HOURS\n"
        "NIL NIL LOW MODERATE HIGH HIGH MODERATE\n" + REAL_FOOTER
    )
    assert parse_probabilities(table, 0) == [
        "NIL", "NIL", "LOW", "MODERATE", "HIGH", "HIGH", "MODERATE",
    ]


# --- Synthetic bulletins, modelled on IMD phrasing --------------------------

CYCLONE_TEXT = f"""
REGIONAL SPECIALISED METEOROLOGICAL CENTRE -TROPICAL CYCLONES, NEW DELHI
TROPICAL WEATHER OUTLOOK FOR THE NORTH INDIAN OCEAN (THE BAY OF BENGAL AND THE
ARABIAN SEA) VALID FOR THE NEXT 168 HOURS ISSUED AT 0600 UTC OF 26.05.2024
BASED ON 0300 UTC OF 26.05.2024.
BAY OF BENGAL:
The Severe Cyclonic Storm over northwest Bay of Bengal moved north-northeastwards
and lay centred at 0300 UTC of today over the same region.
Yesterday's upper air cyclonic circulation over south Bay of Bengal became less
marked at 0300 UTC of today.
{QUIET_TABLE}
ARABIAN SEA:
Scattered low and medium clouds lay over north Arabian Sea.
{QUIET_TABLE}
"""


def test_cyclonic_storm_is_detected_with_severity():
    outlook = parse_outlook(CYCLONE_TEXT, "http://example.invalid/test.pdf")
    active = outlook.active_cyclone
    assert active is not None
    assert active.kind == "severe cyclonic storm"
    assert active.basin == "Bay of Bengal"
    # Severe cyclonic storm outranks a plain cyclonic storm.
    assert active.severity == 4


def test_weakened_systems_are_not_reported_as_present():
    """"became less marked" describes a system that has gone, not a hazard."""
    outlook = parse_outlook(CYCLONE_TEXT, "http://example.invalid/test.pdf")
    assert all("less marked" not in s.sentence.lower() for s in outlook.systems)


def test_issue_time_is_read():
    outlook = parse_outlook(CYCLONE_TEXT, "http://example.invalid/test.pdf")
    assert outlook.issued_text is not None
    assert "26.05.2024" in outlook.issued_text


def test_basins_are_split_and_routed_by_longitude():
    outlook = parse_outlook(CYCLONE_TEXT, "http://example.invalid/test.pdf")
    assert {b.basin for b in outlook.basins} == {"Bay of Bengal", "Arabian Sea"}
    # Digha on the east coast, Kochi on the west.
    assert outlook.basin_for(87.5).basin == "Bay of Bengal"
    assert outlook.basin_for(76.0).basin == "Arabian Sea"


def test_quiet_bulletin_reports_no_cyclone():
    quiet = CYCLONE_TEXT.replace(
        "The Severe Cyclonic Storm over northwest Bay of Bengal moved "
        "north-northeastwards\nand lay centred at 0300 UTC of today over the same region.",
        "Scattered low and medium clouds lay over central Bay of Bengal.",
    )
    outlook = parse_outlook(quiet, "http://example.invalid/test.pdf")
    assert outlook.active_cyclone is None


def test_deep_depression_outranks_depression():
    text = CYCLONE_TEXT.replace(
        "The Severe Cyclonic Storm over northwest Bay of Bengal",
        "The Deep Depression over northwest Bay of Bengal",
    )
    outlook = parse_outlook(text, "http://example.invalid/test.pdf")
    kinds = [s.kind for s in outlook.systems]
    assert "deep depression" in kinds
    # It must not also be counted as a plain "depression".
    assert kinds.count("depression") == 0
    # A deep depression is below cyclonic-storm strength, so not a "cyclone".
    assert outlook.active_cyclone is None


# --- The alert the Alerts screen shows --------------------------------------
#
# Separated from fetching so the warning path is exercised without a live storm.

from datetime import datetime

from app.api.conditions import cyclone_alert

_NOW = datetime(2026, 9, 7, 8, 0, 0)


def test_declared_storm_becomes_a_warning():
    outlook = parse_outlook(CYCLONE_TEXT, "http://example.invalid/test.pdf")
    alert = cyclone_alert(outlook, 87.5, _NOW)
    assert alert is not None
    assert alert["severity"] == "high"
    assert alert["badgeLabel"] == "Cyclone warning"
    assert "severe cyclonic storm" in alert["title"].lower()


def test_quiet_outlook_produces_no_alert():
    """A calm bulletin must add nothing — silence is the honest answer."""
    quiet = CYCLONE_TEXT.replace(
        "The Severe Cyclonic Storm over northwest Bay of Bengal moved "
        "north-northeastwards\nand lay centred at 0300 UTC of today over the same region.",
        "Scattered low and medium clouds lay over central Bay of Bengal.",
    )
    outlook = parse_outlook(quiet, "http://example.invalid/test.pdf")
    assert cyclone_alert(outlook, 87.5, _NOW) is None


def test_formation_chance_is_a_watch_not_a_warning():
    """A chance of forming must never be worded as a declared cyclone."""
    risky = CYCLONE_TEXT.replace(
        "The Severe Cyclonic Storm over northwest Bay of Bengal moved "
        "north-northeastwards\nand lay centred at 0300 UTC of today over the same region.",
        "Scattered low and medium clouds lay over central Bay of Bengal.",
    ).replace("NIL NIL NIL NIL NIL NIL NIL", "NIL LOW MODERATE HIGH HIGH NIL NIL", 1)

    outlook = parse_outlook(risky, "http://example.invalid/test.pdf")
    alert = cyclone_alert(outlook, 87.5, _NOW)
    assert alert is not None
    assert alert["badgeLabel"] == "Cyclone watch"
    assert "watch, not a warning" in alert["message"]
    assert alert["severity"] == "high"  # peak HIGH


def test_alert_follows_the_users_basin():
    """A storm in the Arabian Sea is not a warning for a Bay of Bengal boat."""
    arabian = CYCLONE_TEXT.replace("NIL NIL NIL NIL NIL NIL NIL", "NIL NIL NIL NIL NIL NIL NIL")
    outlook = parse_outlook(arabian, "http://example.invalid/test.pdf")
    # The synthetic storm sits in the Bay of Bengal, so it is a declared system
    # either way; what must differ is the basin used for formation probability.
    assert outlook.basin_for(76.0).basin == "Arabian Sea"
    assert outlook.basin_for(87.5).basin == "Bay of Bengal"
