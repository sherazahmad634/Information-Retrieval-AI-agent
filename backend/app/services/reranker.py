"""Cross-encoder reranker for second-stage retrieval precision."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import Protocol

from app.core.logging import get_logger
from app.models.domain import ScoredChunk

logger = get_logger(__name__)


class Reranker(Protocol):
    """Reranker contract."""

    async def rerank(
        self, query: str, candidates: Sequence[ScoredChunk], top_k: int
    ) -> list[ScoredChunk]:
        """Return up to ``top_k`` candidates re-scored against ``query``."""
        ...


class CrossEncoderReranker:
    """Reranker backed by a sentence-transformers cross-encoder."""

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2") -> None:
        from sentence_transformers import CrossEncoder

        logger.info("loading_reranker_model", model=model_name)
        self._model = CrossEncoder(model_name)

    async def rerank(
        self, query: str, candidates: Sequence[ScoredChunk], top_k: int
    ) -> list[ScoredChunk]:
        if not candidates:
            return []

        pairs = [(query, sc.chunk.text) for sc in candidates]

        def _run() -> list[float]:
            return [float(s) for s in self._model.predict(pairs, show_progress_bar=False)]

        scores = await asyncio.to_thread(_run)
        reranked = [
            ScoredChunk(chunk=sc.chunk, score=score, source="rerank")
            for sc, score in zip(candidates, scores, strict=False)
        ]
        reranked.sort(key=lambda c: c.score, reverse=True)
        return reranked[:top_k]


class NoOpReranker:
    """Pass-through reranker used when reranking is disabled."""

    async def rerank(
        self, query: str, candidates: Sequence[ScoredChunk], top_k: int
    ) -> list[ScoredChunk]:
        sorted_candidates = sorted(candidates, key=lambda c: c.score, reverse=True)
        return list(sorted_candidates[:top_k])
