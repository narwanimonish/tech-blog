"""Unit tests for pagination_util."""

import pytest
from common import pagination_util


def test_encode_decode_cursor_round_trip():
    key = {"postId": "abc-123"}
    token = pagination_util.encode_cursor(key)
    assert token
    assert pagination_util.decode_cursor(token) == key


def test_encode_cursor_returns_none_for_empty_key():
    assert pagination_util.encode_cursor(None) is None
    assert pagination_util.encode_cursor({}) is None


def test_decode_cursor_rejects_invalid_token():
    with pytest.raises(pagination_util.InvalidCursorError):
        pagination_util.decode_cursor("not-a-valid-token")


def test_parse_page_size_defaults_and_bounds():
    assert pagination_util.parse_page_size(None) == pagination_util.DEFAULT_PAGE_SIZE
    assert pagination_util.parse_page_size("50") == 50
    with pytest.raises(pagination_util.InvalidCursorError):
        pagination_util.parse_page_size("0")
    with pytest.raises(pagination_util.InvalidCursorError):
        pagination_util.parse_page_size("101")


def test_build_list_response_includes_next_token_when_more_pages():
    key = {"userId": "u2"}
    body = pagination_util.build_list_response(
        [{"userId": "u1"}],
        limit=pagination_util.DEFAULT_PAGE_SIZE,
        last_evaluated_key=key,
    )
    assert body["items"] == [{"userId": "u1"}]
    assert body["limit"] == pagination_util.DEFAULT_PAGE_SIZE
    assert body["nextToken"] == pagination_util.encode_cursor(key)


def test_build_list_response_null_next_token_on_last_page():
    body = pagination_util.build_list_response(
        [],
        limit=pagination_util.DEFAULT_PAGE_SIZE,
        last_evaluated_key=None,
    )
    assert body["nextToken"] is None
