from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.models.db import get_db
from app.models.schemas import QueryRequest, QueryResponse
from app.services.rag import answer_question

logger = logging.getLogger(__name__)
router = APIRouter(tags=["query"])


@router.post("/query", response_model=QueryResponse)
async def query(payload: QueryRequest, db: Session = Depends(get_db)) -> QueryResponse:
    """Answer a question by retrieving relevant saved chunks and asking the LLM."""
    logger.info("query received", extra={"stage": "query_start", "question": payload.question})
    result = await answer_question(db, payload.question)
    return result
