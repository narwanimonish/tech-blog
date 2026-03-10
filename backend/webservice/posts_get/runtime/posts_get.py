"""GET /posts/{postId} – get one post."""
import logging
import os

import boto3

from common import simple_api_util
from core.posts.service import PostsService

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

TABLE_NAME = os.environ.get("postsTable", "posts")
TABLE = boto3.resource("dynamodb").Table(TABLE_NAME)
SERVICE = PostsService(TABLE)


def lambda_handler(event, context):
    request_id = getattr(context, "aws_request_id", "unknown")
    try:
        post_id = (event.get("pathParameters") or {}).get("postId")
        if not post_id:
            return simple_api_util.build_error_response("BAD_REQUEST", "postId required in path", 400, request_id=request_id)
        item = SERVICE.get_post(post_id)
        if not item:
            return simple_api_util.build_error_response("NOT_FOUND", "Post not found", 404, request_id=request_id)
        return simple_api_util.build_response(200, item)
    except Exception as e:
        LOGGER.exception("posts_get error: %s", e)
        return simple_api_util.build_error_from_exception(e, request_id=request_id)
