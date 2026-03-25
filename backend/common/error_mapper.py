"""
Maps backend exceptions to frontend error codes and HTTP status.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from botocore.exceptions import ClientError

from common.errors import AppError


@dataclass(frozen=True)
class FrontendError:
    code: str
    message: str
    status_code: int
    details: dict | None = None


_CLIENT_ERROR_MAP = {
    "AccessDeniedException": ("FORBIDDEN", 403, "Access denied"),
    "NotAuthorizedException": ("UNAUTHORIZED", 401, "Unauthorized"),
    "UnauthorizedException": ("UNAUTHORIZED", 401, "Unauthorized"),
    "UserNotFoundException": ("NOT_FOUND", 404, "Resource not found"),
    "ResourceNotFoundException": ("NOT_FOUND", 404, "Resource not found"),
    "ConditionalCheckFailedException": ("CONFLICT", 409, "Resource conflict"),
    "ValidationException": ("BAD_REQUEST", 400, "Validation failed"),
    "ThrottlingException": ("TOO_MANY_REQUESTS", 429, "Too many requests"),
    "TooManyRequestsException": ("TOO_MANY_REQUESTS", 429, "Too many requests"),
    "ServiceUnavailableException": ("SERVICE_UNAVAILABLE", 503, "Service unavailable"),
}


def map_exception(
    exc: Exception, default_message: str = "Internal server error"
) -> FrontendError:
    """
    Convert an exception into a frontend-safe error object.
    """
    if isinstance(exc, AppError):
        return FrontendError(
            code=exc.code,
            message=exc.message,
            status_code=exc.status_code,
            details=exc.details,
        )

    if isinstance(exc, json.JSONDecodeError):
        return FrontendError("BAD_REQUEST", "Invalid JSON", 400)

    if isinstance(exc, (ValueError, TypeError, KeyError)):
        return FrontendError("BAD_REQUEST", str(exc) or "Invalid request", 400)

    if isinstance(exc, ClientError):
        err = exc.response.get("Error", {})
        aws_code = err.get("Code", "ClientError")
        message = err.get("Message", default_message)
        mapped = _CLIENT_ERROR_MAP.get(aws_code)
        if mapped:
            frontend_code, status_code, fallback_msg = mapped
            return FrontendError(frontend_code, message or fallback_msg, status_code)
        return FrontendError("UPSTREAM_ERROR", message or "Upstream service error", 502)

    return FrontendError("INTERNAL_ERROR", default_message, 500)
