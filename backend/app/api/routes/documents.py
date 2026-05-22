"""Document management endpoints (upload, list, delete, seed)."""

from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile, status

from app.api.deps import DocumentStoreDep, IngestionDep, SettingsDep
from app.core.exceptions import IngestionError
from app.models.schemas import (
    BulkIngestResponse,
    DocumentList,
    DocumentSummary,
    IngestResponse,
)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=DocumentList, summary="List all indexed documents")
async def list_documents(store: DocumentStoreDep) -> DocumentList:
    docs = await store.list_all()
    items = [DocumentSummary.model_validate(d) for d in docs]
    return DocumentList(items=items, total=len(items))


@router.post(
    "/upload",
    response_model=IngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and ingest a single file",
)
async def upload_document(
    ingestion: IngestionDep,
    settings: SettingsDep,
    file: UploadFile = File(..., description="The document file to ingest"),
    title: str | None = Form(default=None, description="Optional override title"),
) -> IngestResponse:
    """Ingest a single uploaded file.

    Supported formats: ``.txt``, ``.md``, ``.html``, ``.pdf``, ``.docx``.
    """
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    data = await file.read()
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds {settings.max_upload_size_mb} MB limit.",
        )
    if not file.filename:
        raise HTTPException(status_code=400, detail="filename missing")

    try:
        doc = await ingestion.ingest_bytes(
            filename=file.filename,
            data=data,
            content_type=file.content_type,
            title=title,
        )
    except IngestionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    return IngestResponse(
        document_id=doc.id,
        title=doc.title,
        chunks_created=doc.chunk_count,
        char_count=doc.char_count,
    )


@router.post(
    "/ingest-seed",
    response_model=BulkIngestResponse,
    summary="Ingest the bundled seed corpus",
)
async def ingest_seed(ingestion: IngestionDep, settings: SettingsDep) -> BulkIngestResponse:
    """Ingest every document in ``data/seed`` (idempotent — duplicates are appended)."""
    docs = await ingestion.ingest_seed_corpus(settings.seed_corpus_path)
    return BulkIngestResponse(
        documents=[
            IngestResponse(
                document_id=d.id,
                title=d.title,
                chunks_created=d.chunk_count,
                char_count=d.char_count,
            )
            for d in docs
        ],
        total_chunks=sum(d.chunk_count for d in docs),
    )


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Delete a document and its chunks",
)
async def delete_document(document_id: str, ingestion: IngestionDep) -> Response:
    removed = await ingestion.delete(document_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Document not found.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
