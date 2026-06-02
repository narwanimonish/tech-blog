from common import role_cache


def test_get_cached_role_reuses_value_within_ttl():
    role_cache._ROLE_CACHE.clear()
    calls = {"count": 0}

    def loader():
        calls["count"] += 1
        return "writer"

    assert role_cache.get_cached_role("user-1", loader) == "writer"
    assert role_cache.get_cached_role("user-1", loader) == "writer"
    assert calls["count"] == 1


def test_get_cached_user_profile_reuses_value_within_ttl():
    role_cache._USER_PROFILE_CACHE.clear()
    calls = {"count": 0}

    def loader():
        calls["count"] += 1
        return ("writer", "writer@example.com")

    assert role_cache.get_cached_user_profile("user-1", loader) == ("writer", "writer@example.com")
    assert role_cache.get_cached_user_profile("user-1", loader) == ("writer", "writer@example.com")
    assert calls["count"] == 1
