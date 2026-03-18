"""
Unit tests for UsersService (core logic only; DynamoDB is mocked).
"""
import pytest

from core.users.service import UsersService


def test_get_user_returns_item(mock_table):
    mock_table.get_item.return_value = {"Item": {"userId": "u1", "email": "a@b.com", "name": "Alice"}}
    svc = UsersService(mock_table)
    result = svc.get_user("u1")
    assert result == {"userId": "u1", "email": "a@b.com", "name": "Alice"}
    mock_table.get_item.assert_called_once_with(Key={"userId": "u1"})


def test_get_user_returns_none_when_missing(mock_table):
    mock_table.get_item.return_value = {}
    svc = UsersService(mock_table)
    result = svc.get_user("u1")
    assert result is None


def test_list_users_returns_all_items(mock_table):
    mock_table.scan.return_value = {"Items": [{"userId": "u1"}, {"userId": "u2"}], "LastEvaluatedKey": None}
    svc = UsersService(mock_table)
    result = svc.list_users()
    assert result == [{"userId": "u1"}, {"userId": "u2"}]
    mock_table.scan.assert_called_once()


def test_update_user_calls_put_with_user_id(mock_table):
    svc = UsersService(mock_table)
    result = svc.update_user("u1", {"email": "new@b.com", "name": "Alice"})
    assert result["userId"] == "u1"
    assert result["email"] == "new@b.com"
    mock_table.put_item.assert_called_once()
    call_item = mock_table.put_item.call_args[1]["Item"]
    assert call_item["userId"] == "u1"
    assert call_item["email"] == "new@b.com"


def test_delete_user_calls_delete_item(mock_table):
    svc = UsersService(mock_table)
    svc.delete_user("u1")
    mock_table.delete_item.assert_called_once_with(Key={"userId": "u1"})
