# ---------------------------------------------------------------------------
# Grasshopper "Python 3 Script" component  (Rhino 8)
# Paste this INTO the component. The real logic lives in cdf/hyperbolic_spiral.py
#
# Inputs  (name them exactly like this, set type hint in the component):
#   show               bool    (Boolean Toggle)
#   first_round        int     (Number Slider 4 .. 36, default 12)
#   rounds             int     (Number Slider 1 .. 5,  default 3)
#   increase           int     (Number Slider 1 .. 3,  default 2)
#   stitch_width       float   (Number Slider 0.5 .. 2, default 1.0)
#   stitch_height      float   (Number Slider 0.5 .. 3, default 1.5)
#   stitches_per_wave  int     (Number Slider 4 .. 24, default 16)
#   iterations         int     (Number Slider 0 .. 300, default 80)
#   seed               int     (Number Slider 0 .. 100, default 1)
# Outputs:
#   points, ring_lines, radial_lines, info
# ---------------------------------------------------------------------------
import Rhino.Geometry as rg
from cdf.hyperbolic_spiral import create_hyperbolic_spiral

points, ring_lines, radial_lines, info = [], [], [], ""

if show:
    res = create_hyperbolic_spiral(first_round=int(first_round),
                                   rounds=int(rounds),
                                   increase=int(increase),
                                   stitch_width=stitch_width,
                                   stitch_height=stitch_height,
                                   stitches_per_wave=int(stitches_per_wave),
                                   iterations=int(iterations),
                                   seed=int(seed))

    points = [rg.Point3d(x, y, z) for x, y, z in res["points"]]

    for i, j, rest, kind in res["edges"]:
        line = rg.Line(points[i], points[j])
        (ring_lines if kind == "ring" else radial_lines).append(line)

    info = "stitches per round: {}\ntotal: {}\naverage edge error: {:.3f}".format(
        res["counts"], len(points), res["error"])
