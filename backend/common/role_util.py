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

_APIS_CONFIG: list | None = None
_ROLES_CONFIG: tuple[dict, str] | None = None
_SERVICES_CONFIG: dict | None = None
_TABLE_CACHE: dict[str, object] = {}


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
    global _APIS_CONFIG
    if _APIS_CONFIG is None:
        _APIS_CONFIG = _load_json("consolidated_api_permissions.json").get("apis", [])
    return _APIS_CONFIG


def _get_role_permissions_config() -> tuple:
    global _ROLES_CONFIG
    if _ROLES_CONFIG is None:
        data = _load_json("role_permissions.json")
        _ROLES_CONFIG = (data.get("roles", {}), data.get("default_role", "reader"))
    return _ROLES_CONFIG


def _get_service_level_config() -> dict:
    """Load service_level_permissions.json (services and their levels with dependencies)."""
    global _SERVICES_CONFIG
    if _SERVICES_CONFIG is None:
        data = _load_json("service_level_permissions.json")
        _SERVICES_CONFIG = data.get("services", {})
    return _SERVICES_CONFIG


def _users_table(users_table_name: str):
    table = _TABLE_CACHE.get(users_table_name)
    if table is None:
        table = boto3.resource("dynamodb").Table(users_table_name)
        _TABLE_CACHE[users_table_name] = table
    return table


def _get_dependencies_for_level(services_config: dict, service: str, level: str) -> list[str]:
    """
    Return the dependency list for a service.level from service_level_permissions.
    Supports both 'dependancies' and 'dependencies' keys.
    """
    level = (level or "").lower()
    svc = services_config.get(service) or {}
    level_config = svc.get(level) or {}
    deps = level_config.get("dependancies") or level_config.get("dependencies") or []
    return list(deps) if isinstance(deps, list) else []


def _expand_effective_permissions(role_permissions: dict) -> set[str]:
    """
    Expand role's service->level map into a set of effective permission strings,
    using dependencies from service_level_permissions.json (fullaccess -> manage, view; manage -> view).
    """
    services_config = _get_service_level_config()
    effective = set()
    for service, level in (role_permissions or {}).items():
        level = (level or "").lower()
        if not service or not level:
            continue
        # Add the direct action (e.g. posts.fullaccess)
        action = f"{service}.{level}"
        effective.add(action)
        # Recursively add dependencies
        to_process = [action]
        seen = {action}
        while to_process:
            current = to_process.pop()
            if "." not in current:
                continue
            svc, lv = current.split(".", 1)
            for dep in _get_dependencies_for_level(services_config, svc, lv):
                if dep and dep not in seen:
                    seen.add(dep)
                    effective.add(dep)
                    to_process.append(dep)
    return effective


# First URL segment for our routes (anything else is treated as API Gateway stage, e.g. /dev/users/...).
_API_ROOT_SEGMENTS = frozenset({"users", "posts", "auth"})


def _canonical_api_path(p: str) -> str:
    """Leading slash for comparison (API Gateway sometimes omits it on resource / resourcePath)."""
    s = (p or "").strip()
    if not s:
        return ""
    if not s.startswith("/"):
        s = "/" + s
    return s


def _strip_stage_prefix(path: str) -> str:
    """
    API Gateway often includes the stage as the first path segment (e.g. /dev/users/...).
    Strip it so normalization matches consolidated_api_permissions paths (/users/...).
    """
    if not path or not path.startswith("/"):
        return path
    parts = path.strip("/").split("/")
    if len(parts) >= 2 and parts[0] not in _API_ROOT_SEGMENTS:
        return "/" + "/".join(parts[1:])
    return path


def _strip_all_stage_prefixes(path: str) -> str:
    """Strip one or more stage-like leading segments (e.g. /dev/... or rare double prefixes)."""
    p = path or ""
    for _ in range(8):
        n = _strip_stage_prefix(p)
        if n == p:
            break
        p = n
    return p


def _normalize_path(path: str) -> str:
    """Convert request path to config path template, e.g. /users/abc-123 -> /users/{userId}."""
    path = _strip_all_stage_prefixes(path)
    path = _canonical_api_path(path)
    if not path or path == "/":
        return path
    parts = path.strip("/").split("/")
    if len(parts) == 1:
        return "/" + parts[0]
    if parts[0] == "users" and len(parts) == 2:
        return "/users/{userId}"
    if parts[0] == "users" and len(parts) == 3 and parts[2] == "role":
        return "/users/{userId}/role"
    if parts[0] == "posts" and len(parts) == 2:
        return "/posts/{postId}"
    return path


def _extract_http_method(event: dict) -> str:
    """REST proxy uses httpMethod; some clients / HTTP API v2 use other fields."""
    m = event.get("httpMethod")
    if m:
        return str(m).upper()
    rc = event.get("requestContext") or {}
    m = rc.get("httpMethod")
    if m:
        return str(m).upper()
    http = rc.get("http") or {}
    m = http.get("method")
    if m:
        return str(m).upper()
    rk = (event.get("routeKey") or "").strip()
    if rk and " " in rk:
        return rk.split(None, 1)[0].upper()
    return ""


def _permission_path_candidates(event: dict) -> list[str]:
    """
    Build paths that might match consolidated_api_permissions.json.
    Prefer API Gateway resource templates, then normalize raw paths (with stage stripped).
    """
    seen: set[str] = set()
    out: list[str] = []

    def add_template_or_raw(p: str) -> None:
        c = _canonical_api_path(p)
        if not c or c in seen:
            return
        seen.add(c)
        out.append(c)

    rc = event.get("requestContext") or {}
    add_template_or_raw(event.get("resource") or "")
    add_template_or_raw(rc.get("resourcePath") or "")

    for raw in (event.get("path"), rc.get("path"), event.get("rawPath")):
        if not raw:
            continue
        add_template_or_raw(_normalize_path(str(raw).strip()))

    return out


def _get_required_permissions_for_event(event: dict) -> list[str]:
    method = _extract_http_method(event)
    if not method:
        LOGGER.warning("RBAC: missing httpMethod (event keys=%s)", sorted(event.keys()))
        return []

    candidates = _permission_path_candidates(event)
    apis = _get_api_permissions_config()
    want_method = method.upper()

    for api in apis:
        if (api.get("method") or "").upper() != want_method:
            continue
        cfg_path = _canonical_api_path(api.get("path") or "")
        for cand in candidates:
            if cfg_path == _canonical_api_path(cand):
                return api.get("permissions", [])

    LOGGER.warning(
        "No API permission rule for method=%s candidates=%s (resource=%r path=%r resourcePath=%r)",
        method,
        candidates,
        event.get("resource"),
        event.get("path"),
        (event.get("requestContext") or {}).get("resourcePath"),
    )
    return []


def _role_has_permission(role_permissions: dict, required_permission: str) -> bool:
    """
    Check if role's permissions satisfy required permission using dependencies from
    service_level_permissions.json. Expands role's service->level into effective
    permissions (including dependancies), then checks if required is in that set.
    """
    if not required_permission or "." not in required_permission:
        return False
    effective = _expand_effective_permissions(role_permissions)
    return required_permission.strip().lower() in effective


def get_user_role(user_id: str, users_table_name: str) -> str:
    """Look up user in DynamoDB users table; return role field or default_role."""
    if not users_table_name or not user_id:
        return _get_role_permissions_config()[1]
    try:
        resp = _users_table(users_table_name).get_item(
            Key={"userId": user_id},
            ProjectionExpression="#role",
            ExpressionAttributeNames={"#role": "role"},
        )
        item = resp.get("Item") or {}
        role = (item.get("role") or "").strip().lower()
        roles, default = _get_role_permissions_config()
        if role in roles:
            return role
        return default
    except Exception as e:
        LOGGER.exception("Failed to get user role for %s: %s", user_id, e)
        return _get_role_permissions_config()[1]


# Backward-compatible alias for tests and internal callers.
_get_user_role = get_user_role


def resolve_user_role(event: dict, user_id: str | None = None) -> str:
    """
    Resolve application role for RBAC.
    Prefer role injected by the authorizer context; fall back to DynamoDB lookup.
    """
    authorizer = (event.get("requestContext") or {}).get("authorizer") or {}
    ctx_role = (authorizer.get("role") or "").strip().lower()
    roles, _default = _get_role_permissions_config()
    if ctx_role in roles:
        return ctx_role

    sub = user_id or authorizer.get("sub") or authorizer.get("principalId") or ""
    users_table = os.environ.get("usersStoreTable", "")
    return _get_user_role(sub, users_table)


def is_user_action_valid(event: dict, user_id: str | None = None) -> tuple[bool, str]:
    """
    Validate whether the user is authorized to perform the action (path + method).
    Uses role from DynamoDB users table (key "role"); default role is "reader".
    Returns (allowed: bool, error_message: str). If allowed, error_message is empty.
    """
    method = _extract_http_method(event)
    authorizer = (event.get("requestContext") or {}).get("authorizer") or {}
    sub = user_id or authorizer.get("sub") or authorizer.get("principalId") or ""
    if not sub:
        return False, "Missing user identity (sub)"

    role = resolve_user_role(event, user_id=sub)
    roles_config, _ = _get_role_permissions_config()
    role_perms = roles_config.get(role, {})
    if not role_perms and role != "admin":
        LOGGER.warning("Unknown role or no permissions: %s", role)

    required = _get_required_permissions_for_event(event)
    if not required:
        # No rule: deny by default (or we could allow – safer to deny)
        return False, "No permission rule for this API"

    for perm in required:
        if not _role_has_permission(role_perms, perm):
            LOGGER.info(
                "RBAC denied: user %s role %s lacks %s for %s path=%r resource=%r",
                sub,
                role,
                perm,
                method,
                event.get("path"),
                event.get("resource"),
            )
            return False, f"Insufficient permission: requires {perm}"

    return True, ""
