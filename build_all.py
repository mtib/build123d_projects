#!/usr/bin/env python
"""Build build123d projects and export their STLs.

Usage
-----
    python build_all.py                # build every project under projects/
    python build_all.py flowerpot      # build only the named project(s)
    python build_all.py --list         # list discoverable projects

Each project is a folder ``projects/<name>/`` containing a ``build.py`` that
defines ``build() -> dict[str, Shape]``. STLs are written to
``projects/<name>/exports/<stem>.stl``.

This is the entrypoint CI (or a fresh machine) runs to regenerate every model:

    python -m venv .venv && . .venv/bin/activate
    pip install -r requirements.txt
    python build_all.py
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
import time
from pathlib import Path

from pipeline import export_parts

REPO_ROOT = Path(__file__).resolve().parent
PROJECTS_DIR = REPO_ROOT / "projects"


def discover_projects() -> list[str]:
    """Return the names of all projects that have a build.py, sorted."""
    if not PROJECTS_DIR.is_dir():
        return []
    return sorted(
        p.name
        for p in PROJECTS_DIR.iterdir()
        if p.is_dir() and (p / "build.py").is_file()
    )


def _load_build(name: str):
    """Load projects/<name>/build.py as a standalone module (no package import)."""
    build_py = PROJECTS_DIR / name / "build.py"
    spec = importlib.util.spec_from_file_location(f"projects.{name}.build", build_py)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {build_py}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_project(name: str) -> list[Path]:
    """Build a single project and export its STLs; return written paths."""
    module = _load_build(name)
    if not hasattr(module, "build"):
        raise AttributeError(f"projects/{name}/build.py must define build()")
    parts = module.build()
    out_dir = PROJECTS_DIR / name / "exports"
    # Prefix with the project name so files are <project>_<name>.stl.
    return export_parts(parts, out_dir, prefix=f"{name}_")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("projects", nargs="*", help="project name(s); default: all")
    parser.add_argument("--list", action="store_true", help="list projects and exit")
    args = parser.parse_args(argv)

    available = discover_projects()

    if args.list:
        for name in available:
            print(name)
        return 0

    targets = args.projects or available
    if not targets:
        print("No projects found under projects/.", file=sys.stderr)
        return 0

    unknown = [t for t in targets if t not in available]
    if unknown:
        print(f"Unknown project(s): {', '.join(unknown)}", file=sys.stderr)
        print(f"Available: {', '.join(available) or '(none)'}", file=sys.stderr)
        return 1

    exit_code = 0
    for name in targets:
        start = time.perf_counter()
        try:
            files = build_project(name)
        except Exception as exc:  # keep building other projects
            print(f"[FAIL] {name}: {exc}", file=sys.stderr)
            exit_code = 1
            continue
        elapsed = time.perf_counter() - start
        print(f"[ok]   {name}: {len(files)} STL(s) in {elapsed:.1f}s")
        for f in files:
            print(f"         -> {f.relative_to(REPO_ROOT)}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
