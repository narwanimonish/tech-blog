"""
Lambda: GET /posts – list all posts. Uses dynamodb_util, simple_api_util.
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
        items = dynamodb_util.scan_all(TABLE)
        return simple_api_util.build_response(200, {"items": items})
    except Exception as e:
        LOGGER.exception("posts_list error: %s", e)
        return simple_api_util.build_response(500, {"message": "Internal server error"})
