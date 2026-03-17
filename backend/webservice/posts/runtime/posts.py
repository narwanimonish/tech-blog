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

from common import role_util
from common import simple_api_util
from core.posts.service import PostsService

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

TABLE_NAME = os.environ.get("postsTable", "posts")
TABLE = boto3.resource("dynamodb").Table(TABLE_NAME)
SERVICE = PostsService(TABLE)


def _creator_email(event):
    """Extract creator email from authorizer context (set by custom Lambda authorizer)."""
    authorizer = (event.get("requestContext") or {}).get("authorizer") or {}
    return authorizer.get("email") or ""


def lambda_handler(event, context):
    request_id = getattr(context, "aws_request_id", "unknown")
    method = (event.get("httpMethod") or "").upper()
    post_id = (event.get("pathParameters") or {}).get("postId")

    allowed, rbac_message = role_util.is_user_action_valid(event)
    if not allowed:
        return simple_api_util.build_error_response(
            "FORBIDDEN", rbac_message or "Forbidden", 403, request_id=request_id
        )

    try:
        if method == "GET" and not post_id:
            items = SERVICE.list_posts()
            return simple_api_util.build_response(200, {"items": items})

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
