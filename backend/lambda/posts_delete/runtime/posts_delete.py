"""
Lambda: DELETE /posts/{postId} – delete post. Uses dynamodb_util, simple_api_util.
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
        dynamodb_util.delete_item(TABLE, {"postId": post_id})
        LOGGER.info("Deleted post %s", post_id)
        return simple_api_util.build_response(200, {"message": "Deleted"})
    except Exception as e:
        LOGGER.exception("posts_delete error: %s", e)
        return simple_api_util.build_response(500, {"message": "Internal server error"})
