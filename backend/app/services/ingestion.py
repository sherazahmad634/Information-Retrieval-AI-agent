"""Document ingestion pipeline.

Parse → clean → chunk → embed → persist (vector store + document store) →
invalidate BM25 cache.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from app.core.exceptions import IngestionError
from app.core.logging import get_logger
from app.models.domain import Document
from app.repositories.document_store import DocumentStore
from app.repositories.vector_store import VectorStore
from app.services.embedder import Embedder
from app.services.parsers import ParserRegistry
from app.services.retriever import HybridRetriever
from app.utils.chunker import TextChunker
from app.utils.text import clean_text

logger = get_logger(__name__)


class IngestionService:
    """Coordinates parsing, chunking, embedding, and persistence."""

    def __init__(
        self,
        *,
        parsers: ParserRegistry,
        chunker: TextChunker,
        embedder: Embedder,
        vector_store: VectorStore,
        document_store: DocumentStore,
        retriever: HybridRetriever,
    ) -> None:
        self._parsers = parsers
        self._chunker = chunker
        self._embedder = embedder
        self._vector_store = vector_store
        self._document_store = document_store
        self._retriever = retriever

    async def ingest_bytes(
        self,
        *,
        filename: str,
        data: bytes,
        content_type: str | None = None,
        title: str | None = None,
    ) -> Document:
        """Parse and ingest a file from raw bytes."""
        parser = self._parsers.resolve(filename=filename, content_type=content_type)
        text = parser.parse(data)
        if not text.strip():
            raise IngestionError("Document is empty after parsing.")
        return await self.ingest_text(
            title=title or Path(filename).stem,
            text=text,
            source=filename,
            content_type=content_type or "application/octet-stream",
        )

    async def ingest_text(
        self,
        *,
        title: str,
        text: str,
        source: str,
        content_type: str = "text/plain",
    ) -> Document:
        """Ingest pre-parsed text."""
        cleaned = clean_text(text)
        if not cleaned:
            raise IngestionError("Text is empty after normalisation.")

        document_id = str(uuid.uuid4())
        chunks = self._chunker.chunk(document_id=document_id, text=cleaned)
        if not chunks:
            raise IngestionError("Text produced no chunks (too short).")

        embeddings = await self._embedder.embed([c.text for c in chunks])
        await self._vector_store.add(chunks, embeddings)

        doc = Document(
            id=document_id,
            title=title,
            source=source,
            content_type=content_type,
            char_count=len(cleaned),
            chunk_count=len(chunks),
        )
        await self._document_store.add(doc)
        await self._retriever.invalidate_index()
        logger.info(
            "document_ingested",
            document_id=document_id,
            title=title,
            chars=len(cleaned),
            chunks=len(chunks),
        )
        return doc

    async def delete(self, document_id: str) -> bool:
        """Remove a document and its chunks from the indexes."""
        removed_chunks = await self._vector_store.delete_by_document(document_id)
        removed_doc = await self._document_store.delete(document_id)
        if removed_chunks or removed_doc:
            await self._retriever.invalidate_index()
        logger.info(
            "document_deleted",
            document_id=document_id,
            chunks_removed=removed_chunks,
            doc_removed=removed_doc,
        )
        return removed_doc

    async def ingest_seed_corpus(self, seed_dir: str) -> list[Document]:
        """Ingest every file in ``seed_dir`` that matches a known parser."""
        path = Path(seed_dir)
        if not path.exists():
            raise IngestionError(f"Seed directory not found: {seed_dir}")

        ingested: list[Document] = []
        for file_path in sorted(path.iterdir()):
            if not file_path.is_file():
                continue
            try:
                data = file_path.read_bytes()
                doc = await self.ingest_bytes(filename=file_path.name, data=data)
                ingested.append(doc)
            except IngestionError as exc:
                logger.warning("seed_ingestion_skipped", file=file_path.name, reason=str(exc))
        return ingested
