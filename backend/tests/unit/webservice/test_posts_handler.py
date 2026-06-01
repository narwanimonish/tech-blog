"""
Unit tests for the posts Lambda handler (API behaviour with mocked SERVICE and RBAC).
Handler is loaded from webservice/posts/runtime/posts.py.
"""

from __future__ import annotations

import json
import sys
from unittest.mock import MagicMock, patch

import pytest

from backend.tests.helpers import BACKEND_ROOT, api_event

# Make the posts handler importable (runtime.posts)
_POSTS_HANDLER_DIR = BACKEND_ROOT / "webservice" / "posts"
if str(_POSTS_HANDLER_DIR) not in sys.path:
    sys.path.insert(0, str(_POSTS_HANDLER_DIR))

import runtime.posts as posts_module  # noqa: E402
from runtime.posts import lambda_handler as posts_lambda_handler  # noqa: E402


@pytest.fixture
def mock_service():
    """Mock PostsService for handler tests."""
    return MagicMock()


def test_get_posts_list_returns_200_and_items(mock_context, mock_service):
    mock_service.list_posts.return_value = {
        "items": [{"postId": "p1", "title": "Hi", "body": "World"}],
        "last_evaluated_key": None,
    }
    event = api_event("GET", "/posts")
    with patch.object(posts_module.role_util, "is_user_action_valid", return_value=(True, "")):
        with patch("runtime.posts.SERVICE", mock_service):
            resp = posts_lambda_handler(event, mock_context)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["items"][0]["postId"] == "p1"
    assert body["limit"] == 20
    assert body["nextToken"] is None
    mock_service.list_posts.assert_called_once_with(limit=20, start_key=None)


def test_get_posts_list_honors_limit_and_next_token(mock_context, mock_service):
    token = "abc"
    mock_service.list_posts.return_value = {"items": [], "last_evaluated_key": {"postId": "p9"}}
    event = api_event("GET", "/posts", query_params={"limit": "5", "nextToken": token})
    with patch.object(posts_module.role_util, "is_user_action_valid", return_value=(True, "")):
        with patch("runtime.posts.pagination_util.decode_cursor", return_value={"postId": "p0"}) as decode:
            with patch("runtime.posts.SERVICE", mock_service):
                resp = posts_lambda_handler(event, mock_context)
    assert resp["statusCode"] == 200
    decode.assert_called_once_with(token)
    mock_service.list_posts.assert_called_once_with(limit=5, start_key={"postId": "p0"})


def test_get_post_by_id_returns_200_when_found(mock_context, mock_service):
    mock_service.get_post.return_value = {
        "postId": "p1",
        "title": "Hi",
        "body": "World",
    }
    event = api_event("GET", "/posts/p1", path_params={"postId": "p1"})
    event["path"] = "/posts/p1"
    with patch.object(posts_module.role_util, "is_user_action_valid", return_value=(True, "")):
        with patch("runtime.posts.SERVICE", mock_service):
            resp = posts_lambda_handler(event, mock_context)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["postId"] == "p1"


def test_get_post_by_id_returns_404_when_not_found(mock_context, mock_service):
    mock_service.get_post.return_value = None
    event = api_event("GET", "/posts/p1", path_params={"postId": "p1"})
    event["path"] = "/posts/p1"
    with patch.object(posts_module.role_util, "is_user_action_valid", return_value=(True, "")):
        with patch("runtime.posts.SERVICE", mock_service):
            resp = posts_lambda_handler(event, mock_context)
    assert resp["statusCode"] == 404
    body = json.loads(resp["body"])
    assert body.get("errorCode") == "NOT_FOUND"


def test_post_posts_returns_200_and_calls_create_with_creator_email(mock_context, mock_service):
    mock_service.create_post.return_value = {
        "postId": "pid-123",
        "title": "Hi",
        "body": "World",
        "created_by": "author@example.com",
    }
    event = api_event(
        "POST",
        "/posts",
        body={"title": "Hi", "body": "World"},
        authorizer={"sub": "u1", "email": "author@example.com"},
    )
    with patch.object(posts_module.role_util, "is_user_action_valid", return_value=(True, "")):
        with patch("runtime.posts.SERVICE", mock_service):
            resp = posts_lambda_handler(event, mock_context)
    assert resp["statusCode"] == 200
    mock_service.create_post.assert_called_once()
    call_args = mock_service.create_post.call_args
    assert call_args[0][0] == {"title": "Hi", "body": "World"}
    assert call_args[1]["created_by"] == "author@example.com"


def test_put_post_returns_200(mock_context, mock_service):
    mock_service.update_post.return_value = {
        "postId": "p1",
        "title": "New",
        "body": "New",
    }
    event = api_event(
        "PUT",
        "/posts/p1",
        path_params={"postId": "p1"},
        body={"title": "New", "body": "New"},
    )
    event["path"] = "/posts/p1"
    with patch.object(posts_module.role_util, "is_user_action_valid", return_value=(True, "")):
        with patch("runtime.posts.SERVICE", mock_service):
            resp = posts_lambda_handler(event, mock_context)
    assert resp["statusCode"] == 200
    mock_service.update_post.assert_called_once_with("p1", {"title": "New", "body": "New"})


def test_delete_post_returns_200(mock_context, mock_service):
    event = api_event("DELETE", "/posts/p1", path_params={"postId": "p1"})
    event["path"] = "/posts/p1"
    with patch.object(posts_module.role_util, "is_user_action_valid", return_value=(True, "")):
        with patch("runtime.posts.SERVICE", mock_service):
            resp = posts_lambda_handler(event, mock_context)
    assert resp["statusCode"] == 200
    mock_service.delete_post.assert_called_once_with("p1")


def test_post_posts_returns_400_when_body_invalid_json(mock_context, mock_service):
    event = api_event("POST", "/posts", body=None)
    event["body"] = "not json"
    with patch.object(posts_module.role_util, "is_user_action_valid", return_value=(True, "")):
        with patch("runtime.posts.SERVICE", mock_service):
            resp = posts_lambda_handler(event, mock_context)
    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert body.get("errorCode") == "BAD_REQUEST"


def test_rbac_denied_returns_403(mock_context, mock_service):
    event = api_event("GET", "/posts")
    with patch.object(
        posts_module.role_util,
        "is_user_action_valid",
        return_value=(False, "Insufficient permission"),
    ):
        with patch("runtime.posts.SERVICE", mock_service):
            resp = posts_lambda_handler(event, mock_context)
    assert resp["statusCode"] == 403
    body = json.loads(resp["body"])
    assert body.get("errorCode") == "FORBIDDEN"
