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
from common import pagination_util, role_util, simple_api_util
from common.lambda_decorators import api_handler, require_rbac
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


def _caller_is_admin(event: dict) -> bool:
    return role_util.resolve_user_role(event) == "admin"


def _ensure_post_owner_or_admin(event: dict, post: dict) -> tuple[bool, str]:
    """Writers may only modify posts they created; admins may modify any post."""
    if _caller_is_admin(event):
        return True, ""
    caller_email = _creator_email(event).lower()
    if not caller_email:
        return False, "Missing user identity (email)"
    owner_email = (post.get("created_by") or "").strip().lower()
    if caller_email != owner_email:
        return False, "You can only modify your own posts"
    return True, ""


@api_handler(LOGGER)
@require_rbac(LOGGER)
def lambda_handler(event, context):
    request_id = getattr(context, "aws_request_id", "unknown")
    method = (event.get("httpMethod") or "").upper()
    post_id = (event.get("pathParameters") or {}).get("postId")

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
        existing = SERVICE.get_post(post_id)
        if not existing:
            return simple_api_util.build_error_response("NOT_FOUND", "Post not found", 404, request_id=request_id)
        allowed, message = _ensure_post_owner_or_admin(event, existing)
        if not allowed:
            return simple_api_util.build_error_response("FORBIDDEN", message, 403, request_id=request_id)
        data.pop("created_by", None)
        return simple_api_util.build_response(200, SERVICE.update_post(post_id, data))

    if method == "DELETE" and post_id:
        existing = SERVICE.get_post(post_id)
        if not existing:
            return simple_api_util.build_error_response("NOT_FOUND", "Post not found", 404, request_id=request_id)
        allowed, message = _ensure_post_owner_or_admin(event, existing)
        if not allowed:
            return simple_api_util.build_error_response("FORBIDDEN", message, 403, request_id=request_id)
        SERVICE.delete_post(post_id)
        return simple_api_util.build_response(200, {"message": "Deleted"})

    return simple_api_util.build_error_response(
        "METHOD_NOT_ALLOWED",
        f"Unsupported route or method: {method}",
        405,
        request_id=request_id,
    )
