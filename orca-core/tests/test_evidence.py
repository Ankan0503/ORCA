"""Retrieval, tested on the property that makes the whole thing safe.

The engine is ordinary BM25 and could be checked in a few lines. What actually
needs testing is the refusal: that nothing enters the corpus without a fetch
that succeeded, and that an empty or irrelevant corpus produces an admission
rather than the nearest weak match. A fisherman acting on a fabricated closure
date is worse off than one told nothing, so "returns nothing" has to be a
first-class, tested outcome.
"""

import asyncio

import pytest

from app.agents.evidence import EvidenceRetrievalAgent
from app.agents.base import QueryContext
from app.tools import evidence as store


@pytest.fixture(autouse=True)
def isolated_corpus(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "_corpus_path", lambda: tmp_path / "corpus.json")
    monkeypatch.setattr(store, "_cache", None)
    yield tmp_path / "corpus.json"


def doc(**kw) -> store.Document:
    base = dict(
        id="d1",
        title="Doc",
        authority="Test Authority",
        url="https://example.invalid/doc",
        text="placeholder text " * 40,
    )
    base.update(kw)
    return store.Document(**base)


# --- Provenance: the property that makes a citation trustworthy --------------


def test_a_document_without_a_fetch_is_not_verified():
    """Hand-written entries must be visibly distinguishable from fetched ones.

    This is the HackHeritage failure encoded as a test: fourteen convincing
    paragraphs with real-looking identifiers. They would load here, and they
    would report `verified = False`.
    """
    assert doc().verified is False
    assert doc(content_sha256="abc", http_status=404).verified is False
    assert doc(content_sha256="abc", http_status=200).verified is True


def test_ingest_text_marks_its_documents_unwitnessed():
    """Text from another ORCA scraper is real, but this module did not see it arrive."""
    stored = store.ingest_text(
        doc_id="rsmc-2026-09-09",
        title="IMD/RSMC Outlook",
        authority="IMD / RSMC",
        text="A well-marked low pressure area lies over the Bay of Bengal. " * 20,
    )
    assert stored.verified is False
    assert store.corpus_stats()["verified"] == 0
    assert store.corpus_stats()["documents"] == 1


def test_a_failed_fetch_stores_nothing():
    """A 404 must refuse, not store a plausible-looking entry."""
    with pytest.raises(store.EvidenceError):
        asyncio.run(
            store.ingest_url(
                "https://nonexistent.invalid/act.pdf", "Some Act", "Some Ministry"
            )
        )
    assert store.load_corpus(force=True) == []


def test_a_document_too_short_to_be_a_document_is_refused(monkeypatch):
    """Login walls and redirect stubs return 200 and almost no text."""

    class FakeResponse:
        status_code = 200
        headers = {"content-type": "text/plain"}
        content = b"Page not found."
        text = "Page not found."

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, url):
            return FakeResponse()

    monkeypatch.setattr(store.httpx, "AsyncClient", lambda **kw: FakeClient())
    with pytest.raises(store.EvidenceError, match="too short"):
        asyncio.run(store.ingest_url("https://example.test/x", "X", "Y"))
    assert store.load_corpus(force=True) == []


def test_a_successful_fetch_records_status_and_hash(monkeypatch):
    body = ("The monsoon fishing ban applies to mechanised vessels. " * 30).encode()

    class FakeResponse:
        status_code = 200
        headers = {"content-type": "text/plain"}
        content = body
        text = body.decode()

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, url):
            return FakeResponse()

    monkeypatch.setattr(store.httpx, "AsyncClient", lambda **kw: FakeClient())
    stored = asyncio.run(
        store.ingest_url("https://example.test/ban", "Ban notice", "Dept of Fisheries")
    )
    assert stored.verified is True
    assert stored.http_status == 200
    assert len(stored.content_sha256) == 64
    assert stored.byte_count == len(body)


# --- Retrieval ---------------------------------------------------------------


def test_bm25_ranks_the_document_that_is_about_the_question_first():
    corpus = [
        doc(id="ban", title="Monsoon trawl ban", text="The monsoon trawl ban prohibits mechanised fishing " * 20),
        doc(id="wave", title="Wave height advisory", text="Significant wave height and swell period guidance " * 20),
    ]
    hits = store.search("monsoon trawl ban", corpus=corpus)
    assert hits[0].document.id == "ban"
    assert "trawl" in hits[0].matched


def test_no_scoring_bonus_is_hardcoded_to_particular_phrases():
    """HackHeritage's scorer added +0.45 for a fixed list of terms.

    That fits the ranking to the documents it shipped with and mis-ranks
    everything added later. Two documents mentioning a term equally often, of
    equal length, must score equally.
    """
    body = "gahirmatha turtle nesting closure applies here " * 20
    corpus = [doc(id="a", title="A", text=body), doc(id="b", title="B", text=body)]
    hits = store.search("gahirmatha closure", corpus=corpus)
    assert len(hits) == 2
    assert hits[0].score == pytest.approx(hits[1].score)


def test_an_unrelated_query_does_not_match():
    corpus = [doc(id="ban", text="monsoon trawl ban mechanised vessels " * 20)]
    assert store.search("chlorophyll satellite altimetry", corpus=corpus) == []


def test_empty_corpus_and_empty_query_return_nothing():
    assert store.search("anything", corpus=[]) == []
    assert store.search("", corpus=[doc()]) == []


# --- The agent ---------------------------------------------------------------


def run_agent(question: str, **params):
    agent = EvidenceRetrievalAgent()
    context = QueryContext(question=question, params=params or {})
    return asyncio.run(agent.run(context))


def test_an_empty_corpus_says_so_rather_than_guessing():
    result = run_agent("can I fish near Gahirmatha this month?")
    assert result.data["corpusEmpty"] is True
    assert result.confidence == 0.0
    assert "nothing has been guessed" in result.summary.lower()
    assert result.evidence == []


def test_no_relevant_document_sends_the_user_to_a_human():
    store.ingest_text(
        doc_id="wave",
        title="Wave advisory",
        authority="INCOIS",
        text="Significant wave height guidance for coastal craft. " * 20,
    )
    result = run_agent("what are the rules on satellite chlorophyll licensing?")
    assert result.data["hits"] == []
    assert "harbour authority" in result.summary or "fisheries office" in result.summary
    # Silence is explicitly not permission.
    assert "permission" in result.summary.lower()


def test_a_match_is_reported_with_its_authority_and_link():
    store.ingest_text(
        doc_id="ban",
        title="Monsoon fishing ban notice",
        authority="Department of Fisheries",
        text="The monsoon fishing ban prohibits mechanised fishing vessels from operating. " * 20,
        url="https://example.test/ban",
        published="2026-04-15",
    )
    result = run_agent("monsoon fishing ban", query="monsoon fishing ban")
    assert result.data["hits"]
    assert result.evidence
    assert result.evidence[0].source.startswith("Department of Fisheries")
    assert "example.test" in (result.evidence[0].note or "")
    # Unwitnessed text is discounted, never presented as a verified fetch.
    assert result.confidence < 0.75
    assert result.data["hits"][0]["verified"] is False


def test_the_agent_is_registered_as_the_tenth_specialist():
    from app.agents.registry import default_agents

    names = [a.name for a in default_agents()]
    assert "evidence_retrieval" in names
    assert len(names) == 11
    # ...and is selectable by the planner as a tool, not hardwired into it.
    agent = next(a for a in default_agents() if a.name == "evidence_retrieval")
    tool = agent.as_tool()
    assert tool["function"]["name"] == "evidence_retrieval"
    assert "query" in tool["function"]["parameters"]["properties"]
