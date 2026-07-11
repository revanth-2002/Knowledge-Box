"""Embedding generation.

Thin wrapper around the Gemini embeddings API. Kept behind a small
interface (embed_texts / embed_query) so the provider can be swapped
(e.g. for a local sentence-transformers model) without touching callers.
"""
from __future__ import annotations

import logging

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import Settings, get_settings
from app.core.errors import EmbeddingError

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)
settings = get_settings()


def _get_api_key(settings_obj: Settings | None = None) -> str:
    resolved_settings = settings_obj or settings
    api_key = resolved_settings.gemini_api_key
    if not api_key:
        raise EmbeddingError(
            "GEMINI_API_KEY is not configured",
            detail="Set GEMINI_API_KEY in the backend .env file",
        )
    return api_key


@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type((httpx.HTTPError,)),
)






async def _create_embeddings(
    texts: list[str],
    task_type: str = "RETRIEVAL_DOCUMENT",
) -> list[list[float]]:
    embeddings: list[list[float]] = []

    try:
        _client = genai.Client(api_key=_get_api_key())
        async with _client.aio as client:
            for text in texts:
                response = await client.models.embed_content(
                    model=settings.embedding_model,
                    contents=text,
                    config=types.EmbedContentConfig(
                        task_type=task_type,
                    ),
                )

                if not response.embeddings or not response.embeddings[0] or not response.embeddings[0].values:
                    raise EmbeddingError(
                        "Failed to generate embeddings",
                        detail="Gemini returned no embedding values",
                    )

                values = response.embeddings[0].values
                embeddings.append(values)

    except Exception as exc:
        logger.exception("Embedding API error")
        raise EmbeddingError(
            "Failed to generate embeddings",
            detail=str(exc),
        ) from exc

    return embeddings


async def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    return await _create_embeddings(texts)


async def embed_query(text: str) -> list[float]:
    result = await _create_embeddings([text], task_type="RETRIEVAL_QUERY")
    return result[0]
