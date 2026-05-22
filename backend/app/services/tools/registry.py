"""Registry of agent tools."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from app.core.logging import get_logger
from app.services.tools.base import Tool, ToolError, ToolResult

logger = get_logger(__name__)


class ToolRegistry:
    """Lookup table of named tools.

    Open for extension (add new tools via :meth:`register`), closed for
    modification — the agent never has to learn about specific tools.
    """

    def __init__(self, tools: Iterable[Tool] = ()) -> None:
        self._tools: dict[str, Tool] = {}
        for tool in tools:
            self.register(tool)

    def register(self, tool: Tool) -> None:
        """Add a tool to the registry. Raises if the name is duplicated."""
        if tool.name in self._tools:
            raise ValueError(f"Duplicate tool name: {tool.name}")
        self._tools[tool.name] = tool
        logger.info("tool_registered", name=tool.name)

    def get(self, name: str) -> Tool | None:
        """Return the tool with ``name`` or ``None`` if not present."""
        return self._tools.get(name)

    def names(self) -> list[str]:
        """Return all registered tool names sorted alphabetically."""
        return sorted(self._tools)

    def openai_schemas(self) -> list[dict[str, Any]]:
        """Return all tools serialised as OpenAI function-calling specs."""
        return [t.to_openai_schema() for t in self._tools.values()]

    async def invoke(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        """Dispatch a tool call. Wraps :class:`ToolError` for the agent."""
        tool = self.get(name)
        if tool is None:
            raise ToolError(f"Unknown tool: {name}")
        try:
            logger.info("tool_invoked", name=name, args_keys=list(arguments))
            return await tool.run(**arguments)
        except ToolError:
            raise
        except TypeError as exc:
            raise ToolError(f"Invalid arguments for tool '{name}': {exc}") from exc
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("tool_failed", name=name)
            raise ToolError(f"Tool '{name}' failed: {exc}") from exc
