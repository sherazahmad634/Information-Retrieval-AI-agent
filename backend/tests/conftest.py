"""Pytest fixtures and shared test infrastructure.

All tests run with MOCK_LLM=true and an in-memory vector store so the suite
needs no network access and no model downloads. A fresh tempdir-backed
SQLite store is created per test, then torn down by the tempdir fixture.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import AsyncIterator
from pathlib import Path

# Force test-friendly configuration *before* any app module imports.
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("MOCK_LLM", "true")
os.environ.setdefault("LLM_PROVIDER", "mock")
os.environ.setdefault("EMBEDDING_PROVIDER", "mock")
os.environ.setdefault("VECTOR_STORE_PROVIDER", "memory")
os.environ.setdefault("RERANKER_ENABLED", "false")

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.api.deps import AppContainer  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest.fixture
def tmp_data_dir(monkeypatch: pytest.MonkeyPatch) -> Path:
    """Per-test temp dir, propagated through environment vars to the app."""
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setenv("VECTOR_STORE_PATH", str(Path(tmp) / "chroma"))
        monkeypatch.setenv("DOCUMENT_STORE_PATH", str(Path(tmp) / "documents.db"))
        monkeypatch.setenv("SEED_CORPUS_PATH", str(Path(tmp) / "seed"))
        # Clear the cached settings singleton so the new env values are picked up.
        get_settings.cache_clear()  # type: ignore[attr-defined]
        yield Path(tmp)
        get_settings.cache_clear()  # type: ignore[attr-defined]


@pytest_asyncio.fixture
async def container(tmp_data_dir: Path) -> AsyncIterator[AppContainer]:
    """Build a fully wired container against the temp directory."""
    settings = get_settings()
    container = AppContainer(settings)
    await container.startup()
    yield container


@pytest_asyncio.fixture
async def client(tmp_data_dir: Path) -> AsyncIterator[AsyncClient]:
    """ASGI HTTP client for end-to-end API tests."""
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Trigger lifespan startup
        async with app.router.lifespan_context(app):
            yield ac
