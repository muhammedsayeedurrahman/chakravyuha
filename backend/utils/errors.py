"""Centralized error handling for Chakravyuha API."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("chakravyuha")


class ApiError(Exception):
    """Structured API error with status code and detail."""

    def __init__(
        self,
        status_code: int = 500,
        detail: str = "Internal server error",
        error_type: str = "server_error",
        extra: dict[str, Any] | None = None,
    ) -> None:
        self.status_code = status_code
        self.detail = detail
        self.error_type = error_type
        self.extra = extra or {}
        super().__init__(detail)


async def api_error_handler(_request: Request, exc: ApiError) -> JSONResponse:
    """FastAPI exception handler for ApiError."""
    logger.error(
        "API error: %s (type=%s, status=%d)",
        exc.detail,
        exc.error_type,
        exc.status_code,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "error_type": exc.error_type,
            **exc.extra,
        },
    )


async def generic_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler for unhandled exceptions."""
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "An unexpected error occurred. Please try again.",
            "error_type": "internal_error",
        },
    )
