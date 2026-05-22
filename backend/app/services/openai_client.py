"""Factory for the OpenAI-compatible chat client.

The assignment requires the system to be runnable with an "OpenAI-format API
key". By default we instantiate the official ``AsyncOpenAI`` client; if
``OPENAI_BASE_URL`` is set the client transparently talks to any compatible
endpoint (Azure, Ollama, llama.cpp server, local proxies, etc.).
"""

from __future__ import annotations

import os
from typing import Any

from app.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def build_openai_client(settings: Settings) -> Any:
    """Build and return an :class:`openai.AsyncOpenAI` instance.

    Raises :class:`ValueError` if no API key is configured and the mock LLM
    is not enabled.
    """
    if settings.use_mock_llm:
        return None
    from openai import AsyncOpenAI

    if not settings.openai_api_key:
        raise ValueError(
            "OPENAI_API_KEY is not configured. Set it in .env or enable MOCK_LLM=true."
        )

    # `.env` is read into pydantic-settings, not os.environ, so prefer the
    # Settings field. Fall back to shell env for backwards compatibility.
    base_url = settings.openai_base_url or os.environ.get("OPENAI_BASE_URL") or None
    logger.info(
        "openai_client_built",
        base_url=base_url or "https://api.openai.com/v1",
        model=settings.llm_model,
    )
    return AsyncOpenAI(api_key=settings.openai_api_key, base_url=base_url)
