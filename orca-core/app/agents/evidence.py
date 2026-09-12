"""Evidence Retrieval — what the rules say, as opposed to what the sea is doing.

The tenth agent, and the only one that reads rather than measures.

Every other specialist answers a question about conditions: how high the waves
are, where the fishing grounds were advised, whether a cyclone is forming. Not
one of them can answer *"am I allowed?"* — and that question has consequences a
weather forecast does not. The geospatial agent will say a protected-area
boundary lies 4 km east; it has no idea what is prohibited inside it, whether
the closure is seasonal, or that the monsoon trawl ban ends on different dates
in different states.

**This agent is not the orchestrator.** That distinction is worth stating
because the obvious next step after "add retrieval" is to route everything
through it, and that would be wrong: asking for the wave height at Digha would
then perform a document search to answer a number. Retrieval sits in the
catalogue beside the others and the planner calls it when a question is about
rules, so the model decides whether to retrieve — which is what makes this
agentic rather than a search box.

It is deliberately quiet when it holds nothing. An empty or thin corpus produces
"no document in ORCA's collection covers this" rather than the nearest weak
match dressed up as an answer, because a confident wrong rule is worse for a
fisherman than an admission of ignorance: one sends them to ask a harbour
official, the other does not.
"""

from ..tools import evidence as store
from .base import Agent, AgentResult, Evidence, QueryContext

# Below this BM25 score a match is a few common words in common, not a document
# about the question. Chosen so a single mid-frequency term does not qualify.
RELEVANCE_FLOOR = 1.0


class EvidenceRetrievalAgent(Agent):
    name = "evidence_retrieval"
    description = (
        "Retrieves official marine rules, advisories and regulations — fishing "
        "bans and closed seasons, protected-area restrictions, safety-equipment "
        "requirements, what published bulletins actually said. Use for questions "
        "about what is permitted, required or prohibited, or when a claim needs "
        "an official document behind it. Not for current conditions."
    )
    handles = (
        "am i allowed",
        "is it legal",
        "fishing ban",
        "closed season",
        "trawl ban",
        "protected area rules",
        "regulation",
        "safety equipment",
        "what does the rule say",
        "official advisory",
        "restrict",
        "geofenc",
        "rule",
        "permit",
        "prohibit",
        "legal",
        "licence",
        "license",
    )
    is_stub = False

    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "What to look up, in English — the rule or topic, not the "
                    "user's whole sentence. E.g. 'monsoon trawl ban West Bengal'."
                ),
            },
            "topK": {
                "type": "integer",
                "description": "How many documents to return. Default 3.",
            },
        },
        "required": ["query"],
    }

    async def run(self, context: QueryContext) -> AgentResult:
        params = context.params or {}
        query = (params.get("query") or context.question or "").strip()
        top_k = int(params.get("topK") or 3)
        state_hint = params.get("state")

        if not state_hint:
            q_low = query.lower()
            for s in ("odisha", "west bengal", "tamil nadu", "andhra pradesh", "kerala", "gujarat", "goa", "maharashtra"):
                if s in q_low:
                    state_hint = s.title()
                    break

        corpus = store.load_corpus()
        if not corpus:
            # Said plainly rather than as an error: an empty collection is a
            # state of this deployment, not a failure of the request.
            return AgentResult(
                agent=self.name,
                summary=(
                    "ORCA holds no rule documents yet, so this cannot be answered "
                    "from an official source. Nothing has been guessed in their place."
                ),
                evidence=[],
                confidence=0.0,
                is_stub=False,
                data={"documents": 0, "hits": [], "corpusEmpty": True},
            )

        hits = [h for h in store.search(query, top_k=top_k, state=state_hint) if h.score >= RELEVANCE_FLOOR]

        if not hits:
            return AgentResult(
                agent=self.name,
                summary=(
                    f"No document in ORCA's collection of {len(corpus)} covers this. "
                    "Ask the local fisheries office or harbour authority rather than "
                    "treating silence here as permission."
                ),
                evidence=[],
                confidence=0.2,
                is_stub=False,
                data={"documents": len(corpus), "hits": [], "query": query},
            )

        lines: list[str] = []
        collected: list[Evidence] = []
        for hit in hits:
            document = hit.document
            statement = document.rule or document.text[:220].rstrip() + "…"
            active_flag = ""
            if hit.is_active_now is True:
                active_flag = f" [CURRENTLY ACTIVE: {document.effective_start} to {document.effective_end}]"
            elif hit.is_active_now is False:
                active_flag = f" [Seasonal window: {document.effective_start} to {document.effective_end}]"

            lines.append(f"{document.authority}: {statement}{active_flag}")
            collected.append(
                Evidence(
                    source=f"{document.authority} — {document.title}",
                    label=document.doc_type.replace("_", " ").title(),
                    value=f"{statement}{active_flag}",
                    observed_at=document.published,
                    note=(
                        f"State: {document.applicable_state} | {document.url}"
                        + ("" if document.verified else " (text supplied by another ORCA "
                           "scraper; this module did not witness the fetch)")
                    ),
                )
            )

        # Confidence tracks the retrieval, not the rule. A strong lexical match
        # against a verified document is a confident *retrieval*; whether the
        # document settles the user's case is a judgement ORCA does not make.
        best = hits[0]
        confidence = min(0.9, 0.45 + best.score / 20.0)
        if not best.document.verified:
            confidence *= 0.8

        return AgentResult(
            agent=self.name,
            summary=" ".join(lines),
            evidence=collected,
            confidence=round(confidence, 2),
            is_stub=False,
            data={
                "documents": len(corpus),
                "query": query,
                "hits": [h.to_dict() for h in hits],
            },
        )
