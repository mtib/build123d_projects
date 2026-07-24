"""Shared helpers for build123d projects in this repo.

Every project under ``projects/<name>/`` exposes a ``build()`` function in its
``build.py`` that returns a ``dict[str, Shape]`` mapping an output file stem to a
build123d shape (``Part``/``Solid``/``Compound``/etc.). This module knows how to
turn that dict into STL files on disk.

All build123d dimensions in this repo are in **millimetres** (the library's
default unit), which is also what slicers expect from an STL.
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from build123d import Shape, export_stl

# STL tessellation quality. These control the max deviation (mm) and angle (rad)
# between the true surface and the triangle mesh. 0.05 mm / ~5.7 deg is a good
# balance for FDM/resin prints: smooth curves without absurd file sizes.
STL_TOLERANCE = 0.05
STL_ANGULAR_TOLERANCE = 0.1


def export_parts(
    parts: Mapping[str, Shape],
    out_dir: Path | str,
    *,
    tolerance: float = STL_TOLERANCE,
    angular_tolerance: float = STL_ANGULAR_TOLERANCE,
) -> list[Path]:
    """Export each shape in ``parts`` to ``out_dir/<stem>.stl``.

    Files are named by the raw variant key (``9cm.stl``). The ``<project>_``
    prefix that makes release assets globally unique is added later, at the
    release-collection boundary (see ``build_all.collect_dist``). Returns the
    list of written file paths.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for stem, shape in parts.items():
        path = out_dir / f"{stem}.stl"
        export_stl(
            shape,
            str(path),
            tolerance=tolerance,
            angular_tolerance=angular_tolerance,
        )
        written.append(path)
    return written
