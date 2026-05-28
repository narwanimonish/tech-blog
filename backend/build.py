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

Authorizer-only pip deps (PyJWT) are installed into webservice/authorizer/
using manylinux2014_x86_64 wheels for AWS Lambda Python 3.12.
"""

import shutil
import subprocess
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent
COMMON = BACKEND_ROOT / "common"
CORE = BACKEND_ROOT / "core"
WEBSERVICE = BACKEND_ROOT / "webservice"
AUTHORIZER = WEBSERVICE / "authorizer"
LAYER_BUNDLE = BACKEND_ROOT / "layer_bundle"
PYTHON = LAYER_BUNDLE / "python"
LAMBDA_PYTHON_VERSION = "3.12"
LAMBDA_PLATFORM = "manylinux2014_x86_64"


def _clean_authorizer_vendor(authorizer_dir: Path) -> None:
    keep = {"runtime", "requirements.txt"}
    for item in authorizer_dir.iterdir():
        if item.name in keep:
            continue
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()


def _install_authorizer_dependencies() -> None:
    requirements = AUTHORIZER / "requirements.txt"
    if not requirements.is_file():
        return

    _clean_authorizer_vendor(AUTHORIZER)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-r",
            str(requirements),
            "-t",
            str(AUTHORIZER),
            "--upgrade",
            "--no-cache-dir",
            "--platform",
            LAMBDA_PLATFORM,
            "--python-version",
            LAMBDA_PYTHON_VERSION,
            "--implementation",
            "cp",
            "--only-binary",
            ":all:",
        ],
        check=True,
    )
    print(f"Installed authorizer deps for Lambda ({LAMBDA_PLATFORM}, cp{LAMBDA_PYTHON_VERSION})")


def main():
    if not COMMON.is_dir() or not CORE.is_dir():
        raise SystemExit("backend/common and backend/core must exist")

    if LAYER_BUNDLE.exists():
        shutil.rmtree(LAYER_BUNDLE)
    PYTHON.mkdir(parents=True)
    shutil.copytree(COMMON, PYTHON / "common", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copytree(CORE, PYTHON / "core", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    print("Built layer_bundle/python/{common,core}")

    _install_authorizer_dependencies()

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
