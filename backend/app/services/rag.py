"""RAG pipeline: embed question -> retrieve top chunks -> synthesize a
cited answer with the LLM.
"""
from __future__ import annotations

import logging

import httpx
from sqlalchemy.orm import Session

from google import genai
from google.genai import types
from app.config import Settings, get_settings
from app.core.errors import LLMError
from app.models.schemas import QueryResponse, SourceSnippet
from app.services import embeddings
from app.services.vector_store import top_k_similar_chunks

logger = logging.getLogger(__name__)
settings = get_settings()

_SYSTEM_PROMPT = (
    "You are a careful research assistant answering questions using ONLY the "
    "provided context excerpts from the user's saved notes and pages. "
    "Rules:\n"
    "1. Answer using only information present in the context below.\n"
    "2. If the context does not contain enough information to answer, say so "
    "plainly instead of guessing.\n"
    "3. When you state a fact drawn from a specific excerpt, reference it "
    "inline as [1], [2], etc. matching the excerpt numbers given.\n"
    "4. Be concise and direct."
)


def _get_api_key(settings_obj: Settings | None = None) -> str:
    resolved_settings = settings_obj or settings
    api_key = resolved_settings.gemini_api_key 
    if not api_key:
        raise LLMError(
            "GEMINI_API_KEY is not configured",
            detail="Set GEMINI_API_KEY in the backend .env file",
        )
    return api_key


def _build_context_block(chunks_with_items) -> str:
    lines = []
    for i, (chunk, item, _score) in enumerate(chunks_with_items, start=1):
        lines.append(f"[{i}] Source: {item.title}\n{chunk.chunk_text}")
    return "\n\n".join(lines)







async def _generate_answer(prompt: str) -> str:
    try:
        _client = genai.Client(api_key=_get_api_key())
        async with _client.aio as client:
            response = await client.models.generate_content(
                model=settings.chat_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=_SYSTEM_PROMPT,
                    temperature=0.2,
                ),
            )

        if not response.text:
            raise LLMError(
                "Failed to generate an answer",
                detail="Gemini returned an empty response",
            )

        return response.text

    except Exception as exc:
        logger.exception("Gemini generate_content failed")
        raise LLMError(
            "Failed to generate an answer",
            detail=str(exc),
        ) from exc


async def answer_question(db: Session, question: str) -> QueryResponse:
    query_vector = await embeddings.embed_query(question)

    logger.info("retrieval query embedded", extra={"stage": "retrieve"})

    top_chunks = top_k_similar_chunks(db, query_vector)

    if not top_chunks:
        return QueryResponse(
            answer="You don't have any saved content yet, so I can't answer that. Add a note or URL first.",
            sources=[],
        )

    context_block = _build_context_block(top_chunks)
    user_prompt = f"Context excerpts:\n\n{context_block}\n\nQuestion: {question}"

    try:
        answer_text = await _generate_answer(user_prompt)
    except (httpx.HTTPError, ValueError) as exc:
        logger.error("LLM completion error", extra={"error": str(exc)})
        raise LLMError("Failed to generate an answer", detail=str(exc)) from exc

    logger.info("answer generated", extra={"stage": "generate", "source_count": len(top_chunks)})

    sources = [
        SourceSnippet(
            item_id=item.id,
            title=item.title,
            source_type=item.source_type.value,
            url=item.url,
            snippet=chunk.chunk_text[:300],
            similarity=round(score, 4),
        )
        for chunk, item, score in top_chunks
    ]

    return QueryResponse(answer=answer_text, sources=sources)
