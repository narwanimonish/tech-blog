"""
POST /posts – create post (postId auto-generated).
Handler parses body and delegates to core.posts.service.
"""
import json
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
        body = event.get("body")
        if not body:
            return simple_api_util.build_response(400, {"message": "Body required"})
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            return simple_api_util.build_response(400, {"message": "Invalid JSON"})
        data = SERVICE.create_post(data)
        return simple_api_util.build_response(200, data)
    except Exception as e:
        LOGGER.exception("posts_post error: %s", e)
        return simple_api_util.build_response(500, {"message": "Internal server error"})
