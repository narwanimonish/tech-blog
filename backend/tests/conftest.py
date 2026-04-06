"""
Shared pytest fixtures for backend unit tests.
Run from repo root: PYTHONPATH=backend pytest backend/tests -v
Or from backend: PYTHONPATH=. pytest tests -v
"""

# Postpone evaluation of annotations (PEP 563): allows modern hints like dict | None and forward
# references without quoting; consistent with other backend test modules.
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Ensure backend root is on path so "from common import ..." and "from core import ..." work
BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


@pytest.fixture
def mock_table():
    """A MagicMock that behaves like a DynamoDB Table (get_item, put_item, delete_item, scan)."""
    table = MagicMock()
    table.get_item.return_value = {"Item": None}
    table.scan.return_value = {"Items": [], "LastEvaluatedKey": None}
    table.put_item.return_value = {}
    table.delete_item.return_value = {}
    return table


@pytest.fixture
def mock_context():
    """Minimal Lambda context with aws_request_id."""
    ctx = MagicMock()
    ctx.aws_request_id = "test-request-id-123"
    return ctx


@pytest.fixture
def base_event():
    """Minimal API Gateway proxy event with auth context (so RBAC can pass when mocked)."""
    return {
        "httpMethod": "GET",
        "path": "/users",
        "requestContext": {
            "authorizer": {"sub": "user-123", "email": "test@example.com"},
            "path": "/users",
        },
        "pathParameters": None,
        "body": None,
    }


def api_event(method, path, path_params=None, body=None, authorizer=None):
    """Build an API Gateway proxy event for handler tests."""
    return {
        "httpMethod": method,
        "path": path,
        "requestContext": {
            "authorizer": authorizer or {"sub": "user-123", "email": "test@example.com"},
            "path": path,
        },
        "pathParameters": path_params or {},
        "body": json.dumps(body) if body is not None and isinstance(body, dict) else body,
    }
