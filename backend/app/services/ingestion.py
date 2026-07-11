"""Ingestion orchestration: turn raw input into a stored Item + Chunks."""
from __future__ import annotations

import json
import logging

from sqlalchemy.orm import Session

from app.core.errors import ValidationError
from app.models.db import Item, Chunk, SourceType
from app.services import chunking, embeddings
from app.services.fetcher import fetch_url_content

logger = logging.getLogger(__name__)


def _make_title_from_note(content: str) -> str:
    first_line = content.strip().splitlines()[0]
    return (first_line[:80] + "...") if len(first_line) > 80 else first_line


async def ingest_content(db: Session, source_type: str, content: str) -> Item:
    """Validate, fetch (if URL), chunk, embed, and persist an item.

    Raises ValidationError / FetchError / EmbeddingError on failure; the
    caller (API layer) maps these to HTTP responses.
    """
    if source_type == "url":
        title, extracted_text = await fetch_url_content(content)
        item = Item(source_type=SourceType.url, title=title, raw_content=extracted_text, url=content)
    elif source_type == "note":
        title = _make_title_from_note(content)
        item = Item(source_type=SourceType.note, title=title, raw_content=content, url=None)
    else:
        raise ValidationError(f"Unsupported source_type: {source_type}")

    chunk_results = chunking.chunk_text(item.raw_content)
    if not chunk_results:
        raise ValidationError("Content produced no chunks (empty after processing)")

    logger.info(
        "chunked content",
        extra={"stage": "chunk", "chunk_count": len(chunk_results), "source_type": source_type},
    )

    vectors = await embeddings.embed_texts([c.text for c in chunk_results])

    logger.info(
        "generated embeddings", extra={"stage": "embed", "vector_count": len(vectors)}
    )

    for chunk_result, vector in zip(chunk_results, vectors):
        item.chunks.append(
            Chunk(
                chunk_index=chunk_result.index,
                chunk_text=chunk_result.text,
                token_count=chunk_result.token_count,
                embedding_json=json.dumps(vector),
            )
        )

    db.add(item)
    db.commit()
    db.refresh(item)

    logger.info(
        "item persisted",
        extra={"stage": "persist", "item_id": item.id, "chunk_count": len(item.chunks)},
    )
    return item
