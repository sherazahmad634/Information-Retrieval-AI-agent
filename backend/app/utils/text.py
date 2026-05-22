"""Text-processing helpers used across the ingestion and retrieval pipelines."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

_WHITESPACE_RE = re.compile(r"\s+")
_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def normalize_whitespace(text: str) -> str:
    """Collapse runs of whitespace into single spaces and strip."""
    return _WHITESPACE_RE.sub(" ", text).strip()


def normalize_unicode(text: str) -> str:
    """Apply NFKC normalisation to canonicalise Unicode forms."""
    return unicodedata.normalize("NFKC", text)


def clean_text(text: str) -> str:
    """Apply both unicode and whitespace normalisation."""
    return normalize_whitespace(normalize_unicode(text))


def tokenize(text: str) -> list[str]:
    """Lowercase word-level tokenisation used by the BM25 index.

    Intentionally simple — production systems should swap in a proper tokeniser.
    """
    return [m.group(0).lower() for m in _TOKEN_RE.finditer(text)]


def estimate_tokens(text: str) -> int:
    """Roughly estimate token count without loading a tokenizer.

    Uses the heuristic of ~4 characters per token, which is accurate enough for
    chunk sizing in practice. Replace with ``tiktoken`` if exact counts matter.
    """
    if not text:
        return 0
    return max(1, len(text) // 4)


def truncate_at_token_limit(text: str, max_tokens: int) -> str:
    """Truncate a string so it fits within an approximate token budget."""
    max_chars = max_tokens * 4
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0]


def join_unique(items: Iterable[str], sep: str = ", ") -> str:
    """Join an iterable preserving order and dropping duplicates."""
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return sep.join(out)
