"""
Lambda: DELETE /users/{userId} – delete user. Uses dynamodb_util, simple_api_util.
Table env: usersStoreTable.
"""
import os
import logging
import boto3

import dynamodb_util
import simple_api_util

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

TABLE_NAME = os.environ.get("usersStoreTable", "users-store")
TABLE = boto3.resource("dynamodb").Table(TABLE_NAME)


def lambda_handler(event, context):
    try:
        user_id = (event.get("pathParameters") or {}).get("userId")
        if not user_id:
            return simple_api_util.build_response(400, {"message": "userId required in path"})
        dynamodb_util.delete_item(TABLE, {"userId": user_id})
        LOGGER.info("Deleted user %s", user_id)
        return simple_api_util.build_response(200, {"message": "Deleted"})
    except Exception as e:
        LOGGER.exception("users_delete error: %s", e)
        return simple_api_util.build_response(500, {"message": "Internal server error"})
