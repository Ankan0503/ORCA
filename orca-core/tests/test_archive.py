"""The archive, tested on the property that makes it worth having.

Storage is the easy part. The thing that decides whether anything built on this
is trustworthy is *which day a record is filed under*, because an off-by-one
there produces a dataset that looks entirely normal and is wrong throughout.
That is not hypothetical on this project — an earlier trend feature fabricated a
result exactly that way — so it is the first thing checked here.
"""

import asyncio
from pathlib import Path

import pytest

from app import archive
from app.tools.pfz import _iso_forecast_date


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Every test gets its own file, so none of them can see another's rows."""
    monkeypatch.setattr(archive, "_db_path", lambda: tmp_path / "archive.sqlite3")

    class Settings:
        archive_enabled = True

    monkeypatch.setattr(archive, "get_settings", lambda: Settings())
    return tmp_path / "archive.sqlite3"


# --- The date that matters ---------------------------------------------------


def test_incois_forecast_dates_parse_to_iso():
    assert _iso_forecast_date("5 SEP 2026") == "2026-09-05"
    assert _iso_forecast_date("15 JAN 2027") == "2027-01-15"
    assert _iso_forecast_date("1 DEC 2026") == "2026-12-01"


def test_an_unparseable_date_is_none_rather_than_today():
    """Guessing would file an undated advisory as though it were about a day.

    Returning None pushes the record to the collection date and leaves the
    ambiguity visible, which is recoverable. A confident wrong date is not.
    """
    assert _iso_forecast_date(None) is None
    assert _iso_forecast_date("") is None
    assert _iso_forecast_date("tomorrow") is None
    assert _iso_forecast_date("5 SMURF 2026") is None
    assert _iso_forecast_date("SEP 2026") is None


def test_a_record_is_filed_under_the_day_it_describes():
    """An advisory scraped today, forecasting tomorrow, belongs to tomorrow.

    The forecast day is derived from today rather than written as a literal.
    An earlier version of this test hardcoded 2026-09-10, passed, and then
    failed the morning that date arrived — a date test undone by a date, which
    is exactly the class of bug the archive's `observed_for` column exists to
    prevent.
    """
    from datetime import date, timedelta

    from app.archive import ist_today

    tomorrow = (date.fromisoformat(ist_today()) + timedelta(days=1)).isoformat()
    archive.record(
        archive.KIND_PFZ_ADVISORY,
        {"secid": "SEC004"},
        key="SEC004",
        observed_for=tomorrow,
    )
    rows = archive.history(archive.KIND_PFZ_ADVISORY)
    assert len(rows) == 1
    assert rows[0]["observedFor"] == tomorrow
    # ...and when it was collected is kept as its own field, genuinely distinct
    # from the day being described. That separation is the whole point.
    # fetched_at is an instant and so is UTC; observed_for is an Indian
    # calendar day. Around midnight IST those are different dates, which is
    # correct and is why the comparison below is against the IST day.
    assert rows[0]["observedFor"] != ist_today()
    assert rows[0]["fetchedAt"].endswith("+00:00")


def test_days_are_distinct_rows_not_overwrites():
    for day in ("2026-09-08", "2026-09-09", "2026-09-10"):
        archive.record(archive.KIND_PFZ_ADVISORY, {"day": day}, key="SEC004", observed_for=day)
    rows = archive.history(archive.KIND_PFZ_ADVISORY)
    assert [r["observedFor"] for r in rows] == ["2026-09-10", "2026-09-09", "2026-09-08"]


# --- Re-collection -----------------------------------------------------------


def test_recollecting_a_day_updates_the_payload_and_keeps_first_seen():
    """A corrected bulletin should be distinguishable from a first sighting."""
    archive.record(archive.KIND_PFZ_ADVISORY, {"v": 1}, key="SEC004", observed_for="2026-09-10")
    first = archive.history(archive.KIND_PFZ_ADVISORY)[0]["firstSeen"]

    archive.record(archive.KIND_PFZ_ADVISORY, {"v": 2}, key="SEC004", observed_for="2026-09-10")
    rows = archive.history(archive.KIND_PFZ_ADVISORY)

    assert len(rows) == 1
    assert rows[0]["payload"] == {"v": 2}
    assert rows[0]["firstSeen"] == first


def test_different_sectors_on_the_same_day_do_not_collide():
    archive.record(archive.KIND_PFZ_ADVISORY, {"s": "a"}, key="SEC004", observed_for="2026-09-10")
    archive.record(archive.KIND_PFZ_ADVISORY, {"s": "b"}, key="SEC005", observed_for="2026-09-10")
    assert len(archive.history(archive.KIND_PFZ_ADVISORY)) == 2
    assert len(archive.history(archive.KIND_PFZ_ADVISORY, key="SEC004")) == 1


# --- It must never break a request -------------------------------------------


def _unusable_path(tmp_path: Path) -> Path:
    """A path that cannot be created, portably.

    An absolute path under a directory that does not exist is not a failure —
    ``mkdir(parents=True)`` simply creates it, on Windows as readily as on
    Linux, so a test written that way passes for the wrong reason. Putting a
    *file* where a directory has to go is a real filesystem error everywhere.
    """
    blocker = tmp_path / "blocker"
    blocker.write_text("not a directory")
    return blocker / "nested" / "archive.sqlite3"


def test_a_write_failure_is_swallowed_not_raised(tmp_path, monkeypatch):
    """Archiving is a side effect of answering someone.

    An unusable disk must degrade to "nothing was written", never to a failed
    advisory.
    """
    monkeypatch.setattr(archive, "_db_path", lambda: _unusable_path(tmp_path))
    assert archive.record(archive.KIND_PFZ_ADVISORY, {"x": 1}) is False


def test_reads_degrade_to_empty_rather_than_raising(tmp_path, monkeypatch):
    monkeypatch.setattr(archive, "_db_path", lambda: _unusable_path(tmp_path))
    assert archive.history(archive.KIND_PFZ_ADVISORY) == []
    assert archive.export() == []
    assert archive.stats()["available"] is False


def test_disabling_the_archive_writes_nothing(monkeypatch):
    class Off:
        archive_enabled = False

    monkeypatch.setattr(archive, "get_settings", lambda: Off())
    assert archive.record(archive.KIND_PFZ_ADVISORY, {"x": 1}) is False
    monkeypatch.setattr(archive, "get_settings", lambda: type("On", (), {"archive_enabled": True}))
    assert archive.history(archive.KIND_PFZ_ADVISORY) == []


# --- Async path --------------------------------------------------------------


def test_async_write_lands_the_same_row():
    ok = asyncio.run(
        archive.record_async(
            archive.KIND_CYCLONE_OUTLOOK, {"noCycloneDeclared": True}, observed_for="2026-09-09"
        )
    )
    assert ok
    rows = archive.history(archive.KIND_CYCLONE_OUTLOOK)
    assert rows[0]["payload"]["noCycloneDeclared"] is True


# --- Reporting ---------------------------------------------------------------


def test_stats_counts_distinct_days_not_just_rows():
    """Depth is what decides whether anything can be learned yet."""
    for sector in ("SEC004", "SEC005", "SEC006"):
        for day in ("2026-09-08", "2026-09-09"):
            archive.record(archive.KIND_PFZ_ADVISORY, {}, key=sector, observed_for=day)

    summary = archive.stats()
    kinds = {k["kind"]: k for k in summary["kinds"]}
    assert summary["totalRows"] == 6
    assert kinds[archive.KIND_PFZ_ADVISORY]["rows"] == 6
    assert kinds[archive.KIND_PFZ_ADVISORY]["days"] == 2  # not 6
    assert kinds[archive.KIND_PFZ_ADVISORY]["earliest"] == "2026-09-08"
    assert kinds[archive.KIND_PFZ_ADVISORY]["latest"] == "2026-09-09"


def test_since_filters_by_the_described_day():
    for day in ("2026-09-01", "2026-09-05", "2026-09-10"):
        archive.record(archive.KIND_PFZ_STATUS, {"d": day}, observed_for=day)
    recent = archive.history(archive.KIND_PFZ_STATUS, since="2026-09-05")
    assert [r["observedFor"] for r in recent] == ["2026-09-10", "2026-09-05"]


def test_export_returns_every_kind_unless_narrowed():
    archive.record(archive.KIND_PFZ_ADVISORY, {}, key="SEC004", observed_for="2026-09-10")
    archive.record(archive.KIND_CYCLONE_OUTLOOK, {}, observed_for="2026-09-10")
    assert len(archive.export()) == 2
    assert len(archive.export(archive.KIND_CYCLONE_OUTLOOK)) == 1
