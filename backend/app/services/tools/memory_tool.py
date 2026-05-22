"""Working-memory tool — lets the agent persist and recall conversational notes.

This satisfies the assignment requirement for a working-memory system. Memory
entries live in the same SQLite document store but are tagged with a
``kind=memory`` flag so they don't pollute the main document corpus.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.services.tools.base import Tool, ToolError, ToolResult

if TYPE_CHECKING:
    from app.services.memory import MemoryService


class RememberTool(Tool):
    """Save a short fact to long-term agent memory."""

    name = "remember"
    description = (
        "Persist a short fact about the user, their preferences, or context that should "
        "be available in future conversations. Use this when the user states a stable "
        "preference, identity fact, or any information they ask you to remember. Keep "
        "entries short (one sentence). The entry is keyed by `key` so later calls "
        "overwrite prior values for the same key."
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "key": {
                "type": "string",
                "description": "Short identifier for the memory, e.g. 'preferred_language'.",
            },
            "value": {
                "type": "string",
                "description": "The fact to remember (one sentence).",
            },
        },
        "required": ["key", "value"],
        "additionalProperties": False,
    }

    def __init__(self, memory: "MemoryService") -> None:
        self._memory = memory

    async def run(self, **kwargs: Any) -> ToolResult:
        key = kwargs.get("key")
        value = kwargs.get("value")
        if not isinstance(key, str) or not key.strip():
            raise ToolError("`key` is required.")
        if not isinstance(value, str) or not value.strip():
            raise ToolError("`value` is required.")
        await self._memory.set(key.strip(), value.strip())
        return ToolResult(
            content=f"Stored memory '{key}'.",
            data={"key": key, "value": value},
        )


class RecallTool(Tool):
    """Look up a previously remembered fact."""

    name = "recall"
    description = (
        "Look up a previously remembered fact by key, or list all keys when called with "
        "no arguments. Use this to retrieve user preferences or context the user "
        "previously asked you to remember."
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "key": {
                "type": "string",
                "description": "Memory key. If omitted, all keys are returned.",
            }
        },
        "additionalProperties": False,
    }

    def __init__(self, memory: "MemoryService") -> None:
        self._memory = memory

    async def run(self, **kwargs: Any) -> ToolResult:
        key = kwargs.get("key")
        if isinstance(key, str) and key.strip():
            value = await self._memory.get(key.strip())
            if value is None:
                return ToolResult(
                    content=f"No memory found for '{key}'.",
                    data={"key": key, "value": None},
                )
            return ToolResult(
                content=f"{key} = {value}",
                data={"key": key, "value": value},
            )
        items = await self._memory.all()
        if not items:
            return ToolResult(content="No memories stored yet.", data={"items": []})
        lines = [f"{k}: {v}" for k, v in items.items()]
        return ToolResult(content="\n".join(lines), data={"items": items})
