"""Hybrid retrieval service.

Implements a two-branch retrieval pipeline combining lexical (BM25) and
dense (vector) results with **Reciprocal Rank Fusion** (RRF). An optional
cross-encoder rerank stage produces the final, high-precision result list.

Reference: Cormack et al., "Reciprocal rank fusion outperforms condorcet and
individual rank learning methods" (SIGIR 2009).
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from rank_bm25 import BM25Okapi

from app.core.exceptions import RetrievalError
from app.core.logging import get_logger
from app.models.domain import Chunk, ScoredChunk
from app.repositories.vector_store import VectorStore
from app.services.embedder import Embedder
from app.services.reranker import Reranker
from app.utils.text import tokenize

logger = get_logger(__name__)


class HybridRetriever:
    """Hybrid lexical + dense retriever with optional reranking.

    The retriever rebuilds its BM25 index lazily — when the underlying vector
    store grows or shrinks the next ``retrieve`` call recomputes it.
    """

    def __init__(
        self,
        *,
        vector_store: VectorStore,
        embedder: Embedder,
        reranker: Reranker,
        top_k_retrieval: int = 20,
        top_k_rerank: int = 5,
        rrf_k: int = 60,
    ) -> None:
        self._vector_store = vector_store
        self._embedder = embedder
        self._reranker = reranker
        self._top_k_retrieval = top_k_retrieval
        self._top_k_rerank = top_k_rerank
        self._rrf_k = rrf_k

        self._bm25: BM25Okapi | None = None
        self._bm25_chunks: list[Chunk] = []
        self._bm25_cached_count: int = -1
        self._index_lock = asyncio.Lock()

    async def invalidate_index(self) -> None:
        """Drop the cached BM25 index. Called after ingestion/deletion."""
        async with self._index_lock:
            self._bm25 = None
            self._bm25_chunks = []
            self._bm25_cached_count = -1

    async def retrieve(
        self,
        query: str,
        *,
        top_k: int | None = None,
        use_reranker: bool = True,
        filters: dict[str, Any] | None = None,
    ) -> list[ScoredChunk]:
        """Run the full hybrid retrieval pipeline for ``query``."""
        if not query.strip():
            raise RetrievalError("Query must not be empty.")

        final_k = top_k or self._top_k_rerank
        started = time.perf_counter()

        try:
            dense_task = asyncio.create_task(self._dense_search(query, filters))
            sparse_task = asyncio.create_task(self._sparse_search(query, filters))
            dense, sparse = await asyncio.gather(dense_task, sparse_task)
        except Exception as exc:  # pragma: no cover - defensive
            raise RetrievalError("Retrieval failed.", details={"reason": str(exc)}) from exc

        fused = self._reciprocal_rank_fusion(dense, sparse)
        if not fused:
            return []

        candidate_count = max(final_k, self._top_k_rerank)
        candidates = fused[:candidate_count]

        if use_reranker:
            results = await self._reranker.rerank(query, candidates, top_k=final_k)
        else:
            results = candidates[:final_k]

        logger.info(
            "retrieval_complete",
            query_len=len(query),
            dense_hits=len(dense),
            sparse_hits=len(sparse),
            returned=len(results),
            ms=round((time.perf_counter() - started) * 1000, 2),
        )
        return results

    # ------------------------------------------------------------------ dense

    async def _dense_search(
        self, query: str, filters: dict[str, Any] | None
    ) -> list[ScoredChunk]:
        embedding = await self._embedder.embed_one(query)
        return await self._vector_store.search(
            embedding, top_k=self._top_k_retrieval, filters=filters
        )

    # ----------------------------------------------------------------- sparse

    async def _sparse_search(
        self, query: str, filters: dict[str, Any] | None
    ) -> list[ScoredChunk]:
        await self._ensure_bm25_index()
        if not self._bm25 or not self._bm25_chunks:
            return []

        tokens = tokenize(query)
        if not tokens:
            return []

        scores = self._bm25.get_scores(tokens)
        indexed = list(enumerate(scores))
        indexed.sort(key=lambda x: x[1], reverse=True)

        out: list[ScoredChunk] = []
        for idx, score in indexed[: self._top_k_retrieval]:
            if score <= 0:
                continue
            chunk = self._bm25_chunks[idx]
            if filters and not _match_filters(chunk, filters):
                continue
            out.append(ScoredChunk(chunk=chunk, score=float(score), source="bm25"))
        return out

    async def _ensure_bm25_index(self) -> None:
        async with self._index_lock:
            current = await self._vector_store.count()
            if self._bm25 is not None and current == self._bm25_cached_count:
                return
            chunks = await self._vector_store.all_chunks()
            if not chunks:
                self._bm25 = None
                self._bm25_chunks = []
                self._bm25_cached_count = 0
                return
            self._bm25_chunks = chunks
            tokenised = [tokenize(c.text) for c in chunks]
            self._bm25 = BM25Okapi(tokenised)
            self._bm25_cached_count = current
            logger.info("bm25_index_built", chunks=len(chunks))

    # ----------------------------------------------------------------- fusion

    def _reciprocal_rank_fusion(
        self, dense: list[ScoredChunk], sparse: list[ScoredChunk]
    ) -> list[ScoredChunk]:
        """Combine two ranked lists with RRF."""
        scores: dict[str, float] = {}
        chunks: dict[str, ScoredChunk] = {}
        for ranked in (dense, sparse):
            for rank, sc in enumerate(ranked):
                scores[sc.chunk.id] = scores.get(sc.chunk.id, 0.0) + 1.0 / (self._rrf_k + rank + 1)
                chunks[sc.chunk.id] = sc
        ordered = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [
            ScoredChunk(chunk=chunks[cid].chunk, score=score, source="hybrid")
            for cid, score in ordered
        ]


def _match_filters(chunk: Chunk, filters: dict[str, Any]) -> bool:
    for k, v in filters.items():
        if k == "document_id" and chunk.document_id != v:
            return False
        if k in chunk.metadata and chunk.metadata[k] != v:
            return False
    return True
