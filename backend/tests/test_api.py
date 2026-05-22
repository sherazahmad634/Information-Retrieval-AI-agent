"""End-to-end HTTP API tests."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "document_count" in body
    assert "chunk_count" in body


@pytest.mark.asyncio
async def test_tools_listing(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/tools")
    assert resp.status_code == 200
    names = [item["name"] for item in resp.json()["items"]]
    for expected in (
        "document_search",
        "document_ingest",
        "web_search",
        "calculator",
        "remember",
        "recall",
    ):
        assert expected in names


@pytest.mark.asyncio
async def test_document_lifecycle(client: AsyncClient) -> None:
    # Upload a text file
    files = {"file": ("note.txt", b"BM25 is a probabilistic ranking function.", "text/plain")}
    resp = await client.post("/api/v1/documents/upload", files=files)
    assert resp.status_code == 201
    doc_id = resp.json()["document_id"]

    # List documents
    listing = await client.get("/api/v1/documents")
    assert listing.status_code == 200
    assert any(d["id"] == doc_id for d in listing.json()["items"])

    # Search retrieves the chunk
    search = await client.post("/api/v1/search", json={"query": "BM25", "top_k": 3})
    assert search.status_code == 200
    assert search.json()["results"], "Expected at least one search hit"

    # Delete
    delete = await client.delete(f"/api/v1/documents/{doc_id}")
    assert delete.status_code == 204


@pytest.mark.asyncio
async def test_chat_endpoint(client: AsyncClient) -> None:
    files = {"file": ("rag.txt", b"RAG grounds the LLM in retrieved passages.", "text/plain")}
    await client.post("/api/v1/documents/upload", files=files)

    resp = await client.post("/api/v1/chat", json={"query": "what is RAG?", "top_k": 3})
    assert resp.status_code == 200
    body = resp.json()
    assert body["answer"]
    assert isinstance(body["citations"], list)
