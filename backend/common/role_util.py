"""
Role-based access control for tech-blog API.
Validates that the authenticated user's role has the permissions required for the API path/method.
Uses: service_level_permissions.json, consolidated_api_permissions.json, role_permissions.json.
User role is read from DynamoDB users table (field "role"); default role is "reader" if missing.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import boto3

LOGGER = logging.getLogger(__name__)

# Level hierarchy: higher index = more privilege. fullaccess implies manage and view.
_LEVEL_ORDER = ("view", "manage", "fullaccess")

_RBAC_DIR = Path(__file__).resolve().parent / "rbac_config"


def _load_json(name: str) -> dict:
    path = _RBAC_DIR / name
    if not path.is_file():
        LOGGER.warning("RBAC config missing: %s", path)
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        LOGGER.exception("Failed to load RBAC config %s: %s", name, e)
        return {}


def _get_api_permissions_config() -> list:
    data = _load_json("consolidated_api_permissions.json")
    return data.get("apis", [])


def _get_role_permissions_config() -> dict:
    data = _load_json("role_permissions.json")
    return data.get("roles", {}), data.get("default_role", "reader")


def _normalize_path(path: str) -> str:
    """Convert request path to config path template, e.g. /users/abc-123 -> /users/{userId}."""
    if not path or not path.startswith("/"):
        return path
    parts = path.strip("/").split("/")
    if len(parts) == 1:
        return "/" + parts[0]
    if parts[0] == "users" and len(parts) == 2:
        return "/users/{userId}"
    if parts[0] == "posts" and len(parts) == 2:
        return "/posts/{postId}"
    return path


def _get_required_permissions(path: str, method: str) -> list[str]:
    normalized = _normalize_path(path)
    apis = _get_api_permissions_config()
    for api in apis:
        if api.get("path") == normalized and (api.get("method") or "").upper() == (method or "").upper():
            return api.get("permissions", [])
    LOGGER.warning("No API permission rule for %s %s (normalized %s)", method, path, normalized)
    return []


def _level_rank(level: str) -> int:
    level = (level or "").lower()
    for i, lv in enumerate(_LEVEL_ORDER):
        if lv == level:
            return i
    return -1


def _role_has_permission(role_permissions: dict, required_permission: str) -> bool:
    """
    Check if role's permissions satisfy required permission.
    required_permission is e.g. "posts.manage". Role has {"posts": "manage", "users": "view"}.
    fullaccess >= manage >= view.
    """
    if not required_permission or "." not in required_permission:
        return False
    service, required_level = required_permission.split(".", 1)
    role_level = (role_permissions.get(service) or "").lower()
    required_rank = _level_rank(required_level)
    role_rank = _level_rank(role_level)
    if required_rank < 0 or role_rank < 0:
        return False
    return role_rank >= required_rank


def _get_user_role(user_id: str, users_table_name: str) -> str:
    """Look up user in DynamoDB users table; return role field or default_role."""
    if not users_table_name or not user_id:
        return _get_role_permissions_config()[1]
    try:
        table = boto3.resource("dynamodb").Table(users_table_name)
        resp = table.get_item(Key={"userId": user_id})
        item = resp.get("Item") or {}
        role = (item.get("role") or "").strip().lower()
        roles, default = _get_role_permissions_config()
        if role in roles:
            return role
        return default
    except Exception as e:
        LOGGER.exception("Failed to get user role for %s: %s", user_id, e)
        return _get_role_permissions_config()[1]


def is_user_action_valid(event: dict, user_id: str | None = None) -> tuple[bool, str]:
    """
    Validate whether the user is authorized to perform the action (path + method).
    Uses role from DynamoDB users table (key "role"); default role is "reader".
    Returns (allowed: bool, error_message: str). If allowed, error_message is empty.
    """
    # API Gateway proxy: path is the actual request path (e.g. /users/abc-123)
    path = (event.get("path") or event.get("requestContext", {}).get("path") or event.get("resource") or "").strip()
    method = (event.get("httpMethod") or "").upper()
    authorizer = (event.get("requestContext") or {}).get("authorizer") or {}
    sub = user_id or authorizer.get("sub") or authorizer.get("principalId") or ""
    if not sub:
        return False, "Missing user identity (sub)"

    users_table = os.environ.get("usersStoreTable", "")
    role = _get_user_role(sub, users_table)
    roles_config, _ = _get_role_permissions_config()
    role_perms = roles_config.get(role, {})
    if not role_perms and role != "admin":
        LOGGER.warning("Unknown role or no permissions: %s", role)

    required = _get_required_permissions(path, method)
    if not required:
        # No rule: deny by default (or we could allow – safer to deny)
        return False, "No permission rule for this API"

    for perm in required:
        if not _role_has_permission(role_perms, perm):
            LOGGER.info("RBAC denied: user %s role %s lacks %s for %s %s", sub, role, perm, method, path)
            return False, f"Insufficient permission: requires {perm}"

    return True, ""

