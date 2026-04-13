"""
Users domain service: CRUD for users. Uses common.dynamodb_util.
Expects table with partition key userId.
"""

import logging

from botocore.exceptions import ClientError
from common import dynamodb_util

LOGGER = logging.getLogger(__name__)


def _cognito_username_for_delete(item: dict | None, user_id: str) -> str:
    """Pool Username for AdminDeleteUser: prefer stored value, then email, then userId (sub)."""
    if item:
        if item.get("cognitoUsername"):
            return item["cognitoUsername"]
        if item.get("email"):
            return item["email"]
    return user_id


class UsersService:
    """Service for users table operations."""

    def __init__(self, table, *, cognito_client=None, user_pool_id: str | None = None):
        self._table = table
        self._cognito = cognito_client
        self._user_pool_id = (user_pool_id or "").strip() or None

    def get_user(self, user_id):
        """Get a single user by id. Returns item dict or None."""
        return dynamodb_util.get_item(self._table, {"userId": user_id})

    def update_user(self, user_id, data):
        """Create or update a user. data must be a dict; userId is set to user_id."""
        data["userId"] = user_id
        dynamodb_util.put_item(self._table, data)
        LOGGER.info("Put user %s", user_id)
        return data

    def list_users(self):
        """List all users. Returns list of item dicts."""
        return dynamodb_util.scan_all(self._table)

    def delete_user(self, user_id):
        """Delete a user by id from DynamoDB and, when configured, from the Cognito user pool."""
        item = dynamodb_util.get_item(self._table, {"userId": user_id})
        username = _cognito_username_for_delete(item, user_id)

        if self._cognito and self._user_pool_id:
            try:
                self._cognito.admin_delete_user(UserPoolId=self._user_pool_id, Username=username)
                LOGGER.info("Deleted Cognito user %s (pool user key)", username)
            except ClientError as e:
                code = e.response.get("Error", {}).get("Code", "")
                if code != "UserNotFoundException":
                    LOGGER.exception("Cognito admin_delete_user failed for %s: %s", username, e)
                    raise
                LOGGER.info("Cognito user already absent: %s", username)

        dynamodb_util.delete_item(self._table, {"userId": user_id})
        LOGGER.info("Deleted user %s from DynamoDB", user_id)
