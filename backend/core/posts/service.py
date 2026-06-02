"""
Posts domain service: CRUD for posts. Uses common.dynamodb_util.
Expects table with partition key postId and GSI PostsByCreationTime (listPk, creation_time).
"""

import logging
import uuid
from datetime import datetime, timezone

from common import dynamodb_util, pagination_util
from core.posts.keys import (
    POSTS_BY_CREATION_TIME_INDEX,
    POSTS_LIST_PK,
    POSTS_LIST_PK_VALUE,
)

LOGGER = logging.getLogger(__name__)


class PostsService:
    """Service for posts table operations."""

    def __init__(self, table):
        self._table = table

    @staticmethod
    def _with_list_index_fields(data: dict) -> dict:
        """Ensure GSI attributes exist for list-by-creation-time queries."""
        data[POSTS_LIST_PK] = POSTS_LIST_PK_VALUE
        return data

    def get_post(self, post_id):
        """Get a single post by id. Returns item dict or None."""
        return dynamodb_util.get_item(self._table, {"postId": post_id})

    def update_post(self, post_id, data):
        """Create or update a post. data must be a dict; postId is set to post_id.
        Preserves creation_time and created_by from existing item if not in data."""
        existing = dynamodb_util.get_item(self._table, {"postId": post_id})
        if existing:
            if "creation_time" not in data:
                data["creation_time"] = existing.get("creation_time")
            if "created_by" not in data:
                data["created_by"] = existing.get("created_by")
        data["postId"] = post_id
        self._with_list_index_fields(data)
        dynamodb_util.put_item(self._table, data)
        return data

    def create_post(self, data, created_by=""):
        """Create a new post with auto-generated postId (UUID). Sets creation_time and created_by. Returns created item."""
        data["postId"] = str(uuid.uuid4())
        data["creation_time"] = datetime.now(timezone.utc).isoformat()
        data["created_by"] = created_by
        self._with_list_index_fields(data)
        dynamodb_util.put_item(self._table, data)
        LOGGER.info("Created post %s", data["postId"])
        return data

    def list_posts(self, *, limit: int = pagination_util.DEFAULT_PAGE_SIZE, start_key: dict | None = None) -> dict:
        """List one page of posts (newest first) via GSI PostsByCreationTime."""
        return dynamodb_util.query_page(
            self._table,
            index_name=POSTS_BY_CREATION_TIME_INDEX,
            partition_key_name=POSTS_LIST_PK,
            partition_key_value=POSTS_LIST_PK_VALUE,
            limit=limit,
            exclusive_start_key=start_key,
            scan_index_forward=False,
        )

    def delete_post(self, post_id):
        """Delete a post by id."""
        dynamodb_util.delete_item(self._table, {"postId": post_id})
        LOGGER.info("Deleted post %s", post_id)
