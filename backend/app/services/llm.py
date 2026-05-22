"""LLM provider abstraction (direct, non-tool-using).

The tool-using agent in :mod:`app.services.agent` talks to the OpenAI
function-calling endpoint directly. The classes here expose a simpler
interface used by lightweight callers and tests that want straightforward
chat completions without the agent loop.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from typing import Protocol

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.exceptions import LLMError
from app.core.logging import get_logger
from app.models.schemas import ChatMessage

logger = get_logger(__name__)


class LLMService(Protocol):
    """Minimal LLM interface."""

    async def generate(
        self,
        messages: Sequence[ChatMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str: ...

    async def stream(
        self,
        messages: Sequence[ChatMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]: ...


# ---------------------------------------------------------------------------
# OpenAI provider
# ---------------------------------------------------------------------------


class OpenAILLMService:
    """OpenAI Chat Completions implementation (no function calling)."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gpt-4o-mini",
        temperature: float = 0.2,
        max_tokens: int = 1024,
        base_url: str | None = None,
    ) -> None:
        from openai import AsyncOpenAI

        if not api_key:
            raise LLMError("OPENAI_API_KEY is not configured.")
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._model = model
        self._default_temperature = temperature
        self._default_max_tokens = max_tokens

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type(Exception),
    )
    async def generate(
        self,
        messages: Sequence[ChatMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[m.model_dump() for m in messages],
                temperature=temperature if temperature is not None else self._default_temperature,
                max_tokens=max_tokens or self._default_max_tokens,
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            logger.error("openai_generate_failed", error=str(exc))
            raise LLMError("OpenAI completion failed.", details={"reason": str(exc)}) from exc

    async def stream(
        self,
        messages: Sequence[ChatMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        try:
            stream = await self._client.chat.completions.create(
                model=self._model,
                messages=[m.model_dump() for m in messages],
                temperature=temperature if temperature is not None else self._default_temperature,
                max_tokens=max_tokens or self._default_max_tokens,
                stream=True,
            )
            async for event in stream:
                delta = event.choices[0].delta.content if event.choices else None
                if delta:
                    yield delta
        except Exception as exc:
            logger.error("openai_stream_failed", error=str(exc))
            raise LLMError("OpenAI streaming failed.", details={"reason": str(exc)}) from exc


# ---------------------------------------------------------------------------
# Mock provider (offline / tests / demos)
# ---------------------------------------------------------------------------


class MockLLMService:
    """Deterministic mock LLM that paraphrases retrieved context."""

    async def generate(
        self,
        messages: Sequence[ChatMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        user_q = next((m.content for m in reversed(messages) if m.role == "user"), "")
        context = next((m.content for m in messages if m.role == "system"), "")
        return self._compose(user_q, context)

    async def stream(
        self,
        messages: Sequence[ChatMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        answer = await self.generate(messages)
        for token in answer.split(" "):
            yield token + " "

    @staticmethod
    def _compose(question: str, context: str) -> str:
        snippet = ""
        if context:
            for line in context.splitlines():
                stripped = line.strip()
                if stripped and not stripped.startswith("Source"):
                    snippet = stripped[:240]
                    break
        if not snippet:
            return (
                f"I do not have information in the indexed corpus that answers: '{question}'. "
                "Please ingest more documents and try again."
            )
        return (
            f"Based on the indexed documents: {snippet} "
            "[1] Additional supporting details appear in the cited sources."
        )
