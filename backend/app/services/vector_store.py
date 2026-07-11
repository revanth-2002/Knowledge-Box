"""Vector storage and similarity search.

Storage: embeddings live in SQLite (app/models/db.py, Chunk.embedding_json).
Search: brute-force cosine similarity computed in-process with numpy.

Why this is fine here: single user, expected corpus is small (personal
notes/URLs), so an O(n) scan over all chunks is fast (sub-10ms for a few
thousand vectors) and requires zero extra infrastructure.

What breaks at scale: this becomes the bottleneck once chunk count grows
past ~10^5 -- linear scan latency grows with corpus size, and everything
is loaded into memory per-query. Production fix: a proper ANN vector
index (pgvector w/ HNSW, Qdrant, or similar) with persistent indexing
instead of recompute-per-query.
"""
from __future__ import annotations

import numpy as np
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.db import Chunk, Item

settings = get_settings()


def cosine_similarity_batch(query: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    query_norm = query / (np.linalg.norm(query) + 1e-10)
    matrix_norms = matrix / (np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-10)
    return matrix_norms @ query_norm


def top_k_similar_chunks(
    db: Session, query_embedding: list[float], k: int | None = None
) -> list[tuple[Chunk, Item, float]]:
    """Return the top-k (chunk, item, similarity) tuples across all stored chunks."""
    k = k or settings.top_k_chunks

    chunks: list[Chunk] = (
        db.query(Chunk).limit(settings.max_similarity_candidates).all()
    )
    if not chunks:
        return []

    query_vec = np.array(query_embedding, dtype=np.float32)
    embedding_matrix = np.array([c.embedding() for c in chunks], dtype=np.float32)
    similarities = cosine_similarity_batch(query_vec, embedding_matrix)

    ranked_indices = np.argsort(-similarities)[:k]

    results: list[tuple[Chunk, Item, float]] = []
    for idx in ranked_indices:
        chunk = chunks[int(idx)]
        results.append((chunk, chunk.item, float(similarities[int(idx)])))
    return results
