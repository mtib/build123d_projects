"""Render slice/section PNGs of a model so it can be visually verified.

There is no bundled 3D viewer here, so the way to *look* at a model is to render
2D slices and open the PNGs. Use this after building any part:

    from viz import render_slices
    render_slices(part, "/tmp/pot", z_slices=[2, 10], angles=[0, 45])

Then open the PNGs (an image-capable reader / the Read tool) and check the
geometry matches intent — walls, floor, holes, and internal features should line
up and not collide. See the mandatory verification loop in CLAUDE.md.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless
import matplotlib.pyplot as plt  # noqa: E402

from build123d import Axis, Plane, Shape, Vector  # noqa: E402

_SAMPLES = 40  # points sampled per edge when drawing


def _edge_points(edge):
    return [edge.position_at(i / _SAMPLES) for i in range(_SAMPLES + 1)]


def _draw_faces_local(ax, faces, plane: Plane):
    """Draw section-face edges in the plane's local 2D coords."""
    for face in faces:
        for edge in face.edges():
            pts = [plane.to_local_coords(p) for p in _edge_points(edge)]
            ax.plot([p.X for p in pts], [p.Y for p in pts], "-", lw=0.8, color="k")


def _draw_projection(ax, shape: Shape, u: str, v: str):
    """Draw every edge of the shape projected onto two global axes (u, v)."""
    au, av = u.upper(), v.upper()
    for edge in shape.edges():
        pts = _edge_points(edge)
        ax.plot(
            [getattr(p, au) for p in pts],
            [getattr(p, av) for p in pts],
            "-",
            lw=0.5,
            color="k",
        )


def render_slices(
    part: Shape,
    out_prefix: str | Path,
    *,
    angles: list[float] | None = None,
    z_slices: list[float] | None = None,
) -> list[Path]:
    """Render vertical sections, horizontal slices and a top-down plan view.

    - ``angles``: vertical section planes rotated about Z (degrees).
    - ``z_slices``: horizontal section heights (mm).
    Returns the written PNG paths.
    """
    angles = angles if angles is not None else [0.0]
    z_slices = z_slices if z_slices is not None else []
    out_prefix = Path(out_prefix)
    out_prefix.parent.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    # Vertical sections (profile views).
    for ang in angles:
        plane = Plane.XZ.rotated((0, 0, ang))
        faces = part.intersect(plane)
        fig, ax = plt.subplots(figsize=(5, 5))
        _draw_faces_local(ax, faces.faces(), plane)
        ax.set_aspect("equal")
        ax.set_title(f"vertical section @ {ang:g}°")
        ax.grid(True, lw=0.3, alpha=0.5)
        path = out_prefix.with_name(f"{out_prefix.name}_sec{int(ang)}.png")
        fig.savefig(path, dpi=130, bbox_inches="tight")
        plt.close(fig)
        written.append(path)

    # Horizontal slices (plan views at a height).
    for z in z_slices:
        plane = Plane.XY.offset(z)
        faces = part.intersect(plane)
        fig, ax = plt.subplots(figsize=(5, 5))
        _draw_faces_local(ax, faces.faces(), plane)
        ax.set_aspect("equal")
        ax.set_title(f"horizontal slice @ z={z:g}mm")
        ax.grid(True, lw=0.3, alpha=0.5)
        path = out_prefix.with_name(f"{out_prefix.name}_z{int(z)}.png")
        fig.savefig(path, dpi=130, bbox_inches="tight")
        plt.close(fig)
        written.append(path)

    # Top-down projection of all edges (reveals plan-view collisions/alignment).
    fig, ax = plt.subplots(figsize=(5, 5))
    _draw_projection(ax, part, "x", "y")
    ax.set_aspect("equal")
    ax.set_title("top-down projection (all edges)")
    ax.grid(True, lw=0.3, alpha=0.5)
    path = out_prefix.with_name(f"{out_prefix.name}_top.png")
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    written.append(path)

    return written
