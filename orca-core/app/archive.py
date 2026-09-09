"""Keeping what the scrapers already fetch.

ORCA forgets everything daily. ``pfz.py`` caches advisories in module-level
dictionaries keyed by calendar date and deletes yesterday's on the next call;
``cyclone.py`` does the same with bulletins. Every INCOIS advisory scraped and
every RSMC bulletin parsed is gone within twenty-four hours, which is why there
is no way to answer "what did IMD say last week" and no history to learn a PFZ
gap-filler from.

This adds no fetching. It writes down what already arrives.

The one decision that matters
-----------------------------
Records are filed under **the day the data describes**, not the day it was
collected. INCOIS publishes an advisory in the afternoon *for the following
day*, so filing it under the fetch date would shift every row by one and
quietly corrupt any dataset built from it later. That is not a hypothetical:
an earlier trend feature in this project produced a fabricated result by
anchoring windows to the wrong date, and the output looked entirely plausible.
``observed_for`` is therefore the forecast date when the source states one, and
falls back to the collection date only when it does not.

Ephemeral in production, and that is stated rather than hidden
--------------------------------------------------------------
The backend runs on Render's free plan, whose filesystem does not survive a
restart or a redeploy. This file will be empty again after either. That does
not make it useless — it accumulates while the process lives, it works fully on
any host with a persistent disk, and ``export`` exists so a run's worth of data
can be pulled out before it is lost. But nobody should discover the limit by
finding an empty table after a deploy, so: to accumulate a real dataset, attach
a persistent disk, point ``archive_path`` at it, or run the collector somewhere
that keeps its files.

Never breaks a request
----------------------
Archiving is a side effect of answering someone. A locked database, a full
disk or a read-only filesystem must degrade to "nothing was written", never to
a failed advisory. Every write here swallows its own errors by design.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

from .config import get_settings

log = logging.getLogger("orca.archive")

# One table, because the queries that matter all have the same shape: give me
# what this source said about these days. A table per source would need a
# migration every time a source is added, for no gain in what can be asked.
_SCHEMA = """
CREATE TABLE IF NOT EXISTS records (
    kind         TEXT NOT NULL,
    key          TEXT NOT NULL DEFAULT '',
    observed_for TEXT NOT NULL,
    first_seen   TEXT NOT NULL,
    fetched_at   TEXT NOT NULL,
    payload      TEXT NOT NULL,
    PRIMARY KEY (kind, key, observed_for)
);
CREATE INDEX IF NOT EXISTS records_kind_day ON records (kind, observed_for);
"""

KIND_PFZ_ADVISORY = "pfz_advisory"
KIND_PFZ_STATUS = "pfz_status"
KIND_CYCLONE_OUTLOOK = "cyclone_outlook"


def _db_path() -> Path:
    settings = get_settings()
    path = Path(settings.archive_path)
    if not path.is_absolute():
        path = Path(__file__).resolve().parent.parent / path
    return path


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    """A connection per operation.

    Volume here is a handful of rows a day, so pooling would be complexity for
    nothing — and a fresh connection sidesteps SQLite's thread affinity, which
    matters because these calls arrive on whatever worker thread asyncio picks.
    """
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=5.0)
    try:
        conn.row_factory = sqlite3.Row
        # Readers must not block on the daily write, and vice versa.
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(_SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def _now() -> str:
    """When this was collected. An instant, so UTC."""
    return datetime.now(timezone.utc).isoformat()


#: The advisories archived here are issued against Indian calendar days: INCOIS
#: publishes one advisory per IST day and states the forecast date in IST. The
#: default day therefore has to be the IST day, not the host's.
#:
#: This was `date.today()` until a test caught it — on a machine running IST the
#: local day had already rolled to the 10th while UTC was still the 9th, so a
#: record carried `observed_for` from one day and `fetched_at` from another.
#: Harmless on a laptop in India; wrong on Render, whose Singapore region is
#: UTC+8, and wronger anywhere further west, where whole advisories would be
#: filed a day out. A server's timezone is not a fact about the data.
IST = timezone(timedelta(hours=5, minutes=30))


def ist_today() -> str:
    """Today in IST, which is the day Indian agencies issue against."""
    return datetime.now(IST).date().isoformat()


# --- Writing -----------------------------------------------------------------


def record(
    kind: str,
    payload: Any,
    key: str = "",
    observed_for: str | None = None,
) -> bool:
    """Write one record. Returns whether it was stored; never raises.

    Re-collecting a day overwrites that day's payload but keeps ``first_seen``,
    so it stays visible that a record was captured before it was last refreshed
    — which is how a late correction to a bulletin can be told apart from a
    first sighting.
    """
    if not get_settings().archive_enabled:
        return False

    day = observed_for or ist_today()
    now = _now()
    try:
        with _connect() as conn:
            conn.execute(
                """
                INSERT INTO records (kind, key, observed_for, first_seen, fetched_at, payload)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT (kind, key, observed_for) DO UPDATE SET
                    fetched_at = excluded.fetched_at,
                    payload    = excluded.payload
                """,
                (kind, key, day, now, now, json.dumps(payload, default=str)),
            )
        return True
    except Exception as exc:  # noqa: BLE001 - archiving must never break a request
        log.warning("archive write failed (%s/%s/%s): %s", kind, key, day, exc)
        return False


async def record_async(
    kind: str,
    payload: Any,
    key: str = "",
    observed_for: str | None = None,
) -> bool:
    """Write off the event loop, so a slow disk cannot stall a response."""
    return await asyncio.to_thread(record, kind, payload, key, observed_for)


# --- Reading -----------------------------------------------------------------


def history(
    kind: str,
    key: str | None = None,
    since: str | None = None,
    limit: int = 100,
) -> list[dict]:
    """Records of one kind, newest day first."""
    clauses = ["kind = ?"]
    params: list[Any] = [kind]
    if key is not None:
        clauses.append("key = ?")
        params.append(key)
    if since:
        clauses.append("observed_for >= ?")
        params.append(since)
    params.append(max(1, min(limit, 1000)))

    try:
        with _connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM records WHERE {' AND '.join(clauses)} "
                "ORDER BY observed_for DESC LIMIT ?",
                params,
            ).fetchall()
    except Exception as exc:  # noqa: BLE001
        log.warning("archive read failed (%s): %s", kind, exc)
        return []

    return [
        {
            "kind": r["kind"],
            "key": r["key"],
            "observedFor": r["observed_for"],
            "firstSeen": r["first_seen"],
            "fetchedAt": r["fetched_at"],
            "payload": json.loads(r["payload"]),
        }
        for r in rows
    ]


def stats() -> dict:
    """What is in here, and how deep it goes.

    ``days`` is the count of distinct days held, which is the number that
    decides whether anything can be learned from this yet — a hundred rows
    across two days is not a time series.
    """
    try:
        with _connect() as conn:
            rows = conn.execute(
                """
                SELECT kind,
                       COUNT(*)                    AS rows,
                       COUNT(DISTINCT observed_for) AS days,
                       MIN(observed_for)           AS earliest,
                       MAX(observed_for)           AS latest
                FROM records GROUP BY kind ORDER BY kind
                """
            ).fetchall()
            total = conn.execute("SELECT COUNT(*) AS n FROM records").fetchone()["n"]
    except Exception as exc:  # noqa: BLE001
        log.warning("archive stats failed: %s", exc)
        return {"available": False, "reason": str(exc), "kinds": [], "totalRows": 0}

    path = _db_path()
    return {
        "available": True,
        "path": str(path),
        "sizeBytes": path.stat().st_size if path.exists() else 0,
        "totalRows": total,
        "kinds": [
            {
                "kind": r["kind"],
                "rows": r["rows"],
                "days": r["days"],
                "earliest": r["earliest"],
                "latest": r["latest"],
            }
            for r in rows
        ],
        "note": (
            "Filed under the day the data describes, not the day it was fetched. "
            "On a host with an ephemeral filesystem this is emptied by a restart "
            "or a redeploy — export before relying on it."
        ),
    }


def export(kind: str | None = None) -> list[dict]:
    """Everything, for pulling out before an ephemeral host discards it."""
    try:
        with _connect() as conn:
            if kind:
                rows = conn.execute(
                    "SELECT * FROM records WHERE kind = ? ORDER BY kind, observed_for",
                    (kind,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM records ORDER BY kind, observed_for"
                ).fetchall()
    except Exception as exc:  # noqa: BLE001
        log.warning("archive export failed: %s", exc)
        return []

    return [
        {
            "kind": r["kind"],
            "key": r["key"],
            "observedFor": r["observed_for"],
            "firstSeen": r["first_seen"],
            "fetchedAt": r["fetched_at"],
            "payload": json.loads(r["payload"]),
        }
        for r in rows
    ]
