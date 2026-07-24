"""Under-cabinet brush hook, glued on with 30 mm nano tape.

A flat plate nano-tapes to the underside of a kitchen cabinet; a narrow J-hook
hangs beneath it. A brush's ~10 mm hanging hole slips over the upturned tip and
rests on the peg; the tip and the shank capture it on both ends.

The hook is tucked **under the plate footprint** on purpose: the shank drops at
the back edge and the peg reaches forward under the plate, so a hanging brush's
weight line falls inside the tape patch. That keeps the tape mostly in shear
instead of prying one edge off (peel is double-sided tape's weakest mode).

Coordinates are the in-use pose: +Z is up (toward the cabinet), the glue face is
the top (Z = 0), the plate spans +X from the back edge (X = 0, wall side) to the
front (sink side), and the hook hangs below in -Z within that span.

Print orientation (support-free): lay it on its side — the flat hook face
(the Y = 0 face) on the bed — so the 30 mm plate width becomes the build height.
The whole hook profile then sits on the bed (good adhesion) and nothing
overhangs, so no supports. The nano tape goes on the plate's top face. (Rotate
90° about X in the slicer to get there.)
"""

from __future__ import annotations

from build123d import Align, Axis, Box, Part, Pos, Shape, fillet

# --- parameters (mm) --------------------------------------------------------
TAPE_W = 30.0     # plate width == nano-tape width
PLATE_L = 40.0    # plate length (front-to-back); tape cut to ~this
PLATE_T = 4.0     # plate thickness

HOOK_T = 7.0      # hook bar thickness (Y); passes a ~10 mm brush hole
SHANK_W = 7.0     # shank width along X, dropped at the back edge (X 0..SHANK_W)

PEG_DROP = 28.0   # peg underside below the glue face
PEG_H = 6.0       # peg height (vertical thickness of the bar)
PEG_FRONT = 34.0  # how far forward the peg reaches (stays < PLATE_L, under plate)
TIP_W = 6.0       # upturned-tip width (along X)
TIP_RISE = 7.0    # how far the tip rises above the peg top (retention)

FILLET_R = 1.5    # edge rounding

_MIN = (Align.MIN, Align.MIN, Align.MIN)


def make_hook() -> Part:
    """Build the brush hook in its in-use pose."""
    peg_bottom = -PEG_DROP
    peg_top = peg_bottom + PEG_H
    tip_top = peg_top + TIP_RISE

    # Mounting plate: glue face on top at Z = 0.
    plate = Pos(0, 0, -PLATE_T) * Box(PLATE_L, TAPE_W, PLATE_T, align=_MIN)

    # Shank drops from the plate at the BACK edge down to the peg.
    shank = Pos(0, 0, peg_bottom) * Box(SHANK_W, HOOK_T, -peg_bottom, align=_MIN)

    # Peg reaches FORWARD under the plate (overlaps the shank for a solid joint).
    peg = Pos(0, 0, peg_bottom) * Box(PEG_FRONT, HOOK_T, PEG_H, align=_MIN)

    # Upturned tip near the front retains the brush; it and the shank capture the
    # brush between them, and the whole hook stays within the plate footprint.
    tip = Pos(PEG_FRONT - TIP_W, 0, peg_bottom) * Box(
        TIP_W, HOOK_T, tip_top - peg_bottom, align=_MIN
    )

    part = plate + shank + peg + tip

    # Round the profile corners (edges running across the hook thickness) for
    # smooth brush loading and a bit of strength at the inner corner.
    part = fillet(part.edges().filter_by(Axis.Y), radius=FILLET_R)
    return part


# Inspection views for `build_all --views`: the hook profile (0°) and a section
# across the plate width (90°); slice through the plate (z=-2) and the peg (z=-25).
VIEWS = {"angles": [0, 90], "z_slices": [-2, -25]}

# Hero collage for `build_all --hero`: a 3/4 showcase next to a straight-on side
# profile that reads the J-hook shape clearly.
HERO = {"views": [{"elev": 20, "azim": -60}, {"elev": 0, "azim": -90}]}


def build() -> dict[str, Shape]:
    return {"brushhook": make_hook()}


if __name__ == "__main__":
    part = make_hook()
    bb = part.bounding_box()
    print(
        f"valid={part.is_valid} vol={part.volume/1000:.1f}cm^3 "
        f"size={bb.size.X:.0f}x{bb.size.Y:.0f}x{bb.size.Z:.0f}mm"
    )
