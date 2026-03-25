"""
Unit tests for the users Lambda handler (API behaviour with mocked SERVICE and RBAC).
Handler is loaded from webservice/users/runtime/users.py; path is set so runtime.users is importable.
"""

from __future__ import annotations

import json
import sys
from unittest.mock import MagicMock, patch

import pytest

from backend.tests.helpers import BACKEND_ROOT, api_event

# Make the users handler importable (runtime.users)
_USERS_HANDLER_DIR = BACKEND_ROOT / "webservice" / "users"
if str(_USERS_HANDLER_DIR) not in sys.path:
    sys.path.insert(0, str(_USERS_HANDLER_DIR))

import runtime.users as users_module  # noqa: E402
from runtime.users import lambda_handler as users_lambda_handler  # noqa: E402


@pytest.fixture
def mock_service():
    """Mock UsersService for handler tests; set .list_users.return_value, .get_user.return_value, etc."""
    return MagicMock()


def test_get_users_list_returns_200_and_items(mock_context, mock_service):
    mock_service.list_users.return_value = [{"userId": "u1", "email": "a@b.com"}]
    event = api_event("GET", "/users")
    with patch.object(
        users_module.role_util, "is_user_action_valid", return_value=(True, "")
    ):
        with patch("runtime.users.SERVICE", mock_service):
            resp = users_lambda_handler(event, mock_context)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert "items" in body
    assert len(body["items"]) == 1
    assert body["items"][0]["userId"] == "u1"


def test_get_user_by_id_returns_200_when_found(mock_context, mock_service):
    mock_service.get_user.return_value = {
        "userId": "u1",
        "email": "a@b.com",
        "name": "Alice",
    }
    event = api_event("GET", "/users/u1", path_params={"userId": "u1"})
    event["path"] = "/users/u1"
    with patch.object(
        users_module.role_util, "is_user_action_valid", return_value=(True, "")
    ):
        with patch("runtime.users.SERVICE", mock_service):
            resp = users_lambda_handler(event, mock_context)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["userId"] == "u1"
    assert body["email"] == "a@b.com"


def test_get_user_by_id_returns_404_when_not_found(mock_context, mock_service):
    mock_service.get_user.return_value = None
    event = api_event("GET", "/users/u1", path_params={"userId": "u1"})
    event["path"] = "/users/u1"
    with patch.object(
        users_module.role_util, "is_user_action_valid", return_value=(True, "")
    ):
        with patch("runtime.users.SERVICE", mock_service):
            resp = users_lambda_handler(event, mock_context)
    assert resp["statusCode"] == 404
    body = json.loads(resp["body"])
    assert body.get("errorCode") == "NOT_FOUND"
    assert "requestId" in body


def test_put_user_returns_200_and_updated_user(mock_context, mock_service):
    mock_service.update_user.return_value = {
        "userId": "u1",
        "email": "new@b.com",
        "name": "Alice",
    }
    event = api_event(
        "PUT",
        "/users/u1",
        path_params={"userId": "u1"},
        body={"email": "new@b.com", "name": "Alice"},
    )
    event["path"] = "/users/u1"
    with patch.object(
        users_module.role_util, "is_user_action_valid", return_value=(True, "")
    ):
        with patch("runtime.users.SERVICE", mock_service):
            resp = users_lambda_handler(event, mock_context)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["email"] == "new@b.com"
    mock_service.update_user.assert_called_once_with(
        "u1", {"email": "new@b.com", "name": "Alice"}
    )


def test_put_user_returns_400_when_body_missing(mock_context, mock_service):
    event = api_event("PUT", "/users/u1", path_params={"userId": "u1"}, body=None)
    event["body"] = None
    event["path"] = "/users/u1"
    with patch.object(
        users_module.role_util, "is_user_action_valid", return_value=(True, "")
    ):
        with patch("runtime.users.SERVICE", mock_service):
            resp = users_lambda_handler(event, mock_context)
    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert body.get("errorCode") == "BAD_REQUEST"


def test_delete_user_returns_200(mock_context, mock_service):
    event = api_event("DELETE", "/users/u1", path_params={"userId": "u1"})
    event["path"] = "/users/u1"
    with patch.object(
        users_module.role_util, "is_user_action_valid", return_value=(True, "")
    ):
        with patch("runtime.users.SERVICE", mock_service):
            resp = users_lambda_handler(event, mock_context)
    assert resp["statusCode"] == 200
    mock_service.delete_user.assert_called_once_with("u1")


def test_rbac_denied_returns_403(mock_context, mock_service):
    event = api_event("GET", "/users")
    with patch.object(
        users_module.role_util,
        "is_user_action_valid",
        return_value=(False, "Insufficient permission: requires users.view"),
    ):
        with patch("runtime.users.SERVICE", mock_service):
            resp = users_lambda_handler(event, mock_context)
    assert resp["statusCode"] == 403
    body = json.loads(resp["body"])
    assert body.get("errorCode") == "FORBIDDEN"
    assert "requestId" in body
