"""Pydantic schemas for API request/response bodies.

Kept separate from ORM models (app/models/db.py) so the API contract can
evolve independently of storage.
"""
from __future__ import annotations

import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class IngestRequest(BaseModel):
    source_type: Literal["note", "url"]
    content: str = Field(..., min_length=1, max_length=200_000)

    @field_validator("content")
    @classmethod
    def content_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("content must not be blank")
        return v.strip()


class IngestResponse(BaseModel):
    id: str
    source_type: str
    title: str
    chunk_count: int
    created_at: datetime.datetime


class ItemSummary(BaseModel):
    id: str
    source_type: str
    title: str
    url: str | None
    preview: str
    chunk_count: int
    created_at: datetime.datetime


class ItemListResponse(BaseModel):
    items: list[ItemSummary]
    total: int


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)

    @field_validator("question")
    @classmethod
    def question_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("question must not be blank")
        return v.strip()


class SourceSnippet(BaseModel):
    item_id: str
    title: str
    source_type: str
    url: str | None
    snippet: str
    similarity: float


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceSnippet]
