"""Unit tests for memory services."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.models.schemas import ChatMessage
from app.services.memory import MemoryService, WorkingMemory


@pytest.mark.asyncio
async def test_long_term_memory_roundtrip(tmp_path: Path) -> None:
    mem = MemoryService(str(tmp_path / "memory.db"))
    await mem.init()
    await mem.set("preferred_language", "Python")
    assert await mem.get("preferred_language") == "Python"
    await mem.set("preferred_language", "Python 3.11")  # upsert
    assert await mem.get("preferred_language") == "Python 3.11"
    assert await mem.delete("preferred_language") is True
    assert await mem.get("preferred_language") is None


@pytest.mark.asyncio
async def test_long_term_memory_lists_all(tmp_path: Path) -> None:
    mem = MemoryService(str(tmp_path / "memory.db"))
    await mem.init()
    await mem.set("a", "1")
    await mem.set("b", "2")
    items = await mem.all()
    assert items == {"a": "1", "b": "2"}


@pytest.mark.asyncio
async def test_working_memory_respects_bound() -> None:
    mem = WorkingMemory(max_turns=3)
    for i in range(5):
        await mem.append("s1", ChatMessage(role="user", content=f"m{i}"))
    history = await mem.history("s1")
    assert len(history) == 3
    assert history[0].content == "m2"
    assert history[-1].content == "m4"


@pytest.mark.asyncio
async def test_working_memory_session_isolation() -> None:
    mem = WorkingMemory()
    await mem.append("a", ChatMessage(role="user", content="hello-a"))
    await mem.append("b", ChatMessage(role="user", content="hello-b"))
    assert (await mem.history("a"))[0].content == "hello-a"
    assert (await mem.history("b"))[0].content == "hello-b"
    await mem.clear("a")
    assert await mem.history("a") == []
