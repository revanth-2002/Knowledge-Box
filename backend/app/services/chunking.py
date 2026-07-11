"""Chunking strategy.

Approach: fixed-size sliding window over whitespace-delimited "words",
approximated as tokens (roughly 0.75 words/token in English -- we chunk
on words for simplicity and treat the size settings as word counts,
which is intentional and documented in the README's tradeoffs section).

Chosen over semantic/paragraph-based chunking because:
- It's predictable and easy to reason about/debug (fixed chunk sizes).
- It handles arbitrary input (notes with no paragraph structure, raw
  scraped HTML text) without needing a second model call to segment.
- Overlap preserves context that would otherwise be split at a chunk
  boundary, at the cost of some duplicate content in the index.

Tradeoff: it can split mid-sentence/mid-idea, hurting retrieval
precision for content with strong internal structure. A production
version would chunk on paragraph/heading boundaries first, falling back
to fixed-size windows only for oversized paragraphs.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.config import get_settings

settings = get_settings()


@dataclass
class ChunkResult:
    text: str
    index: int
    token_count: int


def chunk_text(
    text: str,
    chunk_size: int | None = None,
    overlap: int | None = None,
) -> list[ChunkResult]:
    """Split text into overlapping fixed-size chunks (word-based approximation of tokens)."""
    chunk_size = chunk_size or settings.chunk_size_tokens
    overlap = overlap if overlap is not None else settings.chunk_overlap_tokens

    if chunk_size <= overlap:
        raise ValueError("chunk_size must be greater than overlap")

    words = text.split()
    if not words:
        return []

    chunks: list[ChunkResult] = []
    step = chunk_size - overlap
    index = 0
    start = 0
    while start < len(words):
        window = words[start : start + chunk_size]
        chunk_str = " ".join(window)
        chunks.append(ChunkResult(text=chunk_str, index=index, token_count=len(window)))
        index += 1
        if start + chunk_size >= len(words):
            break
        start += step

    return chunks
