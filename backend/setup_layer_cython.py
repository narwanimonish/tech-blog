#!/usr/bin/env python3
"""
Compile common/ and core/ modules in the current directory (layer_bundle/python).

Run from layer_bundle/python after sources are copied:

  python ../../setup_layer_cython.py
"""

from __future__ import annotations

from pathlib import Path

from Cython.Build import cythonize
from setuptools import Extension, setup

ROOT = Path(".").resolve()
PACKAGES = ("common", "core")


def discover_extensions() -> list[Extension]:
    extensions: list[Extension] = []
    for pkg in PACKAGES:
        pkg_dir = ROOT / pkg
        if not pkg_dir.is_dir():
            continue
        for py_file in sorted(pkg_dir.rglob("*.py")):
            if py_file.name == "__init__.py":
                continue
            rel = py_file.relative_to(ROOT).with_suffix("")
            module = ".".join(rel.parts)
            extensions.append(Extension(module, [str(py_file)]))
    return extensions


def main() -> None:
    extensions = discover_extensions()
    if not extensions:
        raise SystemExit("No common/core modules found to cythonize")

    setup(
        ext_modules=cythonize(
            extensions,
            compiler_directives={
                "language_level": "3",
                "boundscheck": False,
                "wraparound": False,
            },
        ),
        script_args=["build_ext", "--inplace"],
    )


if __name__ == "__main__":
    main()
