"""Draining outer flower pot ("Übertopf") for standard tapered nursery pots.

A printed OUTER pot that a standard plastic nursery pot of 9/10/11 cm top
diameter drops into. The nursery pot rests on internal bosses that keep its
base off the floor, leaving a drainage plenum. Water leaves through a ring of
holes in the floor and through round side vents just above the floor.

Print orientation: open side UP, flat base on the bed. Support-free by design
(see the easy-to-print principle in the repo CLAUDE.md):

- the base is a flush solid ring -> sticks to the bed, no raft/support;
- walls taper gently outward (~9deg), which is self-supporting;
- the side vents are round holes sitting ABOVE the floor slab, so their tops
  self-support as arches and they never undercut the base;
- internal bosses are interleaved between the drain holes so nothing overlaps.
"""

from __future__ import annotations

from build123d import (
    Align,
    Axis,
    Circle,
    Cylinder,
    GeomType,
    Part,
    Plane,
    Pos,
    Rot,
    Shape,
    fillet,
    loft,
)

# --- fixed design parameters (mm) -------------------------------------------
GAP = 3.0        # radial clearance between nursery pot and inner wall
WALL = 3.5       # side wall thickness
FLOOR = 4.0      # floor thickness
BOSS_H = 8.0     # height of the bosses the nursery pot rests on (drainage gap)
COVER = 0.90     # fraction of nursery-pot height the outer wall covers

DRAIN_R = 3.5    # radius of the floor drain holes
DRAIN_RING_N = 6 # number of holes in the ring (plus one in the centre)

VENT_R = 4.5     # radius of the round side vents
VENT_N = 4       # number of side vents

BOSS_R = 4.0     # radius of the nursery-pot support bosses
BOSS_N = 3       # number of support bosses (interleaved between drain holes)
RIM_FILLET = 1.2 # top-rim rounding

# Inspection views for `build_all --views`: cut through a drain hole (0°), a
# boss (30°) and a side vent (45°); slice through the floor (z=2) and the
# bosses/vents (z=8).
VIEWS = {"angles": [0, 30, 45], "z_slices": [2, 8]}

# Hero render for `build_all --hero`: a collage glued side by side — a 3/4
# showcase (taper, cavity, side vent) next to a top-down view that shows the
# floor drain holes and the support bosses.
HERO = {"views": [{"elev": 22, "azim": -55}, {"elev": 90, "azim": -90}]}

# Standard EU tapered nursery ("grow") pots: top Ø, base Ø, height (mm).
NURSERY_POTS = {
    "9cm": (90.0, 64.0, 82.0),
    "10cm": (100.0, 72.0, 92.0),
    "11cm": (110.0, 80.0, 100.0),
}


def make_pot(np_top_d: float, np_base_d: float, np_h: float) -> Part:
    """Build one draining outer pot sized for a given nursery pot."""
    in_top_r = np_top_d / 2 + GAP        # inner-cavity radii (with clearance)
    in_bot_r = np_base_d / 2 + GAP
    out_top_r = in_top_r + WALL          # outer-shell radii
    out_bot_r = in_bot_r + WALL
    height = FLOOR + BOSS_H + COVER * np_h

    # Tapered outer shell as a solid frustum (bottom circle -> top circle).
    pot = loft(
        [
            Plane.XY * Circle(out_bot_r),
            Plane.XY.offset(height) * Circle(out_top_r),
        ]
    )

    # Hollow it out: cavity from the top of the floor up through the rim.
    # Overshoot the top by 2 mm so the cavity opens cleanly.
    cavity = loft(
        [
            Plane.XY.offset(FLOOR) * Circle(in_bot_r),
            Plane.XY.offset(height + 2) * Circle(in_top_r),
        ]
    )
    pot -= cavity

    # Floor drainage: one central hole + a ring of holes, drilled up through
    # the floor (vertical holes are self-supporting).
    def floor_hole(x: float, y: float) -> Part:
        return Pos(x, y, -1) * Cylinder(
            radius=DRAIN_R,
            height=FLOOR + 2,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )

    pot -= floor_hole(0, 0)
    ring_r = in_bot_r * 0.55
    for i in range(DRAIN_RING_N):
        pot -= Rot(0, 0, i * 360 / DRAIN_RING_N) * floor_hole(ring_r, 0)

    # Side vents: round holes through the wall sitting just ABOVE the floor
    # (bottom tangent to the floor top) so they drain the plenum sideways
    # without undercutting the flush base. Round => self-supporting top.
    vent_z = FLOOR + VENT_R
    for i in range(VENT_N):
        ang = 360 / VENT_N * i + 45
        cutter = (
            Rot(0, 0, ang)
            * Pos(out_bot_r, 0, vent_z)
            * Rot(0, 90, 0)
            * Cylinder(radius=VENT_R, height=WALL * 4)
        )
        pot -= cutter

    # Support bosses on the floor to seat the nursery pot above the plenum.
    # Interleaved halfway between the drain holes so they never overlap them.
    boss_offset = (360 / DRAIN_RING_N) / 2
    for i in range(BOSS_N):
        ang = boss_offset + i * 360 / BOSS_N
        boss = (
            Rot(0, 0, ang)
            * Pos(ring_r, 0, FLOOR)
            * Cylinder(
                radius=BOSS_R,
                height=BOSS_H,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
            )
        )
        pot += boss

    # Round the top rim for comfort and print quality.
    top_edges = pot.edges().filter_by(GeomType.CIRCLE).group_by(Axis.Z)[-1]
    pot = fillet(top_edges, radius=RIM_FILLET)

    return pot


def build() -> dict[str, Shape]:
    """Return the three sized draining flower pots keyed by variant name."""
    return {name: make_pot(*dims) for name, dims in NURSERY_POTS.items()}


if __name__ == "__main__":
    # Convenience: quick sanity check when run directly (not used by build_all).
    for name, part in build().items():
        bb = part.bounding_box()
        print(
            f"{name}: valid={part.is_valid} "
            f"vol={part.volume / 1000:.1f}cm^3 "
            f"size={bb.size.X:.0f}x{bb.size.Y:.0f}x{bb.size.Z:.0f}mm"
        )
