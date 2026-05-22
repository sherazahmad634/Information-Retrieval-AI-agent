"""Unit tests for :mod:`app.utils.chunker`."""

from __future__ import annotations

import pytest

from app.utils.chunker import ChunkerConfig, TextChunker


def test_chunker_splits_long_text() -> None:
    chunker = TextChunker(ChunkerConfig(chunk_size=40, chunk_overlap=8))
    text = " ".join([f"This is sentence number {i}." for i in range(60)])
    chunks = chunker.chunk(document_id="doc1", text=text)

    assert len(chunks) > 1
    assert all(c.document_id == "doc1" for c in chunks)
    assert all(c.text for c in chunks)
    # Positions are sequential.
    assert [c.position for c in chunks] == list(range(len(chunks)))


def test_chunker_handles_empty_input() -> None:
    chunker = TextChunker()
    assert chunker.chunk(document_id="d", text="") == []
    assert chunker.chunk(document_id="d", text="   ") == []


def test_chunker_rejects_invalid_config() -> None:
    with pytest.raises(ValueError):
        ChunkerConfig(chunk_size=10, chunk_overlap=20)
    with pytest.raises(ValueError):
        ChunkerConfig(chunk_size=0, chunk_overlap=0)


def test_chunker_short_text_produces_single_chunk() -> None:
    chunker = TextChunker(ChunkerConfig(chunk_size=512, chunk_overlap=32))
    chunks = chunker.chunk(document_id="d", text="A short sentence. Another one.")
    assert len(chunks) == 1
    assert "short sentence" in chunks[0].text


def test_chunker_overlap_preserves_continuity() -> None:
    chunker = TextChunker(ChunkerConfig(chunk_size=20, chunk_overlap=8))
    text = " ".join([f"Sentence {i} word filler." for i in range(40)])
    chunks = chunker.chunk(document_id="d", text=text)
    assert len(chunks) >= 2
    # The end of chunk[i] should appear at the start of chunk[i+1] for at least one pair.
    overlaps = [
        any(word in chunks[i + 1].text for word in chunks[i].text.split()[-3:])
        for i in range(len(chunks) - 1)
    ]
    assert any(overlaps)
