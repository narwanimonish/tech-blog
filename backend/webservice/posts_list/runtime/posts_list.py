"""
GET /posts – list all posts.
Handler parses event and delegates to core.posts.service.
"""
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
        items = SERVICE.list_posts()
        return simple_api_util.build_response(200, {"items": items})
    except Exception as e:
        LOGGER.exception("posts_list error: %s", e)
        return simple_api_util.build_error_from_exception(e, request_id=request_id)
