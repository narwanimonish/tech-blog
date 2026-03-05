"""
GET /users/{userId} – get one user.
Handler parses event and delegates to core.users.service.
"""
import logging
import os

import boto3

from common import simple_api_util
from core.users.service import UsersService

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

TABLE_NAME = os.environ.get("usersStoreTable", "users-store")
TABLE = boto3.resource("dynamodb").Table(TABLE_NAME)
SERVICE = UsersService(TABLE)


def lambda_handler(event, context):
    try:
        user_id = (event.get("pathParameters") or {}).get("userId")
        if not user_id:
            return simple_api_util.build_response(400, {"message": "userId required in path"})
        item = SERVICE.get_user(user_id)
        if not item:
            return simple_api_util.build_response(404, {"message": "User not found"})
        return simple_api_util.build_response(200, item)
    except Exception as e:
        LOGGER.exception("users_get error: %s", e)
        return simple_api_util.build_response(500, {"message": "Internal server error"})
