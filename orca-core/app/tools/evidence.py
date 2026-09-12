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
from dataclasses import dataclass, field, asdict, fields
from datetime import datetime, timezone
from functools import lru_cache
from html.parser import HTMLParser
from pathlib import Path

import httpx

try:
    from ..config import get_settings
except (ImportError, ValueError):
    import sys
    _pkg_root = str(Path(__file__).resolve().parent.parent.parent)
    if _pkg_root not in sys.path:
        sys.path.insert(0, _pkg_root)
    from app.config import get_settings

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

    # Structured legal & temporal metadata
    applicable_state: str = "All-India"
    effective_start: str | None = None
    effective_end: str | None = None
    regulation_type: str = "document"

    # --- provenance: written by ingestion, never by hand ---------------------
    fetched_at: str = ""
    http_status: int = 0
    byte_count: int = 0
    content_sha256: str = ""

    #: Set at load time for documents whose provenance is known to be untrue.
    #: See :func:`quarantined_ids`. Not persisted — it is derived every load, so
    #: the corpus file on disk is never rewritten to carry a judgement.
    quarantined: bool = False

    @property
    def verified(self) -> bool:
        """Did this come from a fetch that actually succeeded?

        Anything loaded from a corpus file that lacks provenance reads as
        unverified, so a hand-edited entry cannot pass itself off as fetched.

        Quarantine is checked first because these fields can be forged: the
        statutory seed wrote ``http_status: 200`` and a ``content_sha256`` for
        documents it never fetched, and a hash taken over invented text is
        perfectly self-consistent. Provenance that cannot be distinguished
        structurally has to be distinguished by name.
        """
        if self.quarantined:
            return False
        return bool(self.content_sha256) and 200 <= self.http_status < 300

    def is_active_now(self, reference_date: datetime | None = None) -> bool | None:
        """Returns True if this seasonal restriction is active on reference_date (defaults to UTC now)."""
        if not self.effective_start or not self.effective_end:
            return None
        now = reference_date or datetime.now(timezone.utc)
        try:
            s = self.effective_start.strip()
            e = self.effective_end.strip()
            # Handle MM-DD format e.g. "04-15" and "06-14"
            if len(s) == 5 and s[2] == "-" and len(e) == 5 and e[2] == "-":
                sm, sd = int(s[:2]), int(s[3:])
                em, ed = int(e[:2]), int(e[3:])
                s_dt = datetime(now.year, sm, sd, tzinfo=timezone.utc)
                e_dt = datetime(now.year, em, ed, 23, 59, 59, tzinfo=timezone.utc)
                if s_dt <= e_dt:
                    return s_dt <= now <= e_dt
                else:  # Wraps across year-end e.g. 11-01 to 05-31
                    return now >= s_dt or now <= e_dt
            else:
                s_dt = datetime.fromisoformat(s).replace(tzinfo=timezone.utc)
                e_dt = datetime.fromisoformat(e).replace(tzinfo=timezone.utc)
                return s_dt <= now <= e_dt
        except Exception:
            return None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["verified"] = self.verified
        d["isActiveNow"] = self.is_active_now()
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
    dense_score: float = 0.0
    is_active_now: bool | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.document.id,
            "title": self.document.title,
            "authority": self.document.authority,
            "url": self.document.url,
            "published": self.document.published,
            "rule": self.document.rule,
            "applicableState": self.document.applicable_state,
            "regulationType": self.document.regulation_type,
            "effectiveStart": self.document.effective_start,
            "effectiveEnd": self.document.effective_end,
            "isActiveNow": self.is_active_now,
            "verified": self.document.verified,
            "score": round(self.score, 3),
            "denseScore": round(self.dense_score, 3),
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


#: The hand-written seed file. Every document in it is unverified by construction:
#: it carries no URL, no status code and no hash. The same entries were also copied
#: into the live corpus with a fabricated ``http_status: 200``, a hash taken over
#: their own invented text, and ``fetched_at`` stamps seventy microseconds apart
#: across three different government servers — which no real fetch can do.
#:
#: The file is kept, deliberately. Nothing is deleted; it is simply no longer
#: allowed to answer anybody.
_STATUTORY_SEED = (
    Path(__file__).resolve().parent.parent.parent / "data" / "evidence" / "statutory_marine_corpus.json"
)


@lru_cache(maxsize=1)
def quarantined_ids() -> frozenset[str]:
    """Ids of documents whose recorded provenance is known to be untrue.

    Derived from the seed file rather than hardcoded, so the two cannot drift
    apart. If the seed file is removed the quarantine empties on its own.
    """
    try:
        raw = json.loads(_STATUTORY_SEED.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return frozenset()
    items = raw if isinstance(raw, list) else raw.get("documents", [])
    return frozenset(
        str(item["id"]) for item in items if isinstance(item, dict) and item.get("id")
    )


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
    valid_fields = {f.name for f in fields(Document)}
    blocked = quarantined_ids()
    docs = []
    for item in raw:
        doc = Document(
            **{k: v for k, v in item.items() if k in valid_fields and k not in ("verified", "quarantined")}
        )
        # Applied at load rather than written to disk: the corpus file keeps
        # exactly what it always held, and the judgement lives in code where it
        # can be read and argued with.
        doc.quarantined = doc.id in blocked
        docs.append(doc)
    _cache = (stamp, docs)
    return docs


def save_corpus(documents: list[Document]) -> None:
    global _cache
    path = _corpus_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [
        {k: v for k, v in d.to_dict().items() if k != "verified" and k != "isActiveNow"} for d in documents
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
    applicable_state: str = "All-India",
    effective_start: str | None = None,
    effective_end: str | None = None,
    regulation_type: str = "document",
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
        applicable_state=applicable_state,
        effective_start=effective_start,
        effective_end=effective_end,
        regulation_type=regulation_type,
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
    applicable_state: str = "All-India",
    effective_start: str | None = None,
    effective_end: str | None = None,
    regulation_type: str = "document",
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
        applicable_state=applicable_state,
        effective_start=effective_start,
        effective_end=effective_end,
        regulation_type=regulation_type,
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
    try:
        from .. import archive
    except (ImportError, ValueError):
        from app import archive

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


def seed_statutory_corpus() -> dict[str, Any]:
    """Disabled. The seed file's documents were never fetched from anywhere.

    This ran at every startup and copied fourteen hand-written passages into the
    live corpus wearing forged provenance — ``http_status: 200``, a hash over
    their own invented text, and ``fetched_at`` stamps seventy microseconds apart
    across three different government servers. They carried plausible identifiers
    (``INCOIS-OSF-2026-041``, ``IMD-MAR-SQ-89``) and URLs pointing at homepages
    that do not contain the quoted text.

    Nothing has been deleted: the file is still on disk, the entries are still in
    the corpus, and :func:`corpus_stats` still counts them. They are quarantined
    (see :func:`quarantined_ids`) so they cannot reach an answer.

    A fisherman acting on a fabricated closure date is worse off than one told
    nothing, because a confident wrong answer displaces the instinct to go and
    ask. Re-enabling this needs the documents re-ingested through
    :func:`ingest_url`, which records what the server actually returned.
    """
    return {
        "added": 0,
        "status": "disabled_unverified_provenance",
        "quarantined": len(quarantined_ids()),
        "detail": "See docs/ml-plan.md §6. Re-ingest through ingest_url to restore.",
    }


def _seed_statutory_corpus_disabled() -> dict[str, Any]:
    """The original implementation, kept for reference. Not called."""
    possible_paths = [
        Path(__file__).resolve().parent.parent.parent / "data" / "evidence" / "statutory_marine_corpus.json",
        Path(__file__).resolve().parent.parent.parent.parent.parent / "legacy" / "data" / "data" / "evidence" / "statutory_marine_corpus.json",
    ]
    target_file = None
    for p in possible_paths:
        if p.exists():
            target_file = p
            break

    if not target_file:
        return {"added": 0, "status": "no_source_file"}

    try:
        raw_items = json.loads(target_file.read_text(encoding="utf-8"))
    except Exception as exc:
        log.warning("Could not read statutory corpus from %s: %s", target_file, exc)
        return {"added": 0, "status": "read_error", "error": str(exc)}

    existing_docs = {d.id: d for d in load_corpus()}
    added = 0
    for item in raw_items:
        doc_id = item.get("id")
        if not doc_id or doc_id in existing_docs:
            continue

        excerpt = item.get("excerpt", "").strip()
        if not excerpt:
            continue

        title = item.get("title", doc_id)
        doc_type = item.get("documentType", "statutory_act")
        combined_text = f"{title.lower()} {excerpt.lower()}"

        # State jurisdiction inference
        app_state = "All-India"
        detected_states = []
        for s in ("odisha", "west bengal", "tamil nadu", "andhra pradesh", "kerala", "gujarat", "goa", "maharashtra"):
            if s in combined_text:
                detected_states.append(s.title())
        if detected_states:
            app_state = ", ".join(detected_states)

        # Regulation type inference
        reg_type = "document"
        if "trawl ban" in combined_text or "monsoon" in combined_text:
            reg_type = "SEASONAL_BAN"
        elif "protected area" in combined_text or "sanctuary" in combined_text or "national park" in combined_text:
            reg_type = "PROTECTED_AREA"
        elif "port warning" in combined_text or "signal" in combined_text:
            reg_type = "PORT_SAFETY"
        elif "vhf" in combined_text or "safety equipment" in combined_text or "sar" in combined_text:
            reg_type = "SAFETY_EQUIPMENT"
        elif "wave" in combined_text or "swell" in combined_text:
            reg_type = "WAVE_ALERT"

        # Seasonal ban dates inference
        eff_start = None
        eff_end = None
        if "15th april" in combined_text or "15 apr" in combined_text:
            eff_start = "04-15"
        elif "1st june" in combined_text or "01 jun" in combined_text:
            eff_start = "06-01"
        elif "november 1" in combined_text or ("nov" in combined_text and "gahirmatha" in combined_text):
            eff_start = "11-01"

        if "14th june" in combined_text or "14 jun" in combined_text:
            eff_end = "06-14"
        elif "31st july" in combined_text or "31 jul" in combined_text:
            eff_end = "07-31"
        elif "may 31" in combined_text and "gahirmatha" in combined_text:
            eff_end = "05-31"

        content_bytes = excerpt.encode("utf-8")
        doc = Document(
            id=doc_id,
            title=title,
            authority=item.get("sourceAuthority", "Indian Maritime Authority"),
            url=item.get("officialUrl", ""),
            text=excerpt,
            doc_type=doc_type,
            published=item.get("publicationDate", "2026-01-01"),
            rule=item.get("complianceRule"),
            applicable_state=app_state,
            effective_start=eff_start,
            effective_end=eff_end,
            regulation_type=reg_type,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            http_status=200,
            byte_count=len(content_bytes),
            content_sha256=hashlib.sha256(content_bytes).hexdigest(),
        )
        existing_docs[doc_id] = doc
        added += 1

    if added > 0:
        save_corpus(list(existing_docs.values()))
        log.info("Seeded %d statutory marine documents into evidence corpus", added)

    return {
        "added": added,
        "corpus_total": len(existing_docs),
        "status": "ok",
    }


# --- Semantic Vectorization & Hybrid Retrieval -------------------------------


def _vectorize(text: str) -> dict[str, float]:
    """Lightweight character n-gram + subword TF-IDF vectorizer (pure Python, 0 extra RAM)."""
    tokens = _tokenize(text)
    if not tokens:
        return {}
    counts: Counter[str] = Counter()
    for t in tokens:
        counts[f"w_{t}"] += 1.0
    cleaned = " " + " ".join(tokens) + " "
    for n in (3, 4):
        for i in range(len(cleaned) - n + 1):
            ngram = cleaned[i : i + n]
            if not ngram.isspace():
                counts[f"ng_{ngram}"] += 0.5

    norm = math.sqrt(sum(v * v for v in counts.values()))
    if norm == 0:
        return {}
    return {k: v / norm for k, v in counts.items()}


def _cosine_similarity(vec_a: dict[str, float], vec_b: dict[str, float]) -> float:
    """Cosine similarity between two normalized sparse vectors."""
    if not vec_a or not vec_b:
        return 0.0
    small, big = (vec_a, vec_b) if len(vec_a) <= len(vec_b) else (vec_b, vec_a)
    return sum(v * big[k] for k, v in small.items() if k in big)


def search(
    query: str,
    top_k: int = 5,
    corpus: list[Document] | None = None,
    state: str | None = None,
    active_only: bool = False,
    reference_date: datetime | None = None,
) -> list[Hit]:
    """Hybrid BM25 + Dense Semantic search with state and temporal metadata awareness.

    Empty corpus returns nothing. Combines lexical BM25 term weighting with subword
    dense vector similarity to capture exact statutory numbers and paraphrased intents.
    """
    documents = corpus if corpus is not None else load_corpus()
    # A document whose provenance is known to be untrue must never reach an
    # answer. Filtered here rather than at load so the corpus stays inspectable
    # through `corpus_stats` and the API, and only retrieval is closed to it.
    documents = [doc for doc in documents if not doc.quarantined]
    terms = _tokenize(query)
    if not documents or not terms:
        return []

    if active_only:
        documents = [d for d in documents if d.is_active_now(reference_date) is True]
        if not documents:
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

    # 1. BM25 scoring
    bm25_scores: list[float] = [0.0] * n
    matched_by_doc: list[list[str]] = [[] for _ in range(n)]

    for index in range(n):
        doc_matched: list[str] = []
        doc_score = 0.0
        for term in set(terms):
            count = frequencies[index].get(term, 0)
            if not count:
                continue
            doc_matched.append(term)
            df = containing[term]
            idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
            norm = 1 - BM25_B + BM25_B * (lengths[index] / avg_length)
            doc_score += idf * (count * (BM25_K1 + 1)) / (count + BM25_K1 * norm)
        bm25_scores[index] = doc_score
        matched_by_doc[index] = sorted(doc_matched)

    # 2. Dense Semantic Cosine Vectorization
    query_vec = _vectorize(query)
    doc_vectors = [_vectorize(f"{d.title} {d.rule or ''} {d.text}") for d in documents]
    dense_scores: list[float] = [_cosine_similarity(query_vec, dv) for dv in doc_vectors]

    hits: list[Hit] = []
    for index, document in enumerate(documents):
        b_score = bm25_scores[index]
        d_score = dense_scores[index]

        # Consider candidate if BM25 matched or dense similarity >= 0.12
        if b_score <= 0.0 and d_score < 0.12:
            continue

        # Hybrid fusion: BM25 score + dense semantic contribution
        score = b_score + (8.0 * d_score if d_score >= 0.12 else 0.0)

        # State jurisdiction boost
        if state:
            s_clean = state.lower()
            doc_state = document.applicable_state.lower()
            if s_clean in doc_state or doc_state == "all-india":
                score *= 1.25

        # Active regulation boost
        is_active = document.is_active_now(reference_date)
        if is_active is True:
            score *= 1.1

        hits.append(
            Hit(
                document=document,
                score=score,
                matched=matched_by_doc[index],
                dense_score=d_score,
                is_active_now=is_active,
            )
        )

    hits.sort(key=lambda h: (h.score, h.dense_score), reverse=True)
    return hits[:top_k]


def corpus_stats() -> dict:
    documents = load_corpus()
    by_authority: Counter = Counter(d.authority for d in documents)
    by_type: Counter = Counter(d.regulation_type for d in documents)
    by_state: Counter = Counter(d.applicable_state for d in documents)
    return {
        "documents": len(documents),
        "verified": sum(1 for d in documents if d.verified),
        "totalChars": sum(len(d.text) for d in documents),
        "byAuthority": dict(by_authority),
        "byRegulationType": dict(by_type),
        "byState": dict(by_state),
        "path": str(_corpus_path()),
        "retrieval": "hybrid-bm25-dense-rrf",
        "note": (
            "Documents enter only through a fetch that returned 200. 'verified' "
            "means this module witnessed that fetch and holds the content hash; "
            "text handed over by another scraper is real but unwitnessed here."
        ),
    }
