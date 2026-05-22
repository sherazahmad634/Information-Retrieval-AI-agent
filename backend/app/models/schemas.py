"""Pydantic request/response schemas for the HTTP API."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    """Liveness/readiness probe response."""

    status: Literal["ok"] = "ok"
    version: str
    environment: str
    document_count: int
    chunk_count: int


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------


class DocumentSummary(BaseModel):
    """Lightweight metadata record for a single document."""

    id: str
    title: str
    source: str
    content_type: str
    char_count: int
    chunk_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentList(BaseModel):
    """Paginated list of documents."""

    items: list[DocumentSummary]
    total: int


class IngestResponse(BaseModel):
    """Response returned after a successful ingestion call."""

    document_id: str
    title: str
    chunks_created: int
    char_count: int


class BulkIngestResponse(BaseModel):
    """Response returned after ingesting multiple documents at once."""

    documents: list[IngestResponse]
    total_chunks: int


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


class SearchRequest(BaseModel):
    """Request payload for the hybrid search endpoint."""

    query: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=50)
    use_reranker: bool = True
    filters: dict[str, str] | None = None


class CitationChunk(BaseModel):
    """A retrieved chunk returned to the client."""

    chunk_id: str
    document_id: str
    document_title: str
    text: str
    score: float
    source: str
    position: int


class SearchResponse(BaseModel):
    """Hybrid-search response."""

    query: str
    results: list[CitationChunk]
    elapsed_ms: float


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------


class ChatMessage(BaseModel):
    """A single chat message in a conversation history."""

    role: Literal["user", "assistant", "system"]
    content: str


class ChatRequest(BaseModel):
    """Request payload for the agentic Q&A endpoint."""

    query: str = Field(..., min_length=1, max_length=4000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=20)
    top_k: int = Field(default=5, ge=1, le=20)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    stream: bool = False


class ChatResponse(BaseModel):
    """Agentic chat response with grounded answer and citations."""

    answer: str
    citations: list[CitationChunk]
    elapsed_ms: float
    tokens_used: int | None = None


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ErrorResponse(BaseModel):
    """Uniform error payload."""

    code: str
    message: str
    details: dict[str, object] | None = None
    request_id: str | None = None
