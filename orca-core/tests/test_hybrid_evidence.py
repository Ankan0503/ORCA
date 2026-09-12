"""Tests for Lightweight Hybrid RAG (BM25 + Dense Semantic) and Structured Legal Metadata."""

from datetime import datetime, timezone
import pytest

import sys
from pathlib import Path

# Ensure orca-core root is on sys.path for direct script execution
_ORCA_CORE = str(Path(__file__).resolve().parent.parent)
if _ORCA_CORE not in sys.path:
    sys.path.insert(0, _ORCA_CORE)

from app.tools import evidence as store


@pytest.fixture(autouse=True)
def isolated_corpus(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "_corpus_path", lambda: tmp_path / "corpus.json")
    monkeypatch.setattr(store, "_cache", None)
    yield tmp_path / "corpus.json"


def test_hybrid_search_matches_paraphrase_without_exact_terms():
    """Dense subword similarity must match query paraphrases even when exact words differ."""
    doc = store.Document(
        id="gahirmatha",
        title="Gahirmatha Marine Sanctuary Turtle Conservation Area",
        authority="Odisha Forest Dept",
        url="https://wildlife.odisha.gov.in",
        text="Prohibition of mechanized trawler navigation and net casting within 20 km of Olive Ridley sea turtle nesting beach.",
        applicable_state="Odisha",
        regulation_type="PROTECTED_AREA",
    )
    # Paraphrased query: "motorized boat near turtle sanctuary"
    hits = store.search("motorized boat near turtle sanctuary", corpus=[doc])
    assert len(hits) == 1
    assert hits[0].document.id == "gahirmatha"
    assert hits[0].dense_score > 0.15


def test_is_active_now_identifies_current_ban_period():
    """Validates seasonal date range evaluation."""
    doc = store.Document(
        id="east_ban",
        title="East Coast Monsoon Trawl Ban",
        authority="Department of Fisheries",
        url="https://dof.gov.in",
        text="Annual uniform 61-day monsoon fishing ban for mechanised vessels.",
        applicable_state="West Bengal, Odisha, Andhra Pradesh, Tamil Nadu",
        effective_start="04-15",
        effective_end="06-14",
        regulation_type="SEASONAL_BAN",
    )

    in_season = datetime(2026, 5, 1, tzinfo=timezone.utc)
    off_season = datetime(2026, 9, 1, tzinfo=timezone.utc)

    assert doc.is_active_now(reference_date=in_season) is True
    assert doc.is_active_now(reference_date=off_season) is False


def test_is_active_now_handles_cross_year_boundaries():
    """Validates regulations that span across December/January (e.g. Nov 1 to May 31)."""
    doc = store.Document(
        id="gahirmatha_nesting",
        title="Gahirmatha Olive Ridley Sanctuary Winter Ban",
        authority="Odisha Forest Dept",
        url="https://wildlife.odisha.gov.in",
        text="Winter turtle protection seasonal closure.",
        applicable_state="Odisha",
        effective_start="11-01",
        effective_end="05-31",
        regulation_type="PROTECTED_AREA",
    )

    assert doc.is_active_now(reference_date=datetime(2026, 12, 15, tzinfo=timezone.utc)) is True
    assert doc.is_active_now(reference_date=datetime(2026, 1, 20, tzinfo=timezone.utc)) is True
    assert doc.is_active_now(reference_date=datetime(2026, 8, 10, tzinfo=timezone.utc)) is False


def test_state_jurisdiction_boosting():
    """Query specifying a state boosts documents belonging to that jurisdiction."""
    doc_odisha = store.Document(
        id="od_ban",
        title="Odisha Marine Fishing Regulation Rules",
        authority="Directorate of Fisheries, Odisha",
        url="https://fisheries.odisha.gov.in",
        text="Monsoon fishing restrictions for mechanized boats in coastal territorial waters.",
        applicable_state="Odisha",
    )
    doc_gujarat = store.Document(
        id="gj_ban",
        title="Gujarat Fisheries Regulation Act",
        authority="Department of Fisheries, Gujarat",
        url="https://fisheries.gujarat.gov.in",
        text="Monsoon fishing restrictions for mechanized boats in coastal territorial waters.",
        applicable_state="Gujarat",
    )
    corpus = [doc_gujarat, doc_odisha]

    hits = store.search("monsoon fishing restrictions", corpus=corpus, state="Odisha")
    assert len(hits) == 2
    assert hits[0].document.id == "od_ban"


def test_active_only_filtering():
    """active_only=True returns only regulations that are currently in effect."""
    doc_active = store.Document(
        id="active_rule",
        title="Active Winter Marine Conservation",
        authority="MoEFCC",
        url="https://moef.gov.in",
        text="Winter coastal restriction.",
        effective_start="11-01",
        effective_end="05-31",
    )
    doc_inactive = store.Document(
        id="inactive_rule",
        title="Summer Trawl Closure",
        authority="Dept of Fisheries",
        url="https://dof.gov.in",
        text="Summer trawl restriction.",
        effective_start="06-01",
        effective_end="07-31",
    )
    corpus = [doc_active, doc_inactive]
    ref_date = datetime(2026, 1, 15, tzinfo=timezone.utc)

    hits = store.search("marine restriction", corpus=corpus, active_only=True, reference_date=ref_date)
    assert len(hits) == 1
    assert hits[0].document.id == "active_rule"
