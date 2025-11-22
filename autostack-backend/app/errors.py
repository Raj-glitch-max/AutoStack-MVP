from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette import status

from .schemas import ErrorDetails, ErrorResponse


class ApiError(Exception):
    def __init__(self, code: str, message: str, status_code: int, details: dict[str, Any] | None = None) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


def error_response(code: str, message: str, status_code: int, details: dict[str, Any] | None = None) -> JSONResponse:
    payload = ErrorResponse(
        error=ErrorDetails(
            code=code,
            message=message,
            status_code=status_code,
            details=details or {},
        )
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump(by_alias=True))


async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    return error_response(exc.code, exc.message, exc.status_code, exc.details)


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return error_response(
        "VALIDATION_ERROR",
        "Request validation failed",
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        {"errors": exc.errors()},
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    code_map = {
        status.HTTP_401_UNAUTHORIZED: "UNAUTHORIZED",
        status.HTTP_403_FORBIDDEN: "FORBIDDEN",
        status.HTTP_404_NOT_FOUND: "NOT_FOUND",
    }
    code = code_map.get(exc.status_code, "INTERNAL_SERVER_ERROR")
    message = exc.detail if isinstance(exc.detail, str) else code.replace("_", " ").title()
    return error_response(code, message, exc.status_code, {})


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return error_response(
        "INTERNAL_SERVER_ERROR",
        "Internal server error",
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        {},
    )
