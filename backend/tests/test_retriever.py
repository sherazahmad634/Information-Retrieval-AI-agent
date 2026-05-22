"""Unit tests for the hybrid retriever."""

from __future__ import annotations

import pytest

from app.api.deps import AppContainer


@pytest.mark.asyncio
async def test_retriever_returns_relevant_chunks(container: AppContainer) -> None:
    await container.ingestion.ingest_text(
        title="IR primer",
        text=(
            "BM25 is a probabilistic ranking function. It uses term frequency saturation. "
            "Dense retrieval uses neural embeddings. Hybrid retrieval combines them."
        ),
        source="test",
    )
    results = await container.retriever.retrieve("What is BM25?", top_k=3)
    assert results
    assert any("BM25" in r.chunk.text for r in results)
    # Hybrid retrieval should never return more than top_k after rerank.
    assert len(results) <= 3


@pytest.mark.asyncio
async def test_retriever_empty_corpus(container: AppContainer) -> None:
    results = await container.retriever.retrieve("anything", top_k=5)
    assert results == []


@pytest.mark.asyncio
async def test_retriever_rejects_empty_query(container: AppContainer) -> None:
    from app.core.exceptions import RetrievalError

    with pytest.raises(RetrievalError):
        await container.retriever.retrieve("   ", top_k=3)


@pytest.mark.asyncio
async def test_index_invalidation_after_delete(container: AppContainer) -> None:
    doc = await container.ingestion.ingest_text(
        title="t", text="BM25 ranking discussion." * 5, source="t"
    )
    before = await container.vector_store.count()
    assert before > 0
    removed = await container.ingestion.delete(doc.id)
    assert removed is True
    after = await container.vector_store.count()
    assert after == 0
