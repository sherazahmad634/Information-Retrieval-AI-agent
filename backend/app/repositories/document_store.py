"""SQLite-backed document metadata store.

Stores per-document metadata (title, source, timestamps, etc.) separately
from the vector store, so document-level CRUD operations stay fast and
independent of the embedding index.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

from app.models.domain import Document

_SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    source TEXT NOT NULL,
    content_type TEXT NOT NULL,
    char_count INTEGER NOT NULL,
    chunk_count INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    metadata TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at);
"""


class DocumentStore:
    """Async SQLite repository for document metadata."""

    def __init__(self, path: str) -> None:
        self._path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)

    async def init(self) -> None:
        """Create tables if they don't exist."""
        async with aiosqlite.connect(self._path) as db:
            await db.executescript(_SCHEMA)
            await db.commit()

    async def add(self, doc: Document) -> None:
        """Insert or upsert a document record."""
        async with aiosqlite.connect(self._path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO documents
                    (id, title, source, content_type, char_count, chunk_count, created_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    doc.id,
                    doc.title,
                    doc.source,
                    doc.content_type,
                    doc.char_count,
                    doc.chunk_count,
                    doc.created_at.isoformat(),
                    json.dumps(doc.metadata),
                ),
            )
            await db.commit()

    async def get(self, document_id: str) -> Document | None:
        """Return the document with ``document_id`` or ``None``."""
        async with aiosqlite.connect(self._path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM documents WHERE id = ?", (document_id,))
            row = await cursor.fetchone()
            return self._row_to_doc(row) if row else None

    async def list_all(self) -> list[Document]:
        """Return all documents ordered by newest first."""
        async with aiosqlite.connect(self._path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM documents ORDER BY created_at DESC")
            rows = await cursor.fetchall()
            return [self._row_to_doc(r) for r in rows]

    async def delete(self, document_id: str) -> bool:
        """Delete a document record. Returns ``True`` if a row was removed."""
        async with aiosqlite.connect(self._path) as db:
            cursor = await db.execute("DELETE FROM documents WHERE id = ?", (document_id,))
            await db.commit()
            return cursor.rowcount > 0

    async def count(self) -> int:
        """Return total number of documents."""
        async with aiosqlite.connect(self._path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM documents")
            row = await cursor.fetchone()
            return int(row[0]) if row else 0

    @staticmethod
    def _row_to_doc(row: aiosqlite.Row) -> Document:
        raw = row["created_at"]
        created_at = (
            datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if "Z" in raw
            else datetime.fromisoformat(raw)
        )
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        return Document(
            id=row["id"],
            title=row["title"],
            source=row["source"],
            content_type=row["content_type"],
            char_count=row["char_count"],
            chunk_count=row["chunk_count"],
            created_at=created_at,
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        )
