"""Agentic chat endpoints (sync + streaming)."""

from __future__ import annotations

import json
from typing import AsyncIterator

from fastapi import APIRouter, Header
from sse_starlette.sse import EventSourceResponse

from app.api.deps import AgentDep
from app.models.schemas import ChatRequest, ChatResponse, CitationChunk

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse, summary="Agentic Q&A (non-streaming)")
async def chat(
    request: ChatRequest,
    agent: AgentDep,
    session_id: str | None = Header(default=None, alias="X-Session-ID"),
) -> ChatResponse:
    """Run one agentic turn and return the assembled answer with citations."""
    response = await agent.chat(
        query=request.query,
        session_id=session_id,
        history=request.history,
        temperature=request.temperature,
    )
    return ChatResponse(
        answer=response.answer,
        citations=response.citations,
        elapsed_ms=response.elapsed_ms,
    )


@router.post("/stream", summary="Agentic Q&A (Server-Sent Events stream)")
async def chat_stream(
    request: ChatRequest,
    agent: AgentDep,
    session_id: str | None = Header(default=None, alias="X-Session-ID"),
) -> EventSourceResponse:
    """Stream agent trace, citations, and tokens via SSE."""

    async def event_generator() -> AsyncIterator[dict[str, str]]:
        async for event in agent.stream(
            query=request.query,
            session_id=session_id,
            history=request.history,
            temperature=request.temperature,
        ):
            yield {"event": event["event"], "data": json.dumps(_serialise(event["data"]))}

    return EventSourceResponse(event_generator())


def _serialise(payload: object) -> object:
    """Best-effort JSON-serialisation for citation lists."""
    if isinstance(payload, list):
        return [_serialise(p) for p in payload]
    if isinstance(payload, CitationChunk):
        return payload.model_dump()
    return payload
