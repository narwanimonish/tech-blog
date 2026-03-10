"""
Posts domain service: CRUD for posts. Uses common.dynamodb_util.
Expects table with partition key postId.
"""
import logging
import uuid

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
        """Create or update a post. data must be a dict; postId is set to post_id."""
        data["postId"] = post_id
        dynamodb_util.put_item(self._table, data)
        return data

    def create_post(self, data):
        """Create a new post with auto-generated postId (UUID). Returns created item."""
        data["postId"] = str(uuid.uuid4())
        dynamodb_util.put_item(self._table, data)
        LOGGER.info("Created post %s", data["postId"])
        return data

    def list_posts(self):
        """List all posts. Returns list of item dicts."""
        return dynamodb_util.scan_all(self._table)

    def delete_post(self, post_id):
        """Delete a post by id."""
        dynamodb_util.delete_item(self._table, {"postId": post_id})
        LOGGER.info("Deleted post %s", post_id)
