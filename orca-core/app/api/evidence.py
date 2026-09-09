"""The rule corpus: what is in it, and how documents get in.

Ingestion is a POST because it reaches out and fetches. It is the only way a
document enters the corpus, and it refuses anything that does not resolve — so
this route is also the thing that makes a fabricated citation impossible rather
than merely discouraged.
"""

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel, Field

from ..tools import evidence as store

router = APIRouter(prefix="/evidence", tags=["evidence"])


class IngestRequest(BaseModel):
    url: str = Field(..., description="Must resolve; a 404 is refused, not stored")
    title: str
    authority: str = Field(..., description="The body that issued it, e.g. 'MoEFCC'")
    doc_type: str = "document"
    published: str | None = None
    rule: str | None = Field(
        None, description="One-line actionable form, if the document states a clear rule"
    )


@router.get("/stats")
async def evidence_stats(response: Response) -> dict:
    """How many documents are held, and how many were witnessed being fetched."""
    response.headers["Cache-Control"] = "no-store"
    return store.corpus_stats()


@router.get("/search")
async def evidence_search(
    response: Response,
    q: str = Query(..., min_length=2),
    topK: int = Query(5, ge=1, le=20),
) -> dict:
    """Retrieve against the corpus. An empty corpus returns nothing, not a guess."""
    response.headers["Cache-Control"] = "no-store"
    hits = store.search(q, top_k=topK)
    return {
        "query": q,
        "corpusSize": len(store.load_corpus()),
        "count": len(hits),
        "hits": [h.to_dict() for h in hits],
    }


@router.post("/ingest")
async def evidence_ingest(request: IngestRequest) -> dict:
    """Fetch a document and store it, or explain why it was refused."""
    try:
        document = await store.ingest_url(
            url=request.url,
            title=request.title,
            authority=request.authority,
            doc_type=request.doc_type,
            published=request.published,
            rule=request.rule,
        )
    except store.EvidenceError as exc:
        # 422 rather than 502: the request named a document that cannot be
        # verified, which is a problem with what was asked for.
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"stored": True, "document": document.summary()}


@router.post("/seed-from-archive")
async def evidence_seed(response: Response) -> dict:
    """Build documents from bulletins ORCA has already fetched and kept.

    The corpus's sustainable source. Nothing is fetched here — this reads the
    archive, so it grows only as fast as real bulletins arrive.
    """
    response.headers["Cache-Control"] = "no-store"
    return store.seed_from_archive()
