"""
Lambda: PUT /posts/{postId} – create or update post. Uses dynamodb_util, simple_api_util.
Table env: postsTable.
"""
import os
import json
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
        body = event.get("body")
        if not body:
            return simple_api_util.build_response(400, {"message": "Body required"})
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            return simple_api_util.build_response(400, {"message": "Invalid JSON"})
        data["postId"] = post_id
        dynamodb_util.put_item(TABLE, data)
        LOGGER.info("Updated post %s", post_id)
        return simple_api_util.build_response(200, data)
    except Exception as e:
        LOGGER.exception("posts_put error: %s", e)
        return simple_api_util.build_response(500, {"message": "Internal server error"})
