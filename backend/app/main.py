"""FastAPI application entrypoint: wiring only, no business logic here."""
from __future__ import annotations

import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api import ingest, items, query
from app.config import get_settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging
from app.models.db import init_db

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Knowledge Inbox",
    description="Save notes/URLs and ask questions over them via RAG.",
    version="1.0.0",
) 

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_error_handlers(app)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    logger.info(
        "request completed",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    response.headers["X-Request-ID"] = request_id
    return response


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    logger.info("database initialized", extra={"stage": "startup"})


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


app.include_router(ingest.router)
app.include_router(items.router)
app.include_router(query.router)
