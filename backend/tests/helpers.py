"""
Shared test helpers (api_event, BACKEND_ROOT). Use: from backend.tests.helpers import api_event, BACKEND_ROOT.
"""

from __future__ import annotations

import json
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent


def api_event(
    method: str,
    path: str,
    path_params: dict | None = None,
    body: dict | str | None = None,
    authorizer: dict | None = None,
) -> dict:
    """Build an API Gateway proxy event for handler tests."""
    return {
        "httpMethod": method,
        "path": path,
        "requestContext": {
            "authorizer": authorizer
            or {"sub": "user-123", "email": "test@example.com"},
            "path": path,
        },
        "pathParameters": path_params or {},
        "body": json.dumps(body)
        if body is not None and isinstance(body, dict)
        else body,
    }
