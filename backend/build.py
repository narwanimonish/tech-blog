#!/usr/bin/env python3
"""
Build script: copies common/ and core/ into each webservice/<name>/ package
so each Lambda deployment has handler + dependencies. Run from backend/.
"""
import os
import shutil
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent
COMMON = BACKEND_ROOT / "common"
CORE = BACKEND_ROOT / "core"
WEBSERVICE = BACKEND_ROOT / "webservice"


def main():
    if not COMMON.is_dir() or not CORE.is_dir() or not WEBSERVICE.is_dir():
        raise SystemExit("backend/common, backend/core, and backend/webservice must exist")

    for entry in WEBSERVICE.iterdir():
        if not entry.is_dir():
            continue
        # Skip __pycache__ etc.
        if entry.name.startswith("_"):
            continue
        dest = entry
        for name, src_dir in [("common", COMMON), ("core", CORE)]:
            dest_sub = dest / name
            if dest_sub.exists():
                shutil.rmtree(dest_sub)
            shutil.copytree(src_dir, dest_sub, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            print(f"  {dest.name}: copied {name}/")

    print("Build done.")


if __name__ == "__main__":
    main()
