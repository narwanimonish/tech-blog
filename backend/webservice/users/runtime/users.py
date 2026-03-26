"""
Unified users handler.
Routes:
- GET /users
- GET /users/{userId}
- PUT /users/{userId}
- DELETE /users/{userId}
"""

import json
import logging
import os

import boto3
from common import role_util, simple_api_util
from core.users.service import UsersService

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

TABLE_NAME = os.environ.get("usersStoreTable", "users-store")
TABLE = boto3.resource("dynamodb").Table(TABLE_NAME)
SERVICE = UsersService(TABLE)


def lambda_handler(event, context):
    request_id = getattr(context, "aws_request_id", "unknown")
    method = (event.get("httpMethod") or "").upper()
    user_id = (event.get("pathParameters") or {}).get("userId")

    allowed, rbac_message = role_util.is_user_action_valid(event)
    if not allowed:
        return simple_api_util.build_error_response("FORBIDDEN", rbac_message or "Forbidden", 403, request_id=request_id)

    try:
        if method == "GET" and not user_id:
            items = SERVICE.list_users()
            return simple_api_util.build_response(200, {"items": items})

        if method == "GET" and user_id:
            item = SERVICE.get_user(user_id)
            if not item:
                return simple_api_util.build_error_response("NOT_FOUND", "User not found", 404, request_id=request_id)
            return simple_api_util.build_response(200, item)

        if method == "PUT" and user_id:
            body = event.get("body")
            if not body:
                return simple_api_util.build_error_response("BAD_REQUEST", "Body required", 400, request_id=request_id)
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                return simple_api_util.build_error_response("BAD_REQUEST", "Invalid JSON", 400, request_id=request_id)
            return simple_api_util.build_response(200, SERVICE.update_user(user_id, data))

        if method == "DELETE" and user_id:
            SERVICE.delete_user(user_id)
            return simple_api_util.build_response(200, {"message": "Deleted"})

        return simple_api_util.build_error_response(
            "METHOD_NOT_ALLOWED",
            f"Unsupported route or method: {method}",
            405,
            request_id=request_id,
        )
    except Exception as e:
        LOGGER.exception("users handler error: %s", e)
        return simple_api_util.build_error_from_exception(e, request_id=request_id)
