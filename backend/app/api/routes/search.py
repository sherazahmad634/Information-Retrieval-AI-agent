"""Direct retrieval endpoint (no LLM)."""

from __future__ import annotations

import time

from fastapi import APIRouter

from app.api.deps import DocumentStoreDep, RetrieverDep
from app.models.schemas import CitationChunk, SearchRequest, SearchResponse

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=SearchResponse, summary="Hybrid search over the corpus")
async def search(
    request: SearchRequest,
    retriever: RetrieverDep,
    document_store: DocumentStoreDep,
) -> SearchResponse:
    """Run hybrid (BM25 + dense + optional rerank) retrieval and return raw chunks."""
    started = time.perf_counter()
    scored = await retriever.retrieve(
        request.query,
        top_k=request.top_k,
        use_reranker=request.use_reranker,
        filters=request.filters,
    )

    titles: dict[str, str] = {}
    for sc in scored:
        if sc.chunk.document_id and sc.chunk.document_id not in titles:
            doc = await document_store.get(sc.chunk.document_id)
            titles[sc.chunk.document_id] = doc.title if doc else "Unknown"

    results = [
        CitationChunk(
            chunk_id=sc.chunk.id,
            document_id=sc.chunk.document_id,
            document_title=titles.get(sc.chunk.document_id, "Unknown"),
            text=sc.chunk.text,
            score=round(sc.score, 4),
            source=sc.source,
            position=sc.chunk.position,
        )
        for sc in scored
    ]
    return SearchResponse(
        query=request.query,
        results=results,
        elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
    )
