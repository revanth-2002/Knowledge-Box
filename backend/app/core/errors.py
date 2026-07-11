"""Domain exceptions and their mapping to HTTP responses.

Keeping exceptions here (rather than raising HTTPException deep inside
services) means services stay framework-agnostic and every error gets a
consistent JSON envelope: {"error": {"code", "message", "detail"}}.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base class for all domain errors. Not meant to be raised directly."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    code: str = "internal_error"

    def __init__(self, message: str, detail: str | None = None):
        self.message = message
        self.detail = detail
        super().__init__(message)


class ValidationError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    code = "validation_error"


class ItemNotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "item_not_found"


class FetchError(AppError):
    """Raised when a URL can't be downloaded or parsed server-side."""

    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    code = "fetch_error"


class EmbeddingError(AppError):
    """Raised when the embeddings provider fails."""

    status_code = status.HTTP_502_BAD_GATEWAY
    code = "embedding_error"


class LLMError(AppError):
    """Raised when the chat completion provider fails."""

    status_code = status.HTTP_502_BAD_GATEWAY
    code = "llm_error"


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        logger.warning(
            "request failed",
            extra={
                "path": str(request.url.path),
                "error_code": exc.code,
                "detail": exc.detail,
            },
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "detail": exc.detail,
                }
            },
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled exception", extra={"path": str(request.url.path)})
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "internal_error",
                    "message": "Something went wrong processing your request.",
                    "detail": None,
                }
            },
        )
