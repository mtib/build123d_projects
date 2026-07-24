# build123d workspace

A workspace for parametric CAD models built with
[build123d](https://github.com/gumyr/build123d). Each model is a small Python
project that emits **STL files for 3D printing**.

---

## 1. Environment

A virtualenv lives in `.venv/` (Python 3.12, `build123d==0.11.1`). It is
**gitignored** — recreate it on a fresh machine, don't commit it.

### Use the existing venv

```bash
# activate (zsh/bash)
source .venv/bin/activate
python build_all.py            # now on PATH

# …or without activating, call the interpreter directly:
.venv/bin/python build_all.py
```

When running one-off Python for build123d, always use `.venv/bin/python` (or an
activated shell) — the system Python does **not** have build123d, and the
current system default (Python 3.14) has no `cadquery-ocp` wheels yet, which is
why the venv is pinned to 3.12.

### Recreate from scratch (fresh machine / CI)

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python build_all.py
```

---

## 2. Repository layout

```
build123d/
├── .venv/                  # virtualenv (gitignored)
├── requirements.txt        # pinned deps (build123d==0.11.1)
├── build_all.py            # entrypoint: build one / all projects → STL
├── pipeline.py             # shared export helper (export_parts)
├── CLAUDE.md               # this file
└── projects/
    └── <name>/
        ├── build.py        # defines build() -> dict[str, Shape]
        └── exports/        # generated STLs (gitignored)
```

### The project contract

Every project is a folder `projects/<name>/` containing a `build.py` that
defines a single function:

```python
def build() -> dict[str, Shape]:
    """Return {output_file_stem: build123d shape}."""
```

- The **keys** become STL filenames (`{stem}.stl`).
- The **values** are build123d shapes (`Part`, `Solid`, `Compound`, `Sketch`…).
- Keep `build.py` importable with **no side effects at import time** — all work
  happens inside `build()`. The entrypoint loads the module and calls `build()`;
  it does not run any `__main__` block.

`pipeline.py` handles export (STL tessellation tolerance 0.05 mm / 0.1 rad — a
good FDM/resin balance). Change those defaults there if a model needs finer
detail.

### Building

`build_all.py` is the only entrypoint (this is what CI runs):

```bash
python build_all.py            # build EVERY project → projects/*/exports/*.stl
python build_all.py flowerpot  # build ONE project (the usual dev loop)
python build_all.py a b c      # build several
python build_all.py --list     # list discoverable projects
```

A failure in one project is reported but does not stop the others; the process
exits non-zero if any project failed (good for CI).

### Adding a new project

1. `mkdir projects/<name>`
2. Write `projects/<name>/build.py` with a `build()` function.
3. `python build_all.py <name>` and inspect `projects/<name>/exports/`.

No registration step — `build_all.py` discovers any folder with a `build.py`.

---

## 3. build123d primer

build123d is a Python CAD library (successor in spirit to CadQuery) built on the
OpenCascade kernel. You describe solids in code; it produces B-rep geometry you
can export to STL/STEP/etc.

**Units:** the default length unit is the **millimetre**. Angles are in
**degrees**. STL output is unitless numbers → slicers read them as mm, so keep
everything in mm.

### Two API styles

build123d offers two equivalent styles. You can mix them.

**Builder mode** — context managers (`with`) collect objects onto an implicit
stack. Reads top-to-bottom like a machining process. Good for parts built by
sequential feature operations.

```python
from build123d import *

length, width, thickness = 80.0, 60.0, 10.0

with BuildPart() as ex:
    Box(length, width, thickness)                       # add a solid
    Cylinder(radius=11, height=thickness, mode=Mode.SUBTRACT)  # drill a hole
    fillet(ex.edges().filter_by(Axis.Z), radius=3)      # round vertical edges

part = ex.part          # the resulting Part
```

**Algebra mode** — objects are plain values combined with operators. More
functional; good for concise parametric definitions.

```python
from build123d import *

part = Box(80, 60, 10) - Cylinder(radius=11, height=10)   # subtract
part = Box(10, 10, 10) + Pos(0, 0, 10) * Sphere(5)        # union at a location
part = Box(10, 10, 10) & Sphere(7)                        # intersection
```

Operator cheat sheet (algebra mode):

| Operator | Meaning              | Builder-mode equivalent |
|----------|----------------------|-------------------------|
| `+`      | union / add          | `Mode.ADD`              |
| `-`      | cut / subtract       | `Mode.SUBTRACT`         |
| `&`      | intersect            | `Mode.INTERSECT`        |
| `*`      | place at a Location  | (workplane / `Locations`) |

`Pos(x, y, z)` is a translation Location; `Rot(x, y, z)` is a rotation (degrees);
a `Plane` (e.g. `Plane.XY`, `Plane.top`) can also be used on the left of `*` to
place an object on that plane.

### The three builders

- **`BuildLine`** — 1D: build wires/edges (`Line`, `Polyline`, `Spline`,
  `RadiusArc`, `CenterArc`, …). Usually nested inside a `BuildSketch`.
- **`BuildSketch`** — 2D: build faces on a workplane (`Circle`, `Rectangle`,
  `RegularPolygon`, `Text`, `Trapezoid`, …), or `make_face()` from a BuildLine.
- **`BuildPart`** — 3D: primitives (`Box`, `Cylinder`, `Sphere`, `Cone`,
  `Torus`, `Wedge`) and operations that turn sketches into solids.

Typical flow: draw a profile in `BuildSketch`, then `extrude`/`revolve`/`loft`
it into 3D inside `BuildPart`.

### Common objects

- **1D:** `Line`, `Polyline`, `Spline`, `RadiusArc`, `CenterArc`, `EllipseArc`,
  `Bezier`, `JernArc`.
- **2D:** `Circle`, `Ellipse`, `Rectangle`, `RectangleRounded`, `RegularPolygon`,
  `Polygon`, `Trapezoid`, `SlotOverall`, `Text`.
- **3D:** `Box`, `Cylinder`, `Sphere`, `Cone`, `Torus`, `Wedge`.

### Common operations

- **Make 3D from 2D:** `extrude(amount=..., taper=...)`, `revolve(axis=..., revolution_arc=...)`,
  `loft(sections)`, `sweep(path=...)`.
- **Edge treatments:** `fillet(edges, radius=...)`, `chamfer(edges, length=...)`.
- **Shells/walls:** `offset(obj, amount=..., openings=...)` — negative `amount`
  hollows a solid; pass `openings=<face>` to leave that face open (make a cup).
- **Booleans:** `add`, `subtract`, `intersect` (or `+ - &` in algebra mode, or
  the `mode=` kwarg on any object in builder mode).
- **Other:** `mirror(obj, about=Plane.XZ)`, `split(obj, bisect_by=..., keep=...)`,
  `scale`, `project`, `thicken`.

### Enums you'll use constantly

- **`Mode`**: `ADD`, `SUBTRACT`, `INTERSECT`, `REPLACE`, `PRIVATE` — what an
  object/operation does to the active builder context.
- **`Align`**: `MIN`, `CENTER`, `MAX`, `NONE` — how an object is positioned
  relative to its origin per axis. E.g. a `Cylinder(..., align=(Align.CENTER,
  Align.CENTER, Align.MIN))` sits on top of the workplane instead of straddling it.
- **`Keep`**: `TOP`, `BOTTOM`, `BOTH`, `INSIDE`, `OUTSIDE`, `ALL` — for `split`.
- **`Kind`** (`ARC`/`INTERSECTION`/`TANGENT`) and **`Side`** — for `offset`.
- **`SortBy`** (`LENGTH`/`RADIUS`/`AREA`/`VOLUME`/`DISTANCE`) — for selectors.

### Selectors (picking edges/faces to fillet, cut, etc.)

From any shape or builder: `.vertices()`, `.edges()`, `.wires()`, `.faces()`,
`.solids()`. Refine with:

- `.filter_by(Axis.Z)` / `.filter_by(GeomType.CIRCLE)` / `.filter_by(lambda f: ...)`
- Sorting/grouping operators: `>` `<` (sort by axis), `>>` `<<` (group by axis),
  `|` (filter by axis/plane/type), `[i]` (index).
- `.sort_by(SortBy.AREA)`, `.group_by(Axis.Z)`.

Examples:

```python
ex.faces().sort_by(Axis.Z)[-1]          # topmost face
ex.edges().filter_by(Axis.Z)            # all vertical edges
ex.faces().filter_by(GeomType.PLANE)    # flat faces only
ex.edges().group_by(Axis.Z)[0]          # edges at the lowest Z
```

### Locations, planes, workplanes

- A **`Location`** = position + orientation. Objects have `.location`,
  `.position`, `.orientation`. Methods: `move`/`moved` (relative),
  `locate`/`located` (absolute).
- **`Plane`**: `Plane.XY`, `Plane.XZ`, `Plane.YZ`, or derive one from a face:
  `Plane(part.faces().sort_by(Axis.Z)[-1])`. In algebra mode, `plane * obj`
  places `obj` on that plane.
- In builder mode, pass planes to a builder (`with BuildSketch(Plane.XZ):`) or
  use `with Locations((x,y,z), ...):` / `with GridLocations(...):` /
  `with PolarLocations(r, n):` to stamp copies of the next object at several
  spots.

### Export

`pipeline.export_parts()` wraps these, but the raw functions are:

- `export_stl(shape, "file.stl", tolerance=0.05, angular_tolerance=0.1)` — **the
  one we use** for print output.
- `export_step(shape, "file.step")` — parametric-friendly exchange format.
- Also available: `export_brep`, `export_gltf`, `ExportSVG`, `ExportDXF`, and
  the matching `import_*` functions.

### Inspecting / debugging models

```bash
.venv/bin/python -c "
from build123d import *
b = Box(10,10,10) - Cylinder(radius=3, height=10)
print('volume', b.volume)
print('bbox', b.bounding_box())
print('is_valid', b.is_valid())     # sanity-check the B-rep
"
```

`shape.show_topology()` prints the vertex/edge/face tree. There is no bundled
GUI viewer here; verify via `.volume`, `.bounding_box()`, `.is_valid()`, and by
opening the exported STL in a slicer.

### Design principle: prefer easy-to-print models

**Default to designs that print with no support on a bog-standard FDM printer.**
This is a standing preference for every model in this repo — bias toward
printability even at some cost to form:

- **Flat base on the bed.** Give the model a flat bottom so it adheres well and
  needs no raft/support. Avoid raised feet that enclose a flat ceiling
  underneath — that ceiling becomes a long unsupported bridge. Fake feet with
  arched/notched cutouts in a flush base instead.
- **Self-supporting overhangs (≤ ~45° from vertical).** Mild outward wall taper
  is fine. For openings, prefer **arches/teardrops/chamfers** over flat
  horizontal bridges (a round side-hole self-supports its top half).
- **No islands / no floating overhangs** that would need support material.
- **Walls ≥ ~2 mm**, small holes (≤ ~8 mm) bridge fine, orient the model in its
  intended print pose (the STL bakes orientation in).
- When a requested feature can't be printed cleanly without support, adapt it to
  a support-free equivalent and note the trade-off — don't silently emit an
  unprintable model.

### 3D-printing gotchas

- **Manifold & watertight:** exported solids must be closed. Prefer building one
  clean `Solid`/`Part`; check `shape.is_valid()`.
- **Wall thickness:** keep walls ≥ ~2 mm (≥ ~3 perimeters) for strength; thin
  walls print poorly.
- **Overhangs/drainage holes:** holes/bridges over ~45° from vertical may need
  support. Small holes (≤ ~8 mm) usually bridge fine.
- **Orientation is baked into the STL** — model with the intended print
  orientation (e.g. a pot printed open-side-up needs no support for its walls).
```
