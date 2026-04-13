"""
Unit tests for UsersService (core logic only; DynamoDB is mocked).
"""

from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

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
    mock_table.scan.return_value = {
        "Items": [{"userId": "u1"}, {"userId": "u2"}],
        "LastEvaluatedKey": None,
    }
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


# only updates the attributes which are mentioned while calling update()


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
