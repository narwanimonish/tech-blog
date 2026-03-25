#!/usr/bin/env python3
"""
Build script: creates the Lambda Layer bundle (common + core) so Lambdas
don't need a copy inside each webservice folder. Run from backend/.

  python build.py

Output: backend/layer_bundle/ with python/common and python/core.
Lambda Layer mounts this at /opt, so "from common import ..." and
"from core...." work in every function that has the layer attached.

Also removes any existing common/ and core/ from webservice/* so each
Lambda asset contains only the handler (runtime/).
"""

import shutil
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent
COMMON = BACKEND_ROOT / "common"
CORE = BACKEND_ROOT / "core"
WEBSERVICE = BACKEND_ROOT / "webservice"
LAYER_BUNDLE = BACKEND_ROOT / "layer_bundle"
PYTHON = LAYER_BUNDLE / "python"


def main():
    if not COMMON.is_dir() or not CORE.is_dir():
        raise SystemExit("backend/common and backend/core must exist")

    # Build layer: layer_bundle/python/common, layer_bundle/python/core
    if LAYER_BUNDLE.exists():
        shutil.rmtree(LAYER_BUNDLE)
    PYTHON.mkdir(parents=True)
    shutil.copytree(
        COMMON, PYTHON / "common", ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
    )
    shutil.copytree(
        CORE, PYTHON / "core", ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
    )
    print("Built layer_bundle/python/{common,core}")

    # Remove copied common/core from each webservice folder (they use the layer now)
    if WEBSERVICE.is_dir():
        for entry in WEBSERVICE.iterdir():
            if not entry.is_dir() or entry.name.startswith("_"):
                continue
            for name in ("common", "core"):
                dest_sub = entry / name
                if dest_sub.exists():
                    shutil.rmtree(dest_sub)
                    print(f"  Removed {entry.name}/{name}/")
    print("Done. Deploy with the layer attached; each Lambda needs only its runtime/.")


if __name__ == "__main__":
    main()
