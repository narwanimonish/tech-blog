"""
Users domain service: CRUD for users. Uses common.dynamodb_util.
Expects table with partition key userId.
"""
import logging

from common import dynamodb_util

LOGGER = logging.getLogger(__name__)


class UsersService:
    """Service for users table operations."""

    def __init__(self, table):
        self._table = table

    def get_user(self, user_id):
        """Get a single user by id. Returns item dict or None."""
        return dynamodb_util.get_item(self._table, {"userId": user_id})

    def put_user(self, user_id, data):
        """Create or update a user. data must be a dict; userId is set to user_id."""
        data["userId"] = user_id
        dynamodb_util.put_item(self._table, data)
        LOGGER.info("Put user %s", user_id)
        return data

    def list_users(self):
        """List all users. Returns list of item dicts."""
        return dynamodb_util.scan_all(self._table)

    def delete_user(self, user_id):
        """Delete a user by id."""
        dynamodb_util.delete_item(self._table, {"userId": user_id})
        LOGGER.info("Deleted user %s", user_id)
