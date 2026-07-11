from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.models.db import get_db
from app.models.schemas import IngestRequest, IngestResponse
from app.services.ingestion import ingest_content

logger = logging.getLogger(__name__)
router = APIRouter(tags=["ingest"])


@router.post("/ingest", response_model=IngestResponse, status_code=201)
async def ingest(payload: IngestRequest, db: Session = Depends(get_db)) -> IngestResponse:
    """Save a note or URL: fetch (if URL), chunk, embed, and persist it."""
    logger.info(
        "ingest request received",
        extra={"stage": "ingest_start", "source_type": payload.source_type},
    )
    item = await ingest_content(db, payload.source_type, payload.content)
    return IngestResponse(
        id=item.id,
        source_type=item.source_type.value,
        title=item.title,
        chunk_count=len(item.chunks),
        created_at=item.created_at,
    )
