"""Draining outer flower pot ("Übertopf") for standard tapered nursery pots.

A printed OUTER pot that a standard plastic nursery pot of 9/10/11 cm top
diameter drops into. The nursery pot rests on internal bosses that keep its
base off the floor, leaving a drainage plenum. Water leaves through a ring of
holes in the floor and through arched notches at the base.

Print orientation: open side UP, flat base on the bed. Everything is
support-free — the base sits flush, walls taper gently outward, and the base
notches are arched (round cutters) so their tops self-support. See the
easy-to-print design principle in the repo CLAUDE.md.
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
NOTCH_R = 4.5    # radius of the arched base notches
NOTCH_N = 4      # number of base notches ("feet" are the gaps between them)
BOSS_R = 5.0     # radius of the nursery-pot support bosses
BOSS_N = 4       # number of support bosses
RIM_FILLET = 1.2 # top-rim rounding

# Standard EU tapered nursery ("grow") pots: top Ø, base Ø, height (mm).
NURSERY_POTS = {
    "flowerpot_9cm": (90.0, 64.0, 82.0),
    "flowerpot_10cm": (100.0, 72.0, 92.0),
    "flowerpot_11cm": (110.0, 80.0, 100.0),
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

    # Base notches: horizontal round cutters through the base wall, open to the
    # bed, so water always drains sideways even on a flat surface. The wall
    # sections left between them read as feet.
    for i in range(NOTCH_N):
        ang = 360 / NOTCH_N * i + 45
        cutter = (
            Rot(0, 0, ang)
            * Pos(out_bot_r, 0, NOTCH_R)
            * Rot(0, 90, 0)
            * Cylinder(radius=NOTCH_R, height=WALL * 4)
        )
        pot -= cutter

    # Support bosses on the floor to seat the nursery pot above the plenum.
    boss_ring = np_base_d / 2 * 0.5
    for i in range(BOSS_N):
        ang = 360 / BOSS_N * i + 45
        boss = (
            Rot(0, 0, ang)
            * Pos(boss_ring, 0, FLOOR)
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
    """Return the three sized draining flower pots keyed by output stem."""
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
