"""Sentence-aware sliding-window text chunker.

The chunker first splits the input into sentences using a lightweight regex,
then greedily packs sentences into windows of approximately ``chunk_size``
tokens with ``chunk_overlap`` tokens of overlap between consecutive chunks.
Sentence boundaries are respected wherever possible.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

from app.models.domain import Chunk
from app.utils.text import clean_text, estimate_tokens

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'(\[])|(?<=\n)\n+")


@dataclass(slots=True, frozen=True)
class ChunkerConfig:
    """Configuration for :class:`TextChunker`."""

    chunk_size: int = 512
    chunk_overlap: int = 64
    min_chunk_chars: int = 64

    def __post_init__(self) -> None:
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        if self.chunk_size <= 0:
            raise ValueError("chunk_size must be positive")


class TextChunker:
    """Split documents into overlapping, sentence-aware chunks."""

    def __init__(self, config: ChunkerConfig | None = None) -> None:
        self.config = config or ChunkerConfig()

    def split_sentences(self, text: str) -> list[str]:
        """Split ``text`` into sentences using a regex heuristic."""
        cleaned = clean_text(text)
        if not cleaned:
            return []
        sentences = _SENTENCE_SPLIT_RE.split(cleaned)
        return [s.strip() for s in sentences if s.strip()]

    def chunk(self, *, document_id: str, text: str) -> list[Chunk]:
        """Produce chunks for the given ``document_id``/``text``.

        Returns an empty list when ``text`` is empty or shorter than
        ``min_chunk_chars``.
        """
        sentences = self.split_sentences(text)
        if not sentences:
            return []

        chunks: list[Chunk] = []
        cursor = 0  # character offset in `text`
        position = 0  # ordinal chunk index
        buffer: list[str] = []
        buffer_tokens = 0
        overlap_buffer: list[str] = []

        def flush() -> None:
            nonlocal buffer, buffer_tokens, position, cursor, overlap_buffer
            if not buffer:
                return
            chunk_text = " ".join(buffer).strip()
            if len(chunk_text) < self.config.min_chunk_chars and chunks:
                last = chunks[-1]
                merged = (last.text + " " + chunk_text).strip()
                chunks[-1] = Chunk(
                    id=last.id,
                    document_id=last.document_id,
                    text=merged,
                    position=last.position,
                    start_char=last.start_char,
                    end_char=last.end_char + len(chunk_text) + 1,
                    metadata=last.metadata,
                )
            else:
                start = cursor
                end = cursor + len(chunk_text)
                chunks.append(
                    Chunk(
                        id=str(uuid.uuid4()),
                        document_id=document_id,
                        text=chunk_text,
                        position=position,
                        start_char=start,
                        end_char=end,
                        metadata={},
                    )
                )
                position += 1
                cursor = end + 1

            overlap_buffer = self._build_overlap(buffer)
            buffer = list(overlap_buffer)
            buffer_tokens = sum(estimate_tokens(s) for s in buffer)

        for sentence in sentences:
            sent_tokens = estimate_tokens(sentence)
            if sent_tokens > self.config.chunk_size:
                flush()
                for piece in self._hard_split(sentence):
                    buffer = [piece]
                    buffer_tokens = estimate_tokens(piece)
                    flush()
                continue

            if buffer_tokens + sent_tokens > self.config.chunk_size and buffer:
                flush()
            buffer.append(sentence)
            buffer_tokens += sent_tokens

        flush()
        return chunks

    def _build_overlap(self, buffer: list[str]) -> list[str]:
        """Return tail sentences whose combined size matches ``chunk_overlap``."""
        overlap_tokens = 0
        result: list[str] = []
        for sentence in reversed(buffer):
            t = estimate_tokens(sentence)
            if overlap_tokens + t > self.config.chunk_overlap:
                break
            result.insert(0, sentence)
            overlap_tokens += t
        return result

    def _hard_split(self, sentence: str) -> list[str]:
        """Force-split overly-long sentences on a character budget."""
        max_chars = self.config.chunk_size * 4
        return [sentence[i : i + max_chars] for i in range(0, len(sentence), max_chars)]
