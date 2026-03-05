"""
DELETE /posts/{postId} – delete post.
Handler parses path and delegates to core.posts.service.
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
    try:
        post_id = (event.get("pathParameters") or {}).get("postId")
        if not post_id:
            return simple_api_util.build_response(400, {"message": "postId required in path"})
        SERVICE.delete_post(post_id)
        return simple_api_util.build_response(200, {"message": "Deleted"})
    except Exception as e:
        LOGGER.exception("posts_delete error: %s", e)
        return simple_api_util.build_response(500, {"message": "Internal server error"})
