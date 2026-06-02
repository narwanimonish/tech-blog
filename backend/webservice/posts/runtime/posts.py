"""
Unified posts handler.
Routes:
- GET /posts
- POST /posts
- GET /posts/{postId}
- PUT /posts/{postId}
- DELETE /posts/{postId}
"""

import json
import logging
import os

import boto3
from common import pagination_util, role_util, simple_api_util, warmup_util
from core.posts.service import PostsService

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

TABLE_NAME = os.environ.get("postsTable", "posts")
TABLE = boto3.resource("dynamodb").Table(TABLE_NAME)
SERVICE = PostsService(TABLE)


def _creator_email(event):
    """Extract creator email from authorizer context or users table fallback."""
    authorizer = (event.get("requestContext") or {}).get("authorizer") or {}
    email = (authorizer.get("email") or "").strip()
    if email:
        return email
    for key in ("username", "cognitoUsername"):
        candidate = (authorizer.get(key) or "").strip()
        if "@" in candidate:
            return candidate
    sub = authorizer.get("sub") or authorizer.get("principalId") or ""
    users_table = os.environ.get("usersStoreTable", "")
    if sub and users_table:
        return role_util.get_user_email(sub, users_table)
    return ""


def lambda_handler(event, context):
    if warmup_util.is_warmup_event(event):
        return warmup_util.api_warmup_response()

    request_id = getattr(context, "aws_request_id", "unknown")
    method = (event.get("httpMethod") or "").upper()
    post_id = (event.get("pathParameters") or {}).get("postId")

    allowed, rbac_message = role_util.is_user_action_valid(event)
    if not allowed:
        return simple_api_util.build_error_response("FORBIDDEN", rbac_message or "Forbidden", 403, request_id=request_id)

    try:
        if method == "GET" and not post_id:
            try:
                limit, start_key = pagination_util.parse_list_params(event)
            except pagination_util.InvalidCursorError as exc:
                return simple_api_util.build_error_response(
                    "BAD_REQUEST",
                    str(exc),
                    400,
                    request_id=request_id,
                )
            page = SERVICE.list_posts(limit=limit, start_key=start_key)
            body = pagination_util.build_list_response(
                page["items"],
                limit=limit,
                last_evaluated_key=page.get("last_evaluated_key"),
            )
            return simple_api_util.build_response(200, body)

        if method == "POST" and not post_id:
            body = event.get("body")
            if not body:
                return simple_api_util.build_error_response("BAD_REQUEST", "Body required", 400, request_id=request_id)
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                return simple_api_util.build_error_response("BAD_REQUEST", "Invalid JSON", 400, request_id=request_id)
            return simple_api_util.build_response(200, SERVICE.create_post(data, created_by=_creator_email(event)))

        if method == "GET" and post_id:
            item = SERVICE.get_post(post_id)
            if not item:
                return simple_api_util.build_error_response("NOT_FOUND", "Post not found", 404, request_id=request_id)
            return simple_api_util.build_response(200, item)

        if method == "PUT" and post_id:
            body = event.get("body")
            if not body:
                return simple_api_util.build_error_response("BAD_REQUEST", "Body required", 400, request_id=request_id)
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                return simple_api_util.build_error_response("BAD_REQUEST", "Invalid JSON", 400, request_id=request_id)
            return simple_api_util.build_response(200, SERVICE.update_post(post_id, data))

        if method == "DELETE" and post_id:
            SERVICE.delete_post(post_id)
            return simple_api_util.build_response(200, {"message": "Deleted"})

        return simple_api_util.build_error_response(
            "METHOD_NOT_ALLOWED",
            f"Unsupported route or method: {method}",
            405,
            request_id=request_id,
        )
    except Exception as e:
        LOGGER.exception("posts handler error: %s", e)
        return simple_api_util.build_error_from_exception(e, request_id=request_id)
