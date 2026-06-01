#!/usr/bin/env python3
"""
Build script: creates the Lambda Layer bundle (common + core) so Lambdas
don't need a copy inside each webservice folder. Run from backend/.

  python build.py
  CYTHONIZE=1 python build.py    # compile common/core to native extensions (Lambda Linux)

Output: backend/layer_bundle/ with python/common and python/core.
Lambda Layer mounts this at /opt, so "from common import ..." and
"from core...." work in every function that has the layer attached.

Also removes any existing common/ and core/ from webservice/* so each
Lambda asset contains only the handler (runtime/).

Authorizer-only pip deps (PyJWT) are installed into webservice/authorizer/
using manylinux2014_x86_64 wheels for AWS Lambda Python 3.12.

Cython notes:
- Set CYTHONIZE=1 to compile shared logic to .so for faster cold-start imports.
- Requires Linux Python 3.12 (matches Lambda) or Docker (public.ecr.aws/lambda/python:3.12).
- Unit tests always run against backend/common and backend/core sources, not the layer.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent
SETUP_CYTHON = BACKEND_ROOT / "setup_layer_cython.py"
COMMON = BACKEND_ROOT / "common"
CORE = BACKEND_ROOT / "core"
WEBSERVICE = BACKEND_ROOT / "webservice"
AUTHORIZER = WEBSERVICE / "authorizer"
LAYER_BUNDLE = BACKEND_ROOT / "layer_bundle"
PYTHON = LAYER_BUNDLE / "python"
LAMBDA_PYTHON_VERSION = "3.12"
LAMBDA_PLATFORM = "manylinux2014_x86_64"
LAMBDA_DOCKER_IMAGE = "public.ecr.aws/lambda/python:3.12"
FORBIDDEN_LAYER_ROOT = {"jwt", "cryptography", "cffi", "pycparser", "_cffi_backend"}


def _cythonize_enabled() -> bool:
    return os.environ.get("CYTHONIZE", "").strip().lower() in {"1", "true", "yes", "on"}


def _can_compile_inplace() -> bool:
    return sys.platform.startswith("linux") and sys.version_info[:2] == (3, 12)


def _docker_available() -> bool:
    return shutil.which("docker") is not None


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


def _remove_generated_cython_artifacts(python_dir: Path) -> None:
    for pattern in ("*.c", "*.cpp"):
        for path in python_dir.rglob(pattern):
            path.unlink(missing_ok=True)

    for pkg in ("common", "core"):
        pkg_dir = python_dir / pkg
        if not pkg_dir.is_dir():
            continue
        for py_file in pkg_dir.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue
            stem = py_file.stem
            if any(stem in shared.name for shared in py_file.parent.glob(f"{stem}*.so")):
                py_file.unlink()


def _run_cython_compile(python_dir: Path) -> None:
    subprocess.run(
        [sys.executable, str(SETUP_CYTHON)],
        cwd=python_dir,
        check=True,
    )
    _remove_generated_cython_artifacts(python_dir)


def _run_cython_compile_docker(python_dir: Path) -> None:
    python_dir = python_dir.resolve()
    setup_script = SETUP_CYTHON.resolve()
    subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--platform",
            "linux/amd64",
            "--entrypoint",
            "/bin/bash",
            "-v",
            f"{python_dir}:/var/task/layer/python",
            "-v",
            f"{setup_script}:/var/task/setup_layer_cython.py:ro",
            LAMBDA_DOCKER_IMAGE,
            "-lc",
            "pip install -q 'cython>=3.0.12,<4' 'PyJWT[crypto]>=2.8.0,<3' && "
            "cd /var/task/layer/python && python /var/task/setup_layer_cython.py",
        ],
        check=True,
    )
    _remove_generated_cython_artifacts(python_dir)


def _cythonize_layer_bundle() -> None:
    if not _cythonize_enabled():
        return

    if not SETUP_CYTHON.is_file():
        raise SystemExit(f"Missing {SETUP_CYTHON}")

    print("Cythonizing layer_bundle/python/{{common,core}} for Lambda...")
    if _can_compile_inplace():
        _run_cython_compile(PYTHON)
    elif _docker_available():
        _run_cython_compile_docker(PYTHON)
    else:
        raise SystemExit(
            f"CYTHONIZE=1 requires Linux Python 3.12 or Docker ({LAMBDA_DOCKER_IMAGE}) to build Lambda-compatible extensions."
        )

    compiled = list(PYTHON.rglob("*.so"))
    if not compiled:
        raise SystemExit("Cython build produced no .so files in layer_bundle")
    print(f"  Compiled {len(compiled)} extension(s)")


def _verify_layer_bundle(*, cythonized: bool) -> None:
    for name in FORBIDDEN_LAYER_ROOT:
        path = PYTHON / name
        if path.exists():
            raise SystemExit(f"layer_bundle must not contain {name!r} (authorizer deps belong in webservice/authorizer/)")

    for shared_object in PYTHON.rglob("*.so"):
        rel_parts = shared_object.relative_to(PYTHON).parts
        if cythonized:
            if not rel_parts or rel_parts[0] not in {"common", "core"}:
                raise SystemExit(f"Unexpected native library in layer_bundle: {shared_object}")
        else:
            raise SystemExit(f"layer_bundle must not contain native libraries: {shared_object}")


def main() -> None:
    if not COMMON.is_dir() or not CORE.is_dir():
        raise SystemExit("backend/common and backend/core must exist")

    cythonized = _cythonize_enabled()

    if LAYER_BUNDLE.exists():
        shutil.rmtree(LAYER_BUNDLE)
    PYTHON.mkdir(parents=True)
    shutil.copytree(COMMON, PYTHON / "common", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copytree(CORE, PYTHON / "core", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

    _cythonize_layer_bundle()
    cythonized = cythonized or any(PYTHON.rglob("*.so"))

    _verify_layer_bundle(cythonized=cythonized)
    mode = "cythonized common/core" if cythonized else "{common,core}"
    print(f"Built layer_bundle/python/{mode}")

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
