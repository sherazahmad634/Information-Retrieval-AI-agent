"""Working memory + long-term memory for the agent.

Two complementary stores:

* **Short-term (working) memory** — an in-process, per-session rolling buffer
  of recent messages. Used to keep conversational context without overflowing
  the LLM context window.
* **Long-term memory** — a SQLite-backed key/value store that survives
  restarts. Populated by the ``remember`` tool.
"""

from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import aiosqlite

from app.models.schemas import ChatMessage

_SCHEMA = """
CREATE TABLE IF NOT EXISTS memory (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


# ---------------------------------------------------------------------------
# Working (short-term) memory
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class _Session:
    messages: deque[ChatMessage] = field(default_factory=deque)


class WorkingMemory:
    """Bounded per-session rolling buffer of chat turns."""

    def __init__(self, max_turns: int = 20) -> None:
        self._max_turns = max_turns
        self._sessions: dict[str, _Session] = {}
        self._lock = asyncio.Lock()

    async def append(self, session_id: str, message: ChatMessage) -> None:
        """Append a message to the named session."""
        async with self._lock:
            session = self._sessions.setdefault(session_id, _Session())
            session.messages.append(message)
            while len(session.messages) > self._max_turns:
                session.messages.popleft()

    async def extend(self, session_id: str, messages: Iterable[ChatMessage]) -> None:
        for m in messages:
            await self.append(session_id, m)

    async def history(self, session_id: str) -> list[ChatMessage]:
        async with self._lock:
            session = self._sessions.get(session_id)
            return list(session.messages) if session else []

    async def clear(self, session_id: str) -> None:
        async with self._lock:
            self._sessions.pop(session_id, None)


# ---------------------------------------------------------------------------
# Long-term memory
# ---------------------------------------------------------------------------


class MemoryService:
    """Async SQLite-backed key/value store for durable agent memory."""

    def __init__(self, path: str) -> None:
        self._path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)

    async def init(self) -> None:
        async with aiosqlite.connect(self._path) as db:
            await db.executescript(_SCHEMA)
            await db.commit()

    async def set(self, key: str, value: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self._path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO memory (key, value, updated_at) VALUES (?, ?, ?)",
                (key, value, now),
            )
            await db.commit()

    async def get(self, key: str) -> str | None:
        async with aiosqlite.connect(self._path) as db:
            cursor = await db.execute("SELECT value FROM memory WHERE key = ?", (key,))
            row = await cursor.fetchone()
            return row[0] if row else None

    async def delete(self, key: str) -> bool:
        async with aiosqlite.connect(self._path) as db:
            cursor = await db.execute("DELETE FROM memory WHERE key = ?", (key,))
            await db.commit()
            return cursor.rowcount > 0

    async def all(self) -> dict[str, str]:
        async with aiosqlite.connect(self._path) as db:
            cursor = await db.execute("SELECT key, value FROM memory ORDER BY key ASC")
            rows = await cursor.fetchall()
            return {row[0]: row[1] for row in rows}
