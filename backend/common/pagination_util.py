"""Query-string pagination helpers for list endpoints (DynamoDB scan cursors)."""

from __future__ import annotations

import base64
import json
from decimal import Decimal

DEFAULT_PAGE_SIZE = 5
MAX_PAGE_SIZE = 100


class InvalidCursorError(ValueError):
    """Raised when nextToken cannot be decoded."""


def _json_default(value: object) -> object:
    if isinstance(value, Decimal):
        if value % 1 == 0:
            return int(value)
        return float(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def encode_cursor(last_evaluated_key: dict | None) -> str | None:
    if not last_evaluated_key:
        return None
    payload = json.dumps(last_evaluated_key, separators=(",", ":"), default=_json_default).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def decode_cursor(token: str | None) -> dict | None:
    if token is None or str(token).strip() == "":
        return None
    try:
        padding = "=" * (-len(token) % 4)
        raw = base64.urlsafe_b64decode(token + padding)
        value = json.loads(raw.decode("utf-8"))
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise InvalidCursorError("Invalid nextToken") from exc
    if not isinstance(value, dict):
        raise InvalidCursorError("Invalid nextToken")
    return value


def parse_page_size(raw_limit: str | None) -> int:
    if raw_limit is None or str(raw_limit).strip() == "":
        return DEFAULT_PAGE_SIZE
    try:
        limit = int(raw_limit)
    except (TypeError, ValueError) as exc:
        raise InvalidCursorError("limit must be a positive integer") from exc
    if limit < 1 or limit > MAX_PAGE_SIZE:
        raise InvalidCursorError(f"limit must be between 1 and {MAX_PAGE_SIZE}")
    return limit


def parse_list_params(event: dict) -> tuple[int, dict | None]:
    """Read limit and nextToken from an API Gateway proxy event."""
    params = event.get("queryStringParameters") or {}
    limit = parse_page_size(params.get("limit"))
    start_key = decode_cursor(params.get("nextToken"))
    return limit, start_key


def build_list_response(items: list, *, limit: int, last_evaluated_key: dict | None) -> dict:
    return {
        "items": items,
        "limit": limit,
        "nextToken": encode_cursor(last_evaluated_key),
    }
