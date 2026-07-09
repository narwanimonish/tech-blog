"""
Unified users handler.
Routes:
- GET /users
- GET /users/{userId}
- PUT /users/{userId}  (profile; **role** ignored)
- PUT /users/{userId}/role  (admin: change role)
- DELETE /users/{userId}
"""

import json
import logging
import os

import boto3
from common import pagination_util, role_util, simple_api_util
from common.errors import AppError
from common.lambda_decorators import api_handler, require_rbac
from core.users.service import UsersService

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

TABLE_NAME = os.environ.get("usersStoreTable", "users-store")
TABLE = boto3.resource("dynamodb").Table(TABLE_NAME)
_USER_POOL_ID = os.environ.get("USER_POOL_ID", "").strip()
_POOL_REGION = os.environ.get("USER_POOL_REGION", os.environ.get("AWS_REGION", "us-east-1"))
_COGNITO_CLIENT = boto3.client("cognito-idp", region_name=_POOL_REGION) if _USER_POOL_ID else None
SERVICE = UsersService(
    TABLE,
    cognito_client=_COGNITO_CLIENT,
    user_pool_id=_USER_POOL_ID or None,
)


def _is_put_user_role(event: dict) -> bool:
    """True when request is PUT /users/{userId}/role (pathParameters.userId matches path segment).

    Example:
    {
        "httpMethod": "PUT",
        "path": "/users/123/role",
        "pathParameters": {
            "userId": "123"
        }
    }
    Returns True if the request is a PUT request to the /users/{userId}/role endpoint.
    Returns False otherwise.
    """
    if (event.get("httpMethod") or "").upper() != "PUT":
        return False
    path = (event.get("path") or "").rstrip("/") or ""
    if not path.startswith("/"):
        path = "/" + path
    parts = path.strip("/").split("/")
    user_id = (event.get("pathParameters") or {}).get("userId")
    return bool(user_id) and len(parts) == 3 and parts[0] == "users" and parts[1] == user_id and parts[2] == "role"


def _caller_sub(event: dict) -> str:
    authorizer = (event.get("requestContext") or {}).get("authorizer") or {}
    return authorizer.get("sub") or authorizer.get("principalId") or ""


def _caller_is_admin(event: dict) -> bool:
    sub = _caller_sub(event)
    if not sub:
        return False
    role = role_util.resolve_user_role(event)
    return role == "admin"


def _ensure_self_or_admin(event: dict, target_user_id: str) -> tuple[bool, str]:
    if _caller_is_admin(event):
        return True, ""
    caller = _caller_sub(event)
    if not caller:
        return False, "Missing user identity (sub)"
    if caller != target_user_id:
        return False, "You can only access your own profile"
    return True, ""


def _profile_update_payload(data: dict) -> dict:
    """Allowed profile fields for PUT /users/{userId} (merged into existing DynamoDB item)."""
    payload = {}
    if "email" in data and data["email"] is not None:
        payload["email"] = str(data["email"]).strip()
    if "name" in data:
        name = data["name"]
        payload["name"] = str(name).strip() if name is not None else ""
    return payload


@api_handler(LOGGER)
@require_rbac(LOGGER)
def lambda_handler(event, context):
    request_id = getattr(context, "aws_request_id", "unknown")
    method = (event.get("httpMethod") or "").upper()
    user_id = (event.get("pathParameters") or {}).get("userId")

    if method == "GET" and not user_id:
        try:
            limit, start_key = pagination_util.parse_list_params(event)
        except pagination_util.InvalidCursorError as exc:
            return simple_api_util.build_error_response(
                "BAD_REQUEST",
                str(exc),
                400,
                request_id=request_id,
            )
        page = SERVICE.list_users(limit=limit, start_key=start_key)
        body = pagination_util.build_list_response(
            page["items"],
            limit=limit,
            last_evaluated_key=page.get("last_evaluated_key"),
        )
        return simple_api_util.build_response(200, body)

    if method == "GET" and user_id:
        allowed_self, self_msg = _ensure_self_or_admin(event, user_id)
        if not allowed_self:
            return simple_api_util.build_error_response("FORBIDDEN", self_msg, 403, request_id=request_id)
        item = SERVICE.get_user(user_id)
        if not item:
            return simple_api_util.build_error_response("NOT_FOUND", "User not found", 404, request_id=request_id)
        return simple_api_util.build_response(200, item)

    if _is_put_user_role(event):
        body = event.get("body")
        if not body:
            return simple_api_util.build_error_response("BAD_REQUEST", "Body required", 400, request_id=request_id)
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            return simple_api_util.build_error_response("BAD_REQUEST", "Invalid JSON", 400, request_id=request_id)
        if "role" not in data:
            return simple_api_util.build_error_response("BAD_REQUEST", "role is required", 400, request_id=request_id)
        try:
            updated = SERVICE.update_user_role(user_id, data["role"])
        except AppError as err:
            return simple_api_util.build_error_response(err.code, err.message, err.status_code, request_id=request_id)
        return simple_api_util.build_response(200, updated)

    if method == "PUT" and user_id:
        allowed_self, self_msg = _ensure_self_or_admin(event, user_id)
        if not allowed_self:
            return simple_api_util.build_error_response("FORBIDDEN", self_msg, 403, request_id=request_id)
        body = event.get("body")
        if not body:
            return simple_api_util.build_error_response("BAD_REQUEST", "Body required", 400, request_id=request_id)
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            return simple_api_util.build_error_response("BAD_REQUEST", "Invalid JSON", 400, request_id=request_id)
        profile = _profile_update_payload(data)
        if not profile:
            return simple_api_util.build_error_response(
                "BAD_REQUEST",
                "At least one of email or name is required",
                400,
                request_id=request_id,
            )
        try:
            updated = SERVICE.update_user(user_id, profile)
        except AppError as err:
            return simple_api_util.build_error_response(err.code, err.message, err.status_code, request_id=request_id)
        return simple_api_util.build_response(200, updated)

    if method == "DELETE" and user_id:
        SERVICE.delete_user(user_id)
        return simple_api_util.build_response(200, {"message": "Deleted"})

    return simple_api_util.build_error_response(
        "METHOD_NOT_ALLOWED",
        f"Unsupported route or method: {method}",
        405,
        request_id=request_id,
    )
