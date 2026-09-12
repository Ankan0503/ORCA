"""The corpus may only claim what it can prove.

The failure these guard against is not a crash. It is a document that reads like
a government bulletin, carries a status code and a hash, and was never fetched
from anywhere — which is worse than an empty corpus, because a confident wrong
answer displaces the instinct to go and ask.
"""

from __future__ import annotations

import pytest

from app.tools import evidence as ev


def test_forged_provenance_does_not_read_as_verified():
    """A hash over invented text is self-consistent and still proves nothing."""
    forged = ev.Document(
        id="INCOIS-OSF-2026-041",  # one of the quarantined ids
        title="Ocean State Forecast",
        authority="INCOIS",
        url="https://incois.gov.in/portal/osf/osf.jsp",
        text="Significant wave height exceeding 1.8m indicates high capsizing probability.",
        fetched_at="2026-09-10T18:05:35.327344+00:00",
        http_status=200,
        content_sha256="7597485e323a6df28f3a9229c1103a2573635e02c7d61c02c7d3e1cceddf327f",
        byte_count=259,
    )
    forged.quarantined = forged.id in ev.quarantined_ids()
    assert forged.quarantined, "the seeded ids must be quarantined"
    assert forged.verified is False


def test_hand_made_text_is_admitted_but_never_verified():
    """ingest_text is a legitimate route and must still not claim a fetch."""
    document = ev.ingest_text(
        doc_id="test-bulletin-1",
        title="Archived bulletin",
        authority="IMD",
        text="x" * 800,
    )
    try:
        assert document.verified is False
        assert document.content_sha256 == ""
    finally:
        remaining = [d for d in ev.load_corpus(force=True) if d.id != "test-bulletin-1"]
        ev.save_corpus(remaining)


@pytest.mark.asyncio
async def test_a_url_that_does_not_resolve_is_refused(monkeypatch):
    """Refusing is the feature. A 404 must raise, not store something plausible."""
    class _Response:
        status_code = 404
        content = b""
        headers: dict[str, str] = {}

    class _Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def get(self, url):
            return _Response()

    monkeypatch.setattr(ev.httpx, "AsyncClient", lambda **kwargs: _Client())

    before = len(ev.load_corpus(force=True))
    with pytest.raises(ev.EvidenceError):
        await ev.ingest_url(url="https://example.gov.in/missing", title="Missing", authority="X")
    assert len(ev.load_corpus(force=True)) == before


@pytest.mark.asyncio
async def test_a_javascript_shell_is_refused(monkeypatch):
    """dof.gov.in returns 200 with no extractable text. 200 is not enough."""
    class _Response:
        status_code = 200
        content = b"<html><body><script>renderApp()</script></body></html>"
        headers = {"content-type": "text/html"}

    class _Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def get(self, url):
            return _Response()

    monkeypatch.setattr(ev.httpx, "AsyncClient", lambda **kwargs: _Client())
    with pytest.raises(ev.EvidenceError, match="too short"):
        await ev.ingest_url(url="https://example.gov.in/shell", title="Shell", authority="X")


def test_retrieval_only_returns_documents_that_were_really_fetched():
    for query in ("wave height threshold", "trawl ban", "cyclone warning"):
        for hit in ev.search(query, top_k=5):
            assert not hit.document.quarantined
            assert hit.document.verified, (
                f"{hit.document.id} reached an answer without proven provenance"
            )


def test_the_subword_scorer_is_not_claimed_to_be_semantic():
    """It matches morphology, not meaning — and the code must not promise meaning."""
    morphology = ev._cosine_similarity(ev._vectorize("cyclone warning"), ev._vectorize("cyclonic warning"))
    synonym = ev._cosine_similarity(ev._vectorize("boat"), ev._vectorize("vessel"))
    assert morphology > 0.5, "subword overlap should catch morphology"
    assert synonym == 0.0, "it cannot do synonyms; if this changes, the docs must too"
