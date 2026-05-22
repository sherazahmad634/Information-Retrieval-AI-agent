"""Embedding service abstraction.

Two implementations are bundled:

* :class:`SentenceTransformersEmbedder` — local CPU-friendly model.
* :class:`MockEmbedder` — deterministic hash-based embedder for tests.

The :class:`Embedder` Protocol exposes a tiny async surface so callers can be
written against any concrete backend.
"""

from __future__ import annotations

import asyncio
import hashlib
from collections.abc import Sequence
from typing import Protocol

from app.core.logging import get_logger

logger = get_logger(__name__)


class Embedder(Protocol):
    """Embedding-service contract."""

    @property
    def dimension(self) -> int:
        """Return the embedding vector dimensionality."""
        ...

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed a batch of strings and return one vector per input."""
        ...

    async def embed_one(self, text: str) -> list[float]:
        """Embed a single string."""
        ...


class SentenceTransformersEmbedder:
    """CPU-friendly embeddings using the sentence-transformers library."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        from sentence_transformers import SentenceTransformer

        logger.info("loading_embedding_model", model=model_name)
        self._model = SentenceTransformer(model_name)
        self._dim = int(self._model.get_sentence_embedding_dimension())

    @property
    def dimension(self) -> int:
        return self._dim

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []

        def _run() -> list[list[float]]:
            vectors = self._model.encode(
                list(texts),
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
            return [v.tolist() for v in vectors]

        return await asyncio.to_thread(_run)

    async def embed_one(self, text: str) -> list[float]:
        result = await self.embed([text])
        return result[0] if result else []


class MockEmbedder:
    """Deterministic, dependency-free embedder for tests.

    Produces a fixed-dimension vector derived from a SHA-256 hash of the input
    text. Vectors are normalised so cosine similarity behaves sensibly.
    """

    def __init__(self, dimension: int = 384) -> None:
        if dimension <= 0:
            raise ValueError("dimension must be positive")
        self._dim = dimension

    @property
    def dimension(self) -> int:
        return self._dim

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._embed_sync(t) for t in texts]

    async def embed_one(self, text: str) -> list[float]:
        return self._embed_sync(text)

    def _embed_sync(self, text: str) -> list[float]:
        seed = hashlib.sha256(text.encode("utf-8")).digest()
        raw = (seed * ((self._dim // len(seed)) + 1))[: self._dim]
        floats = [(b - 128) / 128.0 for b in raw]
        norm = sum(x * x for x in floats) ** 0.5 or 1.0
        return [x / norm for x in floats]
