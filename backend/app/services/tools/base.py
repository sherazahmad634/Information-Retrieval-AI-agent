"""Base interfaces for the agent tool system."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


class ToolError(Exception):
    """Raised by a tool when it cannot complete its task.

    The agent loop catches this and reports the error back to the LLM so it
    can retry, choose a different tool, or apologise to the user.
    """


@dataclass(slots=True)
class ToolResult:
    """Structured tool output returned to the agent.

    ``content`` is the human-readable text the LLM will see. ``data`` is an
    optional structured payload (e.g. a list of retrieved chunks) that the API
    layer can forward to the frontend alongside the answer.
    """

    content: str
    data: dict[str, Any] = field(default_factory=dict)


class Tool(ABC):
    """Abstract agent tool.

    Concrete tools must declare:

    * ``name`` — a unique snake_case identifier the LLM will use.
    * ``description`` — a one-paragraph natural-language explanation of when
      and how to call the tool. Critical for the LLM to choose correctly.
    * ``parameters_schema`` — a JSON-schema describing the tool's inputs.
    * :meth:`run` — the async implementation.
    """

    name: str = ""
    description: str = ""
    parameters_schema: dict[str, Any] = {}

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        # `__abstractmethods__` is populated by ABCMeta and may not exist yet
        # on partially-constructed classes; treat absence as "still abstract".
        if getattr(cls, "__abstractmethods__", None):
            return
        if not cls.name:
            raise TypeError(f"{cls.__name__} must set a non-empty `name`.")
        if not cls.description:
            raise TypeError(f"{cls.__name__} must set a non-empty `description`.")

    @abstractmethod
    async def run(self, **kwargs: Any) -> ToolResult:
        """Execute the tool and return a :class:`ToolResult`."""

    def to_openai_schema(self) -> dict[str, Any]:
        """Serialise the tool as an OpenAI function-calling tool spec."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_schema
                or {"type": "object", "properties": {}, "additionalProperties": False},
            },
        }
