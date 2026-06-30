"""Decorators for repeated Lambda handler concerns."""

from __future__ import annotations

import functools
import logging
from collections.abc import Callable

from common import role_util, simple_api_util, warmup_util


def request_id(context) -> str:
    """Return AWS request id when Lambda context is available."""
    return getattr(context, "aws_request_id", "unknown")


def api_handler(logger: logging.Logger | None = None):
    """
    Decorate API Gateway Lambda handlers with warmup handling and top-level error mapping.

    Route-specific validation stays inside handlers; this only covers cross-cutting concerns
    that every API Lambda needs.
    """

    log = logger or logging.getLogger(__name__)

    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(event, context):
            if warmup_util.is_warmup_event(event):
                return warmup_util.api_warmup_response()

            try:
                return func(event, context)
            except Exception as exc:
                log.exception("%s unhandled error: %s", func.__name__, exc)
                return simple_api_util.build_error_from_exception(exc, request_id=request_id(context))

        return wrapper

    return decorator


def require_rbac(logger: logging.Logger | None = None):
    """Decorate API Gateway handlers with RBAC validation."""

    log = logger or logging.getLogger(__name__)

    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(event, context):
            allowed, message = role_util.is_user_action_valid(event)
            if not allowed:
                log.info("RBAC denied request: %s", message or "Forbidden")
                return simple_api_util.build_error_response(
                    "FORBIDDEN",
                    message or "Forbidden",
                    403,
                    request_id=request_id(context),
                )
            return func(event, context)

        return wrapper

    return decorator


def authorizer_handler(warmup_response: Callable = warmup_util.authorizer_warmup_response):
    """Decorate Lambda authorizers with scheduled warmup handling."""

    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(event, context):
            if warmup_util.is_warmup_event(event):
                return warmup_response()
            return func(event, context)

        return wrapper

    return decorator
