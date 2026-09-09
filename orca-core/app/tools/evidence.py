"""Retrieval over documents ORCA has actually fetched.

What this answers that nothing else does
----------------------------------------
Every other tool here answers "what is the sea doing". None of them can answer
"am I allowed". The geofence knows a protected-area boundary is 4 km east; it
does not know what is prohibited inside it, that a closure is seasonal, or that
the monsoon trawl ban runs to different dates in different states. For a
fisherman that second question carries arrest risk, and ORCA currently scores
zero on it.

Why this is not the HackHeritage corpus
---------------------------------------
HackHeritage's retrieval stack was sound — BGE-M3 embeddings, Qdrant, reciprocal
rank fusion with a lexical pass. Its corpus was fourteen written paragraphs,
15 KB in total, carrying convincing identifiers like ``INCOIS-OSF-2026-041`` and
specific-sounding closure dates. They read exactly like real bulletins. A
fisherman acting on a fabricated closure date is worse off than one who was told
nothing, because a confident wrong answer displaces the instinct to go and ask.

So the rule this module enforces structurally: **a document cannot enter the
corpus unless it was fetched successfully from a URL that resolved.**
``ingest_url`` is the only way in, it records the status code, the byte count
and a content hash, and it refuses anything that 404s or comes back too short to
be a document. There is no code path that accepts text somebody typed.

That is deliberately inconvenient. Checking six regulatory URLs while writing
this, five returned 404 — including plausible-looking paths on real government
domains that all resolve at the root. Guessed citations are not a hypothetical
failure here; they are the default outcome.

Why lexical and not embeddings
------------------------------
BGE-M3 is XLM-RoBERTa-large: roughly 568M parameters, about 2.2 GB at fp32 and
1.1 GB at fp16, before the PyTorch runtime, against 512 MB on the current host.
That is not a tuning problem. BM25 needs no model, and at a corpus of a few
hundred real passages the retrieval-quality difference is far smaller than the
difference between real documents and invented ones. The multilingual objection
does not apply either: the language layer already normalises a Bengali or Tamil
question to English before it reaches an agent.

The scorer is plain BM25. HackHeritage's added a fixed +0.45 for each of a list
of phrases — "gahirmatha", "trawl ban", "signal 3" — which is the scorer being
fitted to the fourteen documents it was shipped with, and would quietly mis-rank
everything added afterwards.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import re
from collections import Counter
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

import httpx

from ..config import get_settings

log = logging.getLogger("orca.evidence")

# Below this a "document" is an error page, a redirect stub or a login wall.
MIN_DOCUMENT_CHARS = 400

# BM25 constants, at their standard values. k1 controls how quickly repeated
# terms stop adding weight; b how strongly long documents are penalised.
BM25_K1 = 1.5
BM25_B = 0.75

_TOKEN = re.compile(r"[a-z0-9]+")
# Words that match everything and therefore discriminate nothing. Kept short on
# purpose: an aggressive stop list would strip "no" from "no fishing".
_STOP = frozenset(
    """a an and are as at be by for from has have in is it its of on or that the
    to was were will with this these those there their they i you we""".split()
)


def _tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN.findall(text.lower()) if t not in _STOP and len(t) > 1]


class _TextExtractor(HTMLParser):
    """Visible text from an HTML page, with script and style discarded."""

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript") and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            cleaned = data.strip()
            if cleaned:
                self.parts.append(cleaned)

    @property
    def text(self) -> str:
        return re.sub(r"\s+", " ", " ".join(self.parts)).strip()


@dataclass
class Document:
    """One retrievable passage, and the proof it came from somewhere real."""

    id: str
    title: str
    authority: str
    url: str
    text: str
    doc_type: str = "document"
    published: str | None = None
    # The one-line actionable form, when the document states a clear rule.
    rule: str | None = None

    # --- provenance: written by ingestion, never by hand ---------------------
    fetched_at: str = ""
    http_status: int = 0
    byte_count: int = 0
    content_sha256: str = ""

    @property
    def verified(self) -> bool:
        """Did this come from a fetch that actually succeeded?

        Anything loaded from a corpus file that lacks provenance reads as
        unverified, so a hand-edited entry cannot pass itself off as fetched.
        """
        return bool(self.content_sha256) and 200 <= self.http_status < 300

    def to_dict(self) -> dict:
        d = asdict(self)
        d["verified"] = self.verified
        return d

    def summary(self) -> dict:
        """Without the full text, for listings."""
        d = self.to_dict()
        d["text"] = d["text"][:300] + ("…" if len(self.text) > 300 else "")
        return d


@dataclass
class Hit:
    document: Document
    score: float
    matched: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.document.id,
            "title": self.document.title,
            "authority": self.document.authority,
            "url": self.document.url,
            "published": self.document.published,
            "rule": self.document.rule,
            "verified": self.document.verified,
            "score": round(self.score, 3),
            "matchedTerms": self.matched,
            "excerpt": self.document.text[:400] + ("…" if len(self.document.text) > 400 else ""),
        }


class EvidenceError(RuntimeError):
    """Raised when a document cannot be ingested."""


# --- The corpus on disk ------------------------------------------------------


def _corpus_path() -> Path:
    path = Path(get_settings().evidence_corpus_path)
    if not path.is_absolute():
        path = Path(__file__).resolve().parent.parent.parent / path
    return path


_cache: tuple[float, list[Document]] | None = None


def load_corpus(force: bool = False) -> list[Document]:
    """Every document currently held. An absent corpus is empty, not an error."""
    global _cache
    path = _corpus_path()
    if not path.exists():
        return []
    stamp = path.stat().st_mtime
    if not force and _cache is not None and _cache[0] == stamp:
        return _cache[1]
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("evidence corpus unreadable: %s", exc)
        return []
    docs = [Document(**{k: v for k, v in item.items() if k != "verified"}) for item in raw]
    _cache = (stamp, docs)
    return docs


def save_corpus(documents: list[Document]) -> None:
    global _cache
    path = _corpus_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [
        {k: v for k, v in d.to_dict().items() if k != "verified"} for d in documents
    ]
    path.write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
    _cache = None


# --- Getting documents in ----------------------------------------------------


def _extract(content: bytes, content_type: str) -> str:
    if "pdf" in content_type.lower():
        # pypdf is already a dependency, for the IMD bulletins.
        import io

        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(content))
        return re.sub(
            r"\s+", " ", " ".join((page.extract_text() or "") for page in reader.pages)
        ).strip()

    text = content.decode("utf-8", errors="replace")
    if "<" in text[:2000]:
        parser = _TextExtractor()
        parser.feed(text)
        return parser.text
    return re.sub(r"\s+", " ", text).strip()


async def ingest_url(
    url: str,
    title: str,
    authority: str,
    doc_type: str = "document",
    published: str | None = None,
    rule: str | None = None,
    doc_id: str | None = None,
    timeout: float = 45.0,
) -> Document:
    """Fetch a document and add it, or refuse.

    Refusing is the feature. A 404, an unreachable host or a body too short to
    be a document raises rather than storing a plausible-looking entry, so the
    corpus cannot contain a citation that does not resolve.
    """
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(url)
    except httpx.HTTPError as exc:
        raise EvidenceError(f"Could not fetch {url}: {exc}") from exc

    if response.status_code != 200:
        raise EvidenceError(f"{url} returned {response.status_code}, not stored")

    text = _extract(response.content, response.headers.get("content-type", ""))
    if len(text) < MIN_DOCUMENT_CHARS:
        raise EvidenceError(
            f"{url} yielded {len(text)} characters — too short to be a document, not stored"
        )

    document = Document(
        id=doc_id or hashlib.sha256(url.encode()).hexdigest()[:12],
        title=title,
        authority=authority,
        url=url,
        text=text,
        doc_type=doc_type,
        published=published,
        rule=rule,
        fetched_at=datetime.now(timezone.utc).isoformat(),
        http_status=response.status_code,
        byte_count=len(response.content),
        content_sha256=hashlib.sha256(response.content).hexdigest(),
    )

    corpus = [d for d in load_corpus(force=True) if d.id != document.id]
    corpus.append(document)
    save_corpus(corpus)
    return document


def ingest_text(
    doc_id: str,
    title: str,
    authority: str,
    text: str,
    url: str = "",
    doc_type: str = "bulletin",
    published: str | None = None,
) -> Document:
    """Add text ORCA already fetched itself — an archived IMD bulletin.

    This is the one route in that does not fetch, because the fetch already
    happened inside the scraper that produced the text. It records no content
    hash and therefore reports ``verified = False``: the document is real, but
    this module did not witness it arriving, and the difference should be
    visible rather than assumed away.
    """
    document = Document(
        id=doc_id,
        title=title,
        authority=authority,
        url=url,
        text=re.sub(r"\s+", " ", text).strip(),
        doc_type=doc_type,
        published=published,
        fetched_at=datetime.now(timezone.utc).isoformat(),
    )
    corpus = [d for d in load_corpus(force=True) if d.id != document.id]
    corpus.append(document)
    save_corpus(corpus)
    return document


def seed_from_archive(limit: int = 200) -> dict:
    """Turn what the scrapers have already kept into retrievable documents.

    This is the corpus's sustainable source, and the reason Phase 4 came first.
    ORCA fetches real IMD and RSMC bulletin prose every day; before the archive
    it was discarded within twenty-four hours. Now it accumulates, and every
    accumulated bulletin is a genuine government document that can be retrieved
    and cited — with no guessing at URLs and nothing written by hand.

    It grows slowly, which is the honest trade. A corpus of real bulletins built
    over weeks is worth more than several hundred convincing paragraphs written
    in an afternoon, because only one of them can be checked.
    """
    from .. import archive

    added = 0
    skipped = 0
    for row in archive.history(archive.KIND_CYCLONE_OUTLOOK, limit=limit):
        payload = row.get("payload") or {}
        # The bulletin's own sentences, not a summary of them.
        sentences: list[str] = []
        for basin in payload.get("basins") or []:
            for key in ("summary", "text", "narrative"):
                if basin.get(key):
                    sentences.append(str(basin[key]))
        for system in payload.get("systems") or []:
            if system.get("sentence"):
                sentences.append(str(system["sentence"]))

        text = " ".join(sentences).strip()
        if len(text) < MIN_DOCUMENT_CHARS:
            # Most days IMD publishes a short "no cyclone" line. That is a real
            # observation and the archive keeps it, but it is not a document
            # worth retrieving against, and padding it to look like one is
            # exactly the failure this module exists to avoid.
            skipped += 1
            continue

        ingest_text(
            doc_id=f"rsmc-{row['observedFor']}",
            title=f"IMD/RSMC Tropical Weather Outlook — {row['observedFor']}",
            authority="IMD / RSMC Tropical Cyclones, New Delhi",
            text=text,
            url=payload.get("sourceUrl", ""),
            doc_type="bulletin",
            published=row["observedFor"],
        )
        added += 1

    return {
        "added": added,
        "skippedTooShort": skipped,
        "corpus": len(load_corpus(force=True)),
        "note": (
            "Seeded from bulletins ORCA fetched itself. Regulatory documents "
            "(state fishing acts, protected-area notifications) still have to be "
            "ingested by URL, and only ones that actually resolve are stored."
        ),
    }


# --- Retrieval ---------------------------------------------------------------


def search(query: str, top_k: int = 5, corpus: list[Document] | None = None) -> list[Hit]:
    """BM25 over the corpus. Empty corpus returns nothing, and says nothing.

    No relevance floor is applied, because "the best of what is held" is not the
    same claim as "this answers the question" — the agent above decides whether
    a weak match is worth showing, and a score is returned so it can.
    """
    documents = corpus if corpus is not None else load_corpus()
    terms = _tokenize(query)
    if not documents or not terms:
        return []

    tokenized = [_tokenize(f"{d.title} {d.rule or ''} {d.text}") for d in documents]
    lengths = [len(t) for t in tokenized]
    avg_length = sum(lengths) / len(lengths) if lengths else 0.0
    if avg_length == 0:
        return []

    frequencies = [Counter(t) for t in tokenized]
    n = len(documents)
    containing = {
        term: sum(1 for f in frequencies if term in f) for term in set(terms)
    }

    hits: list[Hit] = []
    for index, document in enumerate(documents):
        score = 0.0
        matched: list[str] = []
        for term in set(terms):
            count = frequencies[index].get(term, 0)
            if not count:
                continue
            matched.append(term)
            df = containing[term]
            idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
            norm = 1 - BM25_B + BM25_B * (lengths[index] / avg_length)
            score += idf * (count * (BM25_K1 + 1)) / (count + BM25_K1 * norm)
        if score > 0:
            hits.append(Hit(document=document, score=score, matched=sorted(matched)))

    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:top_k]


def corpus_stats() -> dict:
    documents = load_corpus()
    by_authority: Counter = Counter(d.authority for d in documents)
    return {
        "documents": len(documents),
        "verified": sum(1 for d in documents if d.verified),
        "totalChars": sum(len(d.text) for d in documents),
        "byAuthority": dict(by_authority),
        "path": str(_corpus_path()),
        "retrieval": "bm25-lexical",
        "note": (
            "Documents enter only through a fetch that returned 200. 'verified' "
            "means this module witnessed that fetch and holds the content hash; "
            "text handed over by another scraper is real but unwitnessed here."
        ),
    }
