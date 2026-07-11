from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.db import Item, get_db
from app.models.schemas import ItemListResponse, ItemSummary

logger = logging.getLogger(__name__)
router = APIRouter(tags=["items"])


def _preview(raw_content: str, length: int = 200) -> str:
    text = raw_content.strip().replace("\n", " ")
    return (text[:length] + "...") if len(text) > length else text


@router.get("/items", response_model=ItemListResponse)
async def list_items(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> ItemListResponse:
    """List saved items, newest first, with a short content preview."""
    total = db.query(func.count(Item.id)).scalar() or 0
    items = (
        db.query(Item)
        .order_by(Item.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    summaries = [
        ItemSummary(
            id=item.id,
            source_type=item.source_type.value,
            title=item.title,
            url=item.url,
            preview=_preview(item.raw_content),
            chunk_count=len(item.chunks),
            created_at=item.created_at,
        )
        for item in items
    ]

    logger.info("items listed", extra={"stage": "list_items", "count": len(summaries)})
    return ItemListResponse(items=summaries, total=total)
