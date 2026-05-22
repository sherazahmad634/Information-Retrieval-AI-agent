"""Domain entities — pure data classes used by the service layer.

These are deliberately framework-agnostic so business logic can be unit-tested
without spinning up FastAPI / Pydantic validation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class Document:
    """A source document ingested into the system."""

    id: str
    title: str
    source: str
    content_type: str
    char_count: int
    chunk_count: int
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Chunk:
    """A retrievable chunk of a document."""

    id: str
    document_id: str
    text: str
    position: int
    start_char: int
    end_char: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ScoredChunk:
    """A chunk with an associated retrieval score."""

    chunk: Chunk
    score: float
    source: str = "hybrid"  # "bm25", "dense", "hybrid", "rerank"
