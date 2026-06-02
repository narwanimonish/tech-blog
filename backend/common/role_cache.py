"""Short-lived in-process cache for DynamoDB role lookups."""

from __future__ import annotations

import time

_ROLE_CACHE: dict[str, tuple[str, float]] = {}
_USER_PROFILE_CACHE: dict[str, tuple[tuple[str, str], float]] = {}
_DEFAULT_TTL_SECONDS = 300


def get_cached_role(user_id: str, loader, *, ttl_seconds: int = _DEFAULT_TTL_SECONDS) -> str:
    """Return cached role for user_id or load via loader() and cache the result."""
    if not user_id:
        return loader()

    now = time.time()
    cached = _ROLE_CACHE.get(user_id)
    if cached and cached[1] > now:
        return cached[0]

    role = loader()
    _ROLE_CACHE[user_id] = (role, now + ttl_seconds)
    return role


def get_cached_user_profile(user_id: str, loader, *, ttl_seconds: int = _DEFAULT_TTL_SECONDS) -> tuple[str, str]:
    """Return cached (role, email) for user_id or load via loader() and cache the result."""
    if not user_id:
        return loader()

    now = time.time()
    cached = _USER_PROFILE_CACHE.get(user_id)
    if cached and cached[1] > now:
        return cached[0]

    profile = loader()
    _USER_PROFILE_CACHE[user_id] = (profile, now + ttl_seconds)
    return profile
