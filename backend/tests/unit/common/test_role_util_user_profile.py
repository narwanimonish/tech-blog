"""Tests for DynamoDB user profile lookups (role + email)."""

from __future__ import annotations

from unittest.mock import patch

from common import role_util


@patch.object(role_util, "_get_user_item", return_value={"role": "writer", "email": "writer@example.com"})
def test_get_user_role_and_email_returns_stored_values(_mock_item):
    role, email = role_util.get_user_role_and_email("user-1", "users-table")
    assert role == "writer"
    assert email == "writer@example.com"


@patch.object(role_util, "_get_user_item", return_value={"email": "reader@example.com"})
def test_get_user_role_and_email_defaults_role_when_missing(_mock_item):
    role, email = role_util.get_user_role_and_email("user-1", "users-table")
    assert role == "reader"
    assert email == "reader@example.com"


@patch.object(role_util, "_get_user_item", return_value={"role": "writer", "email": "writer@example.com"})
def test_get_user_email_returns_email_only(_mock_item):
    assert role_util.get_user_email("user-1", "users-table") == "writer@example.com"
