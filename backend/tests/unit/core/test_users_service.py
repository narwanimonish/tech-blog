"""
Unit tests for UsersService (core logic only; DynamoDB is mocked).
"""

from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError
from common.errors import AppError
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


def test_list_users_returns_page(mock_table):
    mock_table.query.return_value = {
        "Items": [{"userId": "u1"}, {"userId": "u2"}],
        "LastEvaluatedKey": {"userId": "u2"},
    }
    svc = UsersService(mock_table)
    page = svc.list_users(limit=2, start_key={"userId": "u0"})
    assert page == {
        "items": [{"userId": "u1"}, {"userId": "u2"}],
        "last_evaluated_key": {"userId": "u2"},
    }
    mock_table.query.assert_called_once()
    kwargs = mock_table.query.call_args.kwargs
    assert kwargs["IndexName"] == "UsersListByCreationTime"
    assert kwargs["Limit"] == 2
    assert kwargs["ExclusiveStartKey"] == {"userId": "u0"}
    assert kwargs["ScanIndexForward"] is False


def test_update_user_merges_into_existing_item(mock_table):
    mock_table.get_item.return_value = {
        "Item": {
            "userId": "u1",
            "email": "old@b.com",
            "name": "Alice",
            "role": "reader",
            "cognitoUsername": "pool-user",
        }
    }
    svc = UsersService(mock_table)
    result = svc.update_user("u1", {"email": "new@b.com", "name": "Bob"})
    assert result["email"] == "new@b.com"
    assert result["name"] == "Bob"
    assert result["role"] == "reader"
    assert result["cognitoUsername"] == "pool-user"
    call_item = mock_table.put_item.call_args[1]["Item"]
    assert call_item["role"] == "reader"


def test_update_user_calls_put_with_user_id(mock_table):
    mock_table.get_item.return_value = {"Item": {"userId": "u1", "email": "old@b.com", "role": "reader"}}
    svc = UsersService(mock_table)
    result = svc.update_user("u1", {"email": "new@b.com", "name": "Alice"})
    assert result["userId"] == "u1"
    assert result["email"] == "new@b.com"
    mock_table.put_item.assert_called_once()
    call_item = mock_table.put_item.call_args[1]["Item"]
    assert call_item["userId"] == "u1"
    assert call_item["email"] == "new@b.com"
    assert call_item["role"] == "reader"


def test_update_user_missing_raises_not_found(mock_table):
    mock_table.get_item.return_value = {}
    svc = UsersService(mock_table)
    with pytest.raises(AppError) as exc:
        svc.update_user("missing", {"email": "a@b.com"})
    assert exc.value.code == "NOT_FOUND"
    mock_table.put_item.assert_not_called()


def test_upsert_user_creates_first_user_as_admin(mock_table):
    mock_table.get_item.return_value = {}
    mock_table.query.return_value = {"Items": []}
    svc = UsersService(mock_table)
    result = svc.upsert_user("u1", {"email": "first@example.com", "name": "First"})
    assert result["role"] == "admin"
    assert result["email"] == "first@example.com"
    assert result["listPk"] == "USER"
    assert result["creation_time"]
    mock_table.put_item.assert_called_once()


def test_upsert_user_creates_second_user_as_reader(mock_table):
    mock_table.get_item.return_value = {}
    mock_table.query.return_value = {"Items": [{"userId": "existing"}]}
    svc = UsersService(mock_table)
    result = svc.upsert_user("u2", {"email": "second@example.com"})
    assert result["role"] == "reader"


def test_upsert_user_preserves_role_on_existing(mock_table):
    mock_table.get_item.return_value = {"Item": {"userId": "u1", "email": "a@b.com", "role": "writer", "name": "Alice"}}
    svc = UsersService(mock_table)
    result = svc.upsert_user("u1", {"email": "new@b.com"})
    assert result["role"] == "writer"
    assert result["email"] == "new@b.com"
    assert result["listPk"] == "USER"
    assert result["creation_time"]


def test_delete_user_calls_get_then_delete_item(mock_table):
    mock_table.get_item.return_value = {}
    svc = UsersService(mock_table)
    svc.delete_user("u1")
    mock_table.get_item.assert_called_once_with(Key={"userId": "u1"})
    mock_table.delete_item.assert_called_once_with(Key={"userId": "u1"})


def test_delete_user_calls_cognito_when_configured(mock_table):
    cognito = MagicMock()
    mock_table.get_item.return_value = {
        "Item": {
            "userId": "sub-1",
            "email": "a@b.com",
            "cognitoUsername": "pool-username-xyz",
        }
    }
    svc = UsersService(mock_table, cognito_client=cognito, user_pool_id="pool-id")
    svc.delete_user("sub-1")
    cognito.admin_delete_user.assert_called_once_with(
        UserPoolId="pool-id",
        Username="pool-username-xyz",
    )
    mock_table.delete_item.assert_called_once_with(Key={"userId": "sub-1"})


def test_delete_user_cognito_username_falls_back_to_email(mock_table):
    cognito = MagicMock()
    mock_table.get_item.return_value = {"Item": {"userId": "sub-1", "email": "only@email.com"}}
    svc = UsersService(mock_table, cognito_client=cognito, user_pool_id="pool-id")
    svc.delete_user("sub-1")
    cognito.admin_delete_user.assert_called_once_with(
        UserPoolId="pool-id",
        Username="only@email.com",
    )


def test_delete_user_cognito_ignores_user_not_found(mock_table):
    cognito = MagicMock()
    cognito.admin_delete_user.side_effect = ClientError(
        {"Error": {"Code": "UserNotFoundException", "Message": "not found"}},
        "AdminDeleteUser",
    )
    mock_table.get_item.return_value = {}
    svc = UsersService(mock_table, cognito_client=cognito, user_pool_id="pool-id")
    svc.delete_user("sub-1")
    mock_table.delete_item.assert_called_once_with(Key={"userId": "sub-1"})


def test_update_user_role_sets_role(mock_table):
    mock_table.get_item.return_value = {"Item": {"userId": "u1", "email": "a@b.com", "role": "reader"}}
    svc = UsersService(mock_table)
    out = svc.update_user_role("u1", "writer")
    assert out["role"] == "writer"
    assert out["email"] == "a@b.com"
    mock_table.put_item.assert_called_once()
    item = mock_table.put_item.call_args[1]["Item"]
    assert item["role"] == "writer"
    assert item["userId"] == "u1"


def test_update_user_role_normalizes_case(mock_table):
    mock_table.get_item.return_value = {"Item": {"userId": "u1", "email": "a@b.com", "role": "reader"}}
    svc = UsersService(mock_table)
    out = svc.update_user_role("u1", "ADMIN")
    assert out["role"] == "admin"


@pytest.mark.parametrize("bad", ["", "superuser", "guest"])
def test_update_user_role_invalid_raises(mock_table, bad):
    mock_table.get_item.return_value = {"Item": {"userId": "u1", "role": "reader"}}
    svc = UsersService(mock_table)
    with pytest.raises(AppError) as exc:
        svc.update_user_role("u1", bad)
    assert exc.value.code == "BAD_REQUEST"
    mock_table.put_item.assert_not_called()


def test_update_user_role_missing_user_raises(mock_table):
    mock_table.get_item.return_value = {}
    svc = UsersService(mock_table)
    with pytest.raises(AppError) as exc:
        svc.update_user_role("missing", "writer")
    assert exc.value.code == "NOT_FOUND"


def test_delete_user_cognito_propagates_other_client_errors(mock_table):
    cognito = MagicMock()
    cognito.admin_delete_user.side_effect = ClientError(
        {"Error": {"Code": "TooManyRequestsException", "Message": "slow down"}},
        "AdminDeleteUser",
    )
    mock_table.get_item.return_value = {"Item": {"userId": "sub-1", "email": "a@b.com"}}
    svc = UsersService(mock_table, cognito_client=cognito, user_pool_id="pool-id")
    with pytest.raises(ClientError):
        svc.delete_user("sub-1")
    mock_table.delete_item.assert_not_called()
