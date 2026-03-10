"""
Lambda: GET /users/{userId} – get one user. Uses dynamodb_util, simple_api_util.
Table env: usersStoreTable.
"""
import logging
import os

import boto3
import common_modules.dynamodb_util as dynamodb_util
import common_modules.simple_api_util as simple_api_util

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

TABLE_NAME = os.environ.get("usersStoreTable", "users-store")
TABLE = boto3.resource("dynamodb").Table(TABLE_NAME)


def lambda_handler(event, context):
    try:
        user_id = (event.get("pathParameters") or {}).get("userId")
        if not user_id:
            return simple_api_util.build_response(400, {"message": "userId required in path"})
        item = dynamodb_util.get_item(TABLE, {"userId": user_id})
        if not item:
            return simple_api_util.build_response(404, {"message": "User not found"})
        return simple_api_util.build_response(200, item)
    except Exception as e:
        LOGGER.exception("users_get error: %s", e)
        return simple_api_util.build_response(500, {"message": "Internal server error"})
