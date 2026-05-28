"""
RBAC path matching: stage-prefixed paths and API Gateway resource templates.
"""

from __future__ import annotations

from unittest.mock import patch

from common import role_util


@patch.object(role_util, "_get_user_role", return_value="admin")
def test_put_user_role_allowed_with_stage_prefix(_mock_role):
    event = {
        "httpMethod": "PUT",
        "path": "/dev/users/u1/role",
        "requestContext": {"authorizer": {"sub": "admin-sub"}},
    }
    ok, msg = role_util.is_user_action_valid(event)
    assert ok is True
    assert msg == ""


@patch.object(role_util, "_get_user_role", return_value="admin")
def test_put_user_role_allowed_with_resource_template(_mock_role):
    event = {
        "httpMethod": "PUT",
        "resource": "/users/{userId}/role",
        "path": "/dev/users/u1/role",
        "requestContext": {"authorizer": {"sub": "admin-sub"}},
    }
    ok, msg = role_util.is_user_action_valid(event)
    assert ok is True
    assert msg == ""


@patch.object(role_util, "_get_user_role", return_value="admin")
def test_get_users_allowed_with_stage_prefix(_mock_role):
    event = {
        "httpMethod": "GET",
        "path": "/dev/users",
        "requestContext": {"authorizer": {"sub": "admin-sub"}},
    }
    ok, msg = role_util.is_user_action_valid(event)
    assert ok is True


@patch.object(role_util, "_get_user_role", return_value="admin")
def test_put_user_role_allowed_resource_without_leading_slash(_mock_role):
    event = {
        "httpMethod": "PUT",
        "resource": "users/{userId}/role",
        "path": "/dev/users/u1/role",
        "requestContext": {"authorizer": {"sub": "admin-sub"}},
    }
    ok, msg = role_util.is_user_action_valid(event)
    assert ok is True
    assert msg == ""


@patch.object(role_util, "_get_user_role", return_value="admin")
def test_put_user_role_allowed_via_resource_path_only(_mock_role):
    event = {
        "httpMethod": "PUT",
        "path": "/prod/users/abc-123/role",
        "requestContext": {
            "authorizer": {"sub": "admin-sub"},
            "resourcePath": "/users/{userId}/role",
        },
    }
    ok, msg = role_util.is_user_action_valid(event)
    assert ok is True
    assert msg == ""


@patch.object(role_util, "_get_user_role", return_value="admin")
def test_method_from_request_context(_mock_role):
    event = {
        "path": "/users/u1/role",
        "requestContext": {
            "httpMethod": "PUT",
            "authorizer": {"sub": "admin-sub"},
        },
    }
    ok, msg = role_util.is_user_action_valid(event)
    assert ok is True


@patch.object(role_util, "_get_user_role", return_value="reader")
def test_put_user_role_denied_for_reader_even_with_valid_path(_mock_role):
    event = {
        "httpMethod": "PUT",
        "path": "/users/u1/role",
        "requestContext": {"authorizer": {"sub": "reader-sub"}},
    }
    ok, msg = role_util.is_user_action_valid(event)
    assert ok is False
    assert "users.fullaccess" in msg


@patch.object(role_util, "_get_user_role")
def test_resolve_user_role_prefers_authorizer_context(mock_get_role):
    event = {"requestContext": {"authorizer": {"sub": "user-1", "role": "writer"}}}
    role = role_util.resolve_user_role(event)
    assert role == "writer"
    mock_get_role.assert_not_called()
