"""
Load Lambda settings from backend/config.json.
Used by Lambda, API, and Auth stacks for timeout, memory_size, reserved_concurrency.
"""
from __future__ import annotations

import json
from pathlib import Path

# Repo root: from infrastructure/ go up one level
_REPO_ROOT = Path(__file__).resolve().parent.parent
_CONFIG_PATH = _REPO_ROOT / "backend" / "config.json"

_DEFAULTS = {
    "timeout": 30,
    "memory_size": 256,
    "reserved_concurrency": None,  # None = no limit
}


def load_lambda_config() -> dict:
    """Load full config dict from backend/config.json. Returns {} if file missing."""
    if not _CONFIG_PATH.is_file():
        return {}
    try:
        with open(_CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def get_lambda_settings(key: str) -> dict:
    """
    Get timeout, memory_size, reserved_concurrency for a Lambda key (e.g. users_api, authorizer).
    Returns dict with keys timeout (int), memory_size (int), reserved_concurrency (int | None).
    """
    config = load_lambda_config()
    raw = config.get(key, {})
    timeout = raw.get("timeout", _DEFAULTS["timeout"])
    memory_size = raw.get("memory_size", _DEFAULTS["memory_size"])
    reserved_concurrency = raw.get("reserved_concurrency")
    if reserved_concurrency is None and "reserved_concurrency" in raw:
        reserved_concurrency = raw["reserved_concurrency"]
    elif reserved_concurrency is None:
        reserved_concurrency = _DEFAULTS["reserved_concurrency"]
    return {
        "timeout_seconds": int(timeout),
        "memory_size": int(memory_size),
        "reserved_concurrent_executions": int(reserved_concurrency) if reserved_concurrency is not None else None,
    }
