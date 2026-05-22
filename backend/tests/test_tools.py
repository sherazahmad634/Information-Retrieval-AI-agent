"""Unit tests for agent tools."""

from __future__ import annotations

import pytest

from app.api.deps import AppContainer
from app.services.tools.base import ToolError
from app.services.tools.calculator import CalculatorTool


@pytest.mark.asyncio
async def test_calculator_basic_arithmetic() -> None:
    tool = CalculatorTool()
    result = await tool.run(expression="2 * (3 + 4)")
    assert result.data["result"] == 14.0


@pytest.mark.asyncio
async def test_calculator_math_functions() -> None:
    tool = CalculatorTool()
    result = await tool.run(expression="sqrt(16) + log(e)")
    assert result.data["result"] == pytest.approx(5.0)


@pytest.mark.asyncio
async def test_calculator_rejects_unsafe_expression() -> None:
    tool = CalculatorTool()
    with pytest.raises(ToolError):
        await tool.run(expression="__import__('os').system('echo bad')")


@pytest.mark.asyncio
async def test_calculator_requires_expression() -> None:
    tool = CalculatorTool()
    with pytest.raises(ToolError):
        await tool.run()


@pytest.mark.asyncio
async def test_remember_and_recall(container: AppContainer) -> None:
    remember = container.tools.get("remember")
    recall = container.tools.get("recall")
    assert remember and recall
    await remember.run(key="preferred_language", value="Python 3.11")
    result = await recall.run(key="preferred_language")
    assert "Python 3.11" in result.content


@pytest.mark.asyncio
async def test_document_search_tool(container: AppContainer) -> None:
    await container.ingestion.ingest_text(
        title="Test doc",
        text="Cross-encoders re-rank retrieved candidates for precision.",
        source="t",
    )
    search = container.tools.get("document_search")
    assert search
    result = await search.run(query="What re-ranks candidates?", top_k=3)
    assert "Cross-encoders" in result.content
    assert result.data["results"]


@pytest.mark.asyncio
async def test_document_ingest_tool(container: AppContainer) -> None:
    ingest = container.tools.get("document_ingest")
    assert ingest
    result = await ingest.run(
        title="Note from agent",
        content="The user likes terse responses.",
        source="user-note",
    )
    assert result.data["document_id"]
    docs = await container.document_store.list_all()
    assert any(d.title == "Note from agent" for d in docs)


def test_tool_registry_rejects_duplicates(container: AppContainer) -> None:
    existing = container.tools.get("calculator")
    assert existing is not None
    with pytest.raises(ValueError):
        container.tools.register(existing)
