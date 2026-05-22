"""End-to-end tests for the tool-using agent (mock LLM)."""

from __future__ import annotations

import pytest

from app.api.deps import AppContainer


@pytest.mark.asyncio
async def test_agent_answers_from_corpus(container: AppContainer) -> None:
    await container.ingestion.ingest_text(
        title="Hybrid retrieval",
        text=(
            "Reciprocal Rank Fusion combines BM25 and dense retrieval. "
            "It outperforms either branch alone in BEIR benchmarks."
        ),
        source="seed",
    )
    response = await container.agent.chat(query="What is reciprocal rank fusion?")
    assert response.answer
    assert response.citations
    assert response.iterations >= 1
    assert any("Reciprocal" in c.text for c in response.citations)


@pytest.mark.asyncio
async def test_agent_calls_document_search(container: AppContainer) -> None:
    await container.ingestion.ingest_text(
        title="t", text="BM25 is a probabilistic ranking function.", source="s"
    )
    response = await container.agent.chat(query="describe BM25")
    tools_used = {t.tool for t in response.traces}
    assert "document_search" in tools_used


@pytest.mark.asyncio
async def test_agent_respects_max_iterations(container: AppContainer) -> None:
    # No documents — agent should still terminate cleanly.
    response = await container.agent.chat(query="anything?")
    assert response.iterations <= container.agent._max_iterations  # type: ignore[attr-defined]
    assert isinstance(response.answer, str)


@pytest.mark.asyncio
async def test_agent_streaming(container: AppContainer) -> None:
    await container.ingestion.ingest_text(
        title="x", text="Dense retrieval uses neural embeddings.", source="s"
    )
    events: list[dict[str, object]] = []
    async for event in container.agent.stream(query="What is dense retrieval?"):
        events.append(event)
    event_types = {e["event"] for e in events}
    assert "citations" in event_types
    assert "token" in event_types
    assert "done" in event_types
