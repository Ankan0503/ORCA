"""Source disagreement, tested on the cases that decide whether it is useful.

The rule being checked is not "do the numbers differ" — they always do. It is
"does the difference change what a fisherman should do", and the two are not
the same question. These tests build comparisons directly rather than calling
the network, so the judgement is what is under test, not the provider.
"""

from app.tools import agreement
from app.tools.agreement import Comparison


def wind(**values: float) -> Comparison:
    return Comparison(variable="wind_speed_10m", unit="km/h", values=dict(values))


def gusts(**values: float) -> Comparison:
    return Comparison(variable="wind_gusts_10m", unit="km/h", values=dict(values))


# --- The finding worth surfacing ---------------------------------------------


def test_straddling_the_imd_limit_is_a_disagreement():
    """One model says go, another says do not. That is the whole point."""
    c = wind(ecmwf_ifs025=32.0, gfs_seamless=38.0)
    assert c.straddles
    straddle = c.straddles[0]
    assert straddle["limit"] == 35.0
    assert "ECMWF" in straddle["below"]
    assert "GFS" in straddle["atOrAbove"]
    assert c.disagrees


def test_straddling_counts_even_when_the_spread_is_small():
    """A 6 km/h spread is modest; across the limit it is still decisive."""
    c = wind(ecmwf_ifs025=34.0, gfs_seamless=36.0)
    assert c.spread == 2.0
    assert c.relative_spread is None  # under the noise floor
    assert c.disagrees  # ...but it crosses the line anyway


def test_agreement_on_the_same_side_of_the_limit_is_agreement():
    c = wind(ecmwf_ifs025=38.0, gfs_seamless=44.0, icon_seamless=41.0)
    assert not c.straddles
    # All three say "do not venture"; that they differ on how much is not a
    # disagreement about the decision.
    assert c.is_material


# --- The correction to the ported rule ---------------------------------------


def test_a_flat_calm_is_not_a_disagreement_however_large_the_percentage():
    """The measured case: 0.7 to 5.9 km/h is a 173% spread and a flat calm.

    A percentage rule alone calls this strong disagreement. Every model agrees
    on the only question being asked.
    """
    c = wind(ecmwf_ifs025=5.9, gfs_seamless=4.1, icon_seamless=1.3, gem_seamless=0.7)
    assert c.relative_spread is not None and c.relative_spread > 1.5
    assert not c.is_material
    assert not c.disagrees


def test_the_same_spread_does_count_once_the_numbers_approach_the_limit():
    c = wind(ecmwf_ifs025=20.9, gfs_seamless=8.1, icon_seamless=11.2)
    assert c.is_material  # 20.9 is past half of IMD's 35
    assert c.disagrees


def test_materiality_is_derived_from_the_published_limit_not_a_magic_number():
    assert agreement._materiality_floor("wind_speed_10m") == 17.5
    assert agreement._materiality_floor("wind_gusts_10m") == 27.5
    # A variable with no published limit cannot be judged this way.
    assert agreement._materiality_floor("sea_surface_temperature") is None


def test_noise_floor_suppresses_a_percentage_built_from_nothing():
    c = wind(ecmwf_ifs025=0.1, gfs_seamless=0.3)
    assert c.spread is not None and c.spread < agreement.NOISE_FLOOR["wind_speed_10m"]
    assert c.relative_spread is None
    assert not c.disagrees


# --- Degenerate input --------------------------------------------------------


def test_one_model_yields_no_spread_and_no_claim():
    c = wind(ecmwf_ifs025=40.0)
    assert c.spread is None
    assert c.straddles == []
    assert not c.disagrees


def test_no_values_at_all_is_not_reported_as_agreement():
    c = wind()
    assert c.spread is None
    assert c.mean is None
    report = agreement.AgreementReport(
        latitude=21.6, longitude=87.5, hours_ahead=0, comparisons=[c]
    )
    assert "No model returned" in report.headline


# --- The report --------------------------------------------------------------


def test_headline_leads_with_the_decision_changing_case():
    report = agreement.AgreementReport(
        latitude=21.6,
        longitude=87.5,
        hours_ahead=12,
        comparisons=[
            wind(ecmwf_ifs025=32.0, gfs_seamless=38.0),
            gusts(ecmwf_ifs025=40.0, gfs_seamless=44.0),
        ],
    )
    assert report.decision_changing
    assert "disagree across" in report.headline
    assert "do not venture" in report.headline


def test_calm_report_says_so_rather_than_claiming_bare_agreement():
    report = agreement.AgreementReport(
        latitude=21.6,
        longitude=87.5,
        hours_ahead=0,
        comparisons=[wind(ecmwf_ifs025=5.9, gfs_seamless=0.7)],
    )
    assert not report.decision_changing
    assert "well inside safe limits" in report.headline


def test_serialised_report_names_the_models_and_the_source():
    report = agreement.AgreementReport(
        latitude=21.6,
        longitude=87.5,
        hours_ahead=0,
        comparisons=[wind(ecmwf_ifs025=32.0, gfs_seamless=38.0)],
        unavailable=["DWD ICON"],
    )
    payload = report.to_dict()
    assert payload["decisionChanging"] is True
    assert "DWD ICON" in payload["modelsUnavailable"]
    values = payload["comparisons"][0]["values"]
    # Reported under agency names, not opaque model slugs.
    assert "ECMWF IFS (0.25°)" in values
    assert payload["comparisons"][0]["straddles"][0]["source"].startswith("IMD")


def test_best_match_is_not_among_the_models_compared():
    """It resolves to reanalysis for past dates, so it would compare with itself."""
    assert "best_match" not in agreement.MODELS
    assert len(agreement.MODELS) >= 3
