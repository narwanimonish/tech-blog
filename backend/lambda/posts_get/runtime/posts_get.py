"""
Lambda: GET /posts/{postId} – get one post. Uses dynamodb_util, simple_api_util.
Table env: postsTable.
"""
import os
import logging
import boto3

import dynamodb_util
import simple_api_util

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

TABLE_NAME = os.environ.get("postsTable", "posts")
TABLE = boto3.resource("dynamodb").Table(TABLE_NAME)


def lambda_handler(event, context):
    try:
        post_id = (event.get("pathParameters") or {}).get("postId")
        if not post_id:
            return simple_api_util.build_response(400, {"message": "postId required in path"})
        item = dynamodb_util.get_item(TABLE, {"postId": post_id})
        if not item:
            return simple_api_util.build_response(404, {"message": "Post not found"})
        return simple_api_util.build_response(200, item)
    except Exception as e:
        LOGGER.exception("posts_get error: %s", e)
        return simple_api_util.build_response(500, {"message": "Internal server error"})
