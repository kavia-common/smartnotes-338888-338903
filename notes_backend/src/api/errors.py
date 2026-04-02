from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from fastapi import Request
from fastapi.responses import JSONResponse


@dataclass(frozen=True)
class ApiError:
    """Serializable error payload."""
    code: str
    message: str
    details: Optional[Any] = None


class ApiException(Exception):
    """Typed exception for consistent API error responses."""

    def __init__(self, *, status_code: int, code: str, message: str, details: Any = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error = ApiError(code=code, message=message, details=details)


# PUBLIC_INTERFACE
async def api_exception_handler(_: Request, exc: ApiException) -> JSONResponse:
    """Convert ApiException to JSONResponse with a standard shape."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.error.code, "message": exc.error.message, "details": exc.error.details}},
    )
