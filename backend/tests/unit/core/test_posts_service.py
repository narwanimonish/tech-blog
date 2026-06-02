"""
Unit tests for PostsService (core logic only; DynamoDB is mocked).
"""

import re

from core.posts.service import PostsService


def test_create_post_sets_post_id_and_metadata(mock_table):
    svc = PostsService(mock_table)
    result = svc.create_post({"title": "Hi", "body": "World"}, created_by="author@example.com")
    assert "postId" in result
    assert re.match(r"^[0-9a-f-]{36}$", result["postId"])
    assert result["title"] == "Hi"
    assert result["body"] == "World"
    assert result["created_by"] == "author@example.com"
    assert "creation_time" in result
    mock_table.put_item.assert_called_once()
    call_item = mock_table.put_item.call_args[1]["Item"]
    assert call_item["created_by"] == "author@example.com"
    assert call_item["listPk"] == "POST"
    assert "creation_time" in call_item


def test_create_post_default_created_by(mock_table):
    svc = PostsService(mock_table)
    result = svc.create_post({"title": "T", "body": "B"}, created_by="")
    assert result["created_by"] == ""


def test_get_post_returns_item(mock_table):
    mock_table.get_item.return_value = {"Item": {"postId": "p1", "title": "T", "body": "B"}}
    svc = PostsService(mock_table)
    result = svc.get_post("p1")
    assert result["postId"] == "p1"
    mock_table.get_item.assert_called_once_with(Key={"postId": "p1"})


def test_get_post_returns_none_when_missing(mock_table):
    mock_table.get_item.return_value = {}
    svc = PostsService(mock_table)
    assert svc.get_post("p1") is None


def test_update_post_preserves_creation_time_and_created_by(mock_table):
    mock_table.get_item.return_value = {
        "Item": {
            "postId": "p1",
            "title": "Old",
            "body": "Old",
            "creation_time": "2025-01-01T00:00:00Z",
            "created_by": "original@example.com",
        }
    }
    svc = PostsService(mock_table)
    result = svc.update_post("p1", {"title": "New", "body": "New"})
    assert result["postId"] == "p1"
    assert result["creation_time"] == "2025-01-01T00:00:00Z"
    assert result["created_by"] == "original@example.com"
    call_item = mock_table.put_item.call_args[1]["Item"]
    assert call_item["creation_time"] == "2025-01-01T00:00:00Z"
    assert call_item["created_by"] == "original@example.com"


def test_update_post_allows_overriding_creation_fields(mock_table):
    mock_table.get_item.return_value = {"Item": {"postId": "p1", "creation_time": "old", "created_by": "old"}}
    svc = PostsService(mock_table)
    svc.update_post("p1", {"creation_time": "new", "created_by": "new@x.com"})
    call_item = mock_table.put_item.call_args[1]["Item"]
    assert call_item["creation_time"] == "new"
    assert call_item["created_by"] == "new@x.com"


def test_delete_post_calls_delete_item(mock_table):
    svc = PostsService(mock_table)
    svc.delete_post("p1")
    mock_table.delete_item.assert_called_once_with(Key={"postId": "p1"})


def test_list_posts_queries_gsi_newest_first(mock_table):
    mock_table.query.return_value = {
        "Items": [{"postId": "p1", "creation_time": "2026-01-02T00:00:00+00:00"}],
        "LastEvaluatedKey": {"postId": "p1", "listPk": "POST", "creation_time": "2026-01-02T00:00:00+00:00"},
    }
    svc = PostsService(mock_table)
    page = svc.list_posts(limit=10, start_key={"postId": "p0", "listPk": "POST"})
    assert page == {
        "items": [{"postId": "p1", "creation_time": "2026-01-02T00:00:00+00:00"}],
        "last_evaluated_key": {
            "postId": "p1",
            "listPk": "POST",
            "creation_time": "2026-01-02T00:00:00+00:00",
        },
    }
    mock_table.query.assert_called_once()
    kwargs = mock_table.query.call_args[1]
    assert kwargs["IndexName"] == "PostsByCreationTime"
    assert kwargs["Limit"] == 10
    assert kwargs["ScanIndexForward"] is False
    assert kwargs["ExclusiveStartKey"] == {"postId": "p0", "listPk": "POST"}
