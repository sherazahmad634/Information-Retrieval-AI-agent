"""Agent tool system.

Tools are first-class plug-ins: each tool subclasses :class:`Tool`, declares a
JSON-schema of its parameters, and implements a single async :meth:`run`
method. The :class:`ToolRegistry` collects them into the format expected by
OpenAI-style function calling, so the agent can dispatch them transparently.
"""

from app.services.tools.base import Tool, ToolError, ToolResult
from app.services.tools.registry import ToolRegistry

__all__ = ["Tool", "ToolError", "ToolResult", "ToolRegistry"]
