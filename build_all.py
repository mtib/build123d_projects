#!/usr/bin/env python
"""Build build123d projects and export their STLs.

Usage
-----
    python build_all.py                    # build every project under projects/
    python build_all.py flowerpot          # build only the named project(s)
    python build_all.py --hero             # + render a hero PNG per model
    python build_all.py --views            # + write inspection slice renders
    python build_all.py --dist dist        # + collect release assets into dist/
    python build_all.py --list             # list discoverable projects

Each project is a folder ``projects/<name>/`` containing a ``build.py`` that
defines ``build() -> dict[str, Shape]``. STLs are written to
``projects/<name>/exports/<key>.stl``.

Naming: exported STLs use the raw variant key (``9cm.stl``). The globally-unique
release name ``<project>_<key>.stl`` is applied only when collecting into a dist
directory (``--dist``), which is what CI uploads to a release. Doing the prefix
at the collection boundary keeps it path-derived and lets us fail loudly on any
name collision instead of silently overwriting.

Hero renders (``--hero``): renders one showcase PNG per model named exactly like
its STL (``<key>.png`` beside ``<key>.stl``). Unlike the slice views, hero PNGs
ARE collected by ``--dist`` and uploaded to the release (``<project>_<key>.png``).
A project sets its own viewpoint via ``HERO = {"elev": .., "azim": ..}``.

Inspection views (``--views``): renders cross-sections + a top projection next
to the STLs (``projects/<name>/exports/<key>_*.png``) so you can eyeball each
model and spot regressions. Requires matplotlib (requirements-dev.txt). These
slice PNGs live under the gitignored ``exports/`` and are never collected into a
release — they are a local verification aid only.

This is the entrypoint CI runs to regenerate every model:

    python -m venv .venv && . .venv/bin/activate
    pip install -r requirements.txt
    python build_all.py --dist dist
"""

from __future__ import annotations

import argparse
import importlib.util
import shutil
import sys
import time
from pathlib import Path

from pipeline import export_parts

REPO_ROOT = Path(__file__).resolve().parent
PROJECTS_DIR = REPO_ROOT / "projects"

# Fallback inspection views for projects that don't declare their own VIEWS.
DEFAULT_VIEW_ANGLES = [0.0, 45.0, 90.0]


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


def _render_views(module, parts: dict, out_dir: Path) -> list[Path]:
    """Render inspection PNGs for each part next to the STLs.

    A project may declare ``VIEWS = {"angles": [...], "z_slices": [...]}`` in its
    build.py to target its notable features; otherwise generic sections and
    height-based slices are used.
    """
    from viz import render_slices  # lazy import: matplotlib is a dev-only dep

    spec = getattr(module, "VIEWS", None) or {}
    angles = spec.get("angles", DEFAULT_VIEW_ANGLES)
    written: list[Path] = []
    for key, part in parts.items():
        z_slices = spec.get("z_slices")
        if z_slices is None:  # default: quarter/half/three-quarter height
            bb = part.bounding_box()
            lo, hi = bb.min.Z, bb.max.Z
            z_slices = [round(lo + f * (hi - lo), 2) for f in (0.25, 0.5, 0.75)]
        written += render_slices(part, out_dir / key, angles=angles, z_slices=z_slices)
    return written


def _render_heroes(module, parts: dict, out_dir: Path) -> list[Path]:
    """Render a hero PNG per part as ``<key>.png`` (sibling of ``<key>.stl``).

    A project may declare ``HERO = {"elev": .., "azim": .., "tolerance": ..}`` in
    its build.py to set a per-model viewpoint; otherwise the defaults are used.
    """
    from viz import render_hero  # lazy import: matplotlib is a dev-only dep

    spec = getattr(module, "HERO", None) or {}
    return [render_hero(part, out_dir / f"{key}.png", **spec) for key, part in parts.items()]


def build_project(
    name: str, *, render_views: bool = False, render_hero: bool = False
) -> tuple[list[Path], list[Path]]:
    """Build a single project; return (stl_paths, png_paths)."""
    module = _load_build(name)
    if not hasattr(module, "build"):
        raise AttributeError(f"projects/{name}/build.py must define build()")
    parts = module.build()
    out_dir = PROJECTS_DIR / name / "exports"
    # Clear stale STLs so a renamed/removed variant can't linger into a release.
    if out_dir.is_dir():
        for old in out_dir.glob("*.stl"):
            old.unlink()
    stls = export_parts(parts, out_dir)
    pngs: list[Path] = []
    if render_hero:
        pngs += _render_heroes(module, parts, out_dir)
    if render_views:
        pngs += _render_views(module, parts, out_dir)
    return stls, pngs


def collect_dist(projects: list[str], dist_dir: Path | str) -> list[Path]:
    """Copy each project's STLs into dist_dir as ``<project>_<file>``.

    The project prefix is derived from the directory here (not trusted from the
    filename), and any resulting name collision is a hard error rather than a
    silent overwrite.
    """
    dist = Path(dist_dir)
    dist.mkdir(parents=True, exist_ok=True)
    seen: dict[str, Path] = {}
    written: list[Path] = []
    for name in projects:
        exports = PROJECTS_DIR / name / "exports"
        if not exports.is_dir():
            continue
        for stl in sorted(exports.glob("*.stl")):
            # Ship the STL and, if present, its hero render (<key>.png). The
            # slice views (<key>_*.png) are deliberately not collected.
            sources = [stl]
            hero = stl.with_suffix(".png")
            if hero.exists():
                sources.append(hero)
            for src in sources:
                asset = f"{name}_{src.name}"
                if asset in seen:
                    raise SystemExit(
                        f"release asset name collision: '{asset}' produced by both "
                        f"{seen[asset]} and {src}"
                    )
                seen[asset] = src
                target = dist / asset
                shutil.copy2(src, target)
                written.append(target)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("projects", nargs="*", help="project name(s); default: all")
    parser.add_argument("--list", action="store_true", help="list projects and exit")
    parser.add_argument(
        "--views",
        action="store_true",
        help="render inspection slice PNGs next to the STLs (needs matplotlib)",
    )
    parser.add_argument(
        "--hero",
        action="store_true",
        help="render a hero PNG (<key>.png) per model; collected into the release",
    )
    parser.add_argument(
        "--dist",
        metavar="DIR",
        help="collect built STLs into DIR as <project>_<file>.stl (for release)",
    )
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
    built_ok: list[str] = []
    for name in targets:
        start = time.perf_counter()
        try:
            stls, pngs = build_project(
                name, render_views=args.views, render_hero=args.hero
            )
        except Exception as exc:  # keep building other projects
            print(f"[FAIL] {name}: {exc}", file=sys.stderr)
            exit_code = 1
            continue
        built_ok.append(name)
        elapsed = time.perf_counter() - start
        extra = f", {len(pngs)} render(s)" if pngs else ""
        print(f"[ok]   {name}: {len(stls)} STL(s){extra} in {elapsed:.1f}s")
        for f in stls:
            print(f"         -> {f.relative_to(REPO_ROOT)}")

    if args.dist and built_ok:
        assets = collect_dist(built_ok, args.dist)
        print(f"[dist] {len(assets)} asset(s) collected into {args.dist}/")
        for f in assets:
            print(f"         -> {f.name}")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
