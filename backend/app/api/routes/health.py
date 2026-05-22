"""Health & readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import ContainerDep, SettingsDep
from app.models.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, summary="Liveness probe")
async def health(container: ContainerDep, settings: SettingsDep) -> HealthResponse:
    """Return basic service health and corpus statistics."""
    doc_count = await container.document_store.count()
    chunk_count = await container.vector_store.count()
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        environment=settings.app_env,
        document_count=doc_count,
        chunk_count=chunk_count,
    )
