"""
Posts domain service: CRUD for posts. Uses common.dynamodb_util.
Expects table with partition key postId.
"""

import logging
import uuid
from datetime import datetime, timezone

from common import dynamodb_util

LOGGER = logging.getLogger(__name__)


class PostsService:
    """Service for posts table operations."""

    def __init__(self, table):
        self._table = table

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
        dynamodb_util.put_item(self._table, data)
        return data

    def create_post(self, data, created_by=""):
        """Create a new post with auto-generated postId (UUID). Sets creation_time and created_by. Returns created item."""
        data["postId"] = str(uuid.uuid4())
        data["creation_time"] = datetime.now(timezone.utc).isoformat()
        data["created_by"] = created_by
        dynamodb_util.put_item(self._table, data)
        LOGGER.info("Created post %s", data["postId"])
        return data

    def list_posts(self, *, limit: int = 20, start_key: dict | None = None) -> dict:
        """List one page of posts. Returns items and optional DynamoDB cursor."""
        return dynamodb_util.scan_page(self._table, limit=limit, exclusive_start_key=start_key)

    def delete_post(self, post_id):
        """Delete a post by id."""
        dynamodb_util.delete_item(self._table, {"postId": post_id})
        LOGGER.info("Deleted post %s", post_id)
