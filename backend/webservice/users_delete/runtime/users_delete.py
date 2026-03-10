"""DELETE /users/{userId} – delete user."""
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
    request_id = getattr(context, "aws_request_id", "unknown")
    try:
        user_id = (event.get("pathParameters") or {}).get("userId")
        if not user_id:
            return simple_api_util.build_error_response("BAD_REQUEST", "userId required in path", 400, request_id=request_id)
        SERVICE.delete_user(user_id)
        return simple_api_util.build_response(200, {"message": "Deleted"})
    except Exception as e:
        LOGGER.exception("users_delete error: %s", e)
        return simple_api_util.build_error_from_exception(e, request_id=request_id)
