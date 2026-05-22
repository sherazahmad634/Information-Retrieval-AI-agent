"""Vector store abstraction with ChromaDB and in-memory implementations.

The :class:`VectorStore` Protocol pins the interface used by the retrieval
pipeline. Two implementations are provided:

* :class:`ChromaVectorStore` — persistent, production-grade.
* :class:`InMemoryVectorStore` — zero-dependency, used for unit tests and the
  ``vector_store_provider=memory`` configuration.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any, Protocol

from app.models.domain import Chunk, ScoredChunk


class VectorStore(Protocol):
    """Vector-store contract used by retrieval and ingestion services."""

    async def add(self, chunks: Sequence[Chunk], embeddings: Sequence[Sequence[float]]) -> None:
        """Persist chunks alongside their embeddings."""
        ...

    async def search(
        self, embedding: Sequence[float], top_k: int, *, filters: dict[str, Any] | None = None
    ) -> list[ScoredChunk]:
        """Return ``top_k`` chunks most similar to ``embedding``."""
        ...

    async def delete_by_document(self, document_id: str) -> int:
        """Remove all chunks belonging to ``document_id``. Returns count removed."""
        ...

    async def count(self) -> int:
        """Return the total number of vectors stored."""
        ...

    async def all_chunks(self) -> list[Chunk]:
        """Return every stored chunk — used to (re)build the BM25 index."""
        ...


# ---------------------------------------------------------------------------
# Chroma implementation
# ---------------------------------------------------------------------------


class ChromaVectorStore:
    """Persistent vector store backed by ``chromadb``'s PersistentClient."""

    def __init__(self, *, path: str, collection_name: str) -> None:
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        self._client = chromadb.PersistentClient(
            path=path,
            settings=ChromaSettings(anonymized_telemetry=False, allow_reset=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    async def add(self, chunks: Sequence[Chunk], embeddings: Sequence[Sequence[float]]) -> None:
        if not chunks:
            return
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must have equal length")
        self._collection.add(
            ids=[c.id for c in chunks],
            embeddings=[list(e) for e in embeddings],
            documents=[c.text for c in chunks],
            metadatas=[
                {
                    "document_id": c.document_id,
                    "position": c.position,
                    "start_char": c.start_char,
                    "end_char": c.end_char,
                    **{
                        k: v
                        for k, v in c.metadata.items()
                        if isinstance(v, (str, int, float, bool))
                    },
                }
                for c in chunks
            ],
        )

    async def search(
        self,
        embedding: Sequence[float],
        top_k: int,
        *,
        filters: dict[str, Any] | None = None,
    ) -> list[ScoredChunk]:
        if await self.count() == 0:
            return []
        result = self._collection.query(
            query_embeddings=[list(embedding)],
            n_results=top_k,
            where=filters or None,
        )
        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        scored: list[ScoredChunk] = []
        for cid, text, meta, dist in zip(ids, documents, metadatas, distances, strict=False):
            chunk = Chunk(
                id=cid,
                document_id=str(meta.get("document_id", "")),
                text=text,
                position=int(meta.get("position", 0)),
                start_char=int(meta.get("start_char", 0)),
                end_char=int(meta.get("end_char", 0)),
                metadata={
                    k: v
                    for k, v in meta.items()
                    if k not in {"document_id", "position", "start_char", "end_char"}
                },
            )
            score = 1.0 - float(dist) if dist is not None else 0.0
            scored.append(ScoredChunk(chunk=chunk, score=score, source="dense"))
        return scored

    async def delete_by_document(self, document_id: str) -> int:
        existing = self._collection.get(where={"document_id": document_id})
        ids = existing.get("ids", []) or []
        if not ids:
            return 0
        self._collection.delete(ids=ids)
        return len(ids)

    async def count(self) -> int:
        return int(self._collection.count())

    async def all_chunks(self) -> list[Chunk]:
        data = self._collection.get(include=["documents", "metadatas"])
        ids = data.get("ids", []) or []
        documents = data.get("documents", []) or []
        metadatas = data.get("metadatas", []) or []
        out: list[Chunk] = []
        for cid, text, meta in zip(ids, documents, metadatas, strict=False):
            out.append(
                Chunk(
                    id=cid,
                    document_id=str(meta.get("document_id", "")),
                    text=text,
                    position=int(meta.get("position", 0)),
                    start_char=int(meta.get("start_char", 0)),
                    end_char=int(meta.get("end_char", 0)),
                    metadata={},
                )
            )
        return out


# ---------------------------------------------------------------------------
# In-memory implementation (tests / mock mode)
# ---------------------------------------------------------------------------


class InMemoryVectorStore:
    """Naive in-memory store using cosine similarity. Intended for tests."""

    def __init__(self) -> None:
        self._chunks: dict[str, Chunk] = {}
        self._embeddings: dict[str, list[float]] = {}

    async def add(self, chunks: Sequence[Chunk], embeddings: Sequence[Sequence[float]]) -> None:
        for c, e in zip(chunks, embeddings, strict=True):
            self._chunks[c.id] = c
            self._embeddings[c.id] = list(e)

    async def search(
        self,
        embedding: Sequence[float],
        top_k: int,
        *,
        filters: dict[str, Any] | None = None,
    ) -> list[ScoredChunk]:
        if not self._embeddings:
            return []
        q = list(embedding)
        scores: list[tuple[float, str]] = []
        for cid, vec in self._embeddings.items():
            chunk = self._chunks[cid]
            if filters and not self._match_filters(chunk, filters):
                continue
            scores.append((self._cosine(q, vec), cid))
        scores.sort(key=lambda x: x[0], reverse=True)
        return [
            ScoredChunk(chunk=self._chunks[cid], score=s, source="dense")
            for s, cid in scores[:top_k]
        ]

    async def delete_by_document(self, document_id: str) -> int:
        to_remove = [cid for cid, c in self._chunks.items() if c.document_id == document_id]
        for cid in to_remove:
            self._chunks.pop(cid, None)
            self._embeddings.pop(cid, None)
        return len(to_remove)

    async def count(self) -> int:
        return len(self._chunks)

    async def all_chunks(self) -> list[Chunk]:
        return list(self._chunks.values())

    @staticmethod
    def _match_filters(chunk: Chunk, filters: dict[str, Any]) -> bool:
        for k, v in filters.items():
            if k == "document_id" and chunk.document_id != v:
                return False
            if k in chunk.metadata and chunk.metadata[k] != v:
                return False
        return True

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        if not a or not b:
            return 0.0
        dot = sum(x * y for x, y in zip(a, b, strict=False))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)
