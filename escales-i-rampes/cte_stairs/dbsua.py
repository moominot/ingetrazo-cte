# SPDX-License-Identifier: GPL-3.0-or-later
"""Whether a stair meets the sizes of CTE DB SUA 1, 4.1 (restricted use)
and 4.2 (general use), and a ramp those of 4.3 (``check_ramp``). It only
says so: nothing is changed.

Checked: risers, goings (curved ones where the code measures them), the
2 risers + going relation, the flights' steps and height, the length of a
landing in line and the least width. Not checked: the width table 4.1 and
DB SI ask for each use and occupancy, handrails, guards, closed risers,
nosings, headroom, doors and corridors by the landings.
"""
from __future__ import annotations

from . import geom as g
from . import ramp as ramps
from .layout import Layout

#: "restricted" | "general" | "public" (public areas, or no lift)
USES = ("restricted", "general", "public")
_TOL = 0.0005                      # half a millimetre
_LEAST_WIDTH = 0.80
#: In a curve, where the going is under this the width does not count.
_USEFUL_GOING = 0.17


class _Tread:
    """One tread, measured the way it is walked."""

    def __init__(self, layout: Layout, k: int) -> None:
        a0, b0 = layout.line(k)
        a1, b1 = layout.line(k + 1)
        left, right = g.dist(a0, a1), g.dist(b0, b1)
        if left <= right:                    # the narrow side first
            self.lines = ((a0, b0), (a1, b1))
        else:
            self.lines = ((b0, a0), (b1, a1))
        d0, d1 = g.unit(g.sub(b0, a0)), g.unit(g.sub(b1, a1))
        self.curved = abs(g.cross(d0, d1)) > 0.015       # about 1 degree
        other = layout.right.nearest(a0)[0]
        self.width = max(0.05, min(other, g.dist(a0, b0)))

    def going(self, from_narrow: float) -> float:
        """The going ``from_narrow`` metres in from the narrow side."""
        f = min(1.0, max(0.0, from_narrow / self.width))
        (a0, b0), (a1, b1) = self.lines
        return g.dist(g.lerp(a0, b0, f), g.lerp(a1, b1, f))

    def useful_width(self) -> float:
        narrow, wide = self.going(0.0), self.going(self.width)
        if narrow >= _USEFUL_GOING:
            return self.width
        if wide <= _USEFUL_GOING:
            return 0.0
        return self.width * (wide - _USEFUL_GOING) / (wide - narrow)


def _flights(layout: Layout) -> list:
    """The risers of each flight, landings apart: ``[(first, last)]``."""
    out, first = [], 0
    for k in range(layout.count - 1):
        if k in layout.landings:
            if k >= first:
                out.append((first, k))
            first = k + 1
    if first <= layout.count - 1:
        out.append((first, layout.count - 1))
    return out


def check(layout: Layout, use: str) -> list:
    """What is not met, as ``[(key of texts, {values})]``; empty: it
    complies with what is checked."""
    out: list = []

    def fail(key, **values):
        if all(k != key for k, _v in out):
            out.append((key, values))

    def cm(x):
        return f"{x * 100:.1f}"

    riser = layout.riser
    treads = [_Tread(layout, k) for k in range(layout.count - 1)
              if k not in layout.landings]
    if not treads:
        return [("db_no_treads", {})]
    width = min(t.width for t in treads)

    if use == "restricted":
        if riser > 0.20 + _TOL:
            fail("db_riser_max", v=cm(riser), m="20")
        if width < _LEAST_WIDTH - _TOL:
            fail("db_width", v=f"{width:.2f}")
        for t in treads:
            if not t.curved:
                if t.going(t.width / 2) < 0.22 - _TOL:
                    fail("db_going_min", v=cm(t.going(t.width / 2)), m="22")
                continue
            at = t.width / 2 if t.width < 1.0 else 0.50
            if t.going(at) < 0.22 - _TOL:
                fail("db_curve_walking", v=cm(t.going(at)), m="22")
            if t.going(0.0) < 0.05 - _TOL:
                fail("db_curve_narrow", v=cm(t.going(0.0)))
            if t.going(t.width) > 0.44 + _TOL:
                fail("db_curve_wide", v=cm(t.going(t.width)))
        return out

    most = 0.175 if use == "public" else 0.185
    if riser < 0.13 - _TOL:
        fail("db_riser_min", v=cm(riser))
    if riser > most + _TOL:
        fail("db_riser_max", v=cm(riser), m=f"{most * 100:g}")

    def relation(going):
        total = 2 * riser + going
        if not 0.54 - _TOL <= total <= 0.70 + _TOL:
            fail("db_relation", v=cm(total))

    straight_goings, curved_axis = [], []
    useful = width
    for t in treads:
        if not t.curved:
            going = t.going(t.width / 2)
            straight_goings.append(going)
            if going < 0.28 - _TOL:
                fail("db_going_min", v=cm(going), m="28")
            relation(going)
            continue
        inner = t.going(0.50)
        if inner < 0.28 - _TOL:
            fail("db_curve_inner", v=cm(inner))
        if t.going(t.width) > 0.44 + _TOL:
            fail("db_curve_wide", v=cm(t.going(t.width)))
        relation(inner)
        relation(t.going(max(0.0, t.width - 0.50)))
        curved_axis.append(t.going(t.width / 2))
        useful = min(useful, t.useful_width())
    if useful < _LEAST_WIDTH - _TOL:
        fail("db_width", v=f"{useful:.2f}")
    if straight_goings:
        if max(straight_goings) - min(straight_goings) > 0.005:
            fail("db_uneven")
        if curved_axis and min(curved_axis) < min(straight_goings) - 0.005:
            fail("db_mixed")

    high = 2.25 if use == "public" else 3.20
    for first, last in _flights(layout):
        risers = last - first + 1
        if risers < 3:
            fail("db_few_steps", v=risers)
        if risers * riser > high + _TOL:
            fail("db_flight_height", v=f"{risers * riser:.2f}",
                 m=f"{high:.2f}")
    for k in layout.landings:
        if k + 1 >= layout.count:
            continue
        a0, b0 = layout.line(k)
        a1, b1 = layout.line(k + 1)
        in_line = abs(g.cross(g.unit(g.sub(b0, a0)),
                              g.unit(g.sub(b1, a1)))) < 0.015
        long = layout.stations[k + 1] - layout.stations[k]
        if in_line and long < 1.0 - _TOL:
            fail("db_landing", v=f"{long:.2f}")
    return out


def _in_line(walk, a: float, b: float) -> bool:
    """Whether a landing goes straight on (not at a change of direction)."""
    before = walk.tangent(max(0.0, a - 0.01))
    after = walk.tangent(min(walk.length, b + 0.01))
    return abs(g.cross(before, after)) < 0.015 and g.dot(before, after) > 0


def check_ramp(ramp, use: str) -> list:
    """What a ramp does not meet, as ``[(key of texts, {values})]``. Up to
    4 % the code does not call it a ramp, and nothing applies. The texts'
    values use a point for the decimals."""
    worst = ramp.worst()
    if worst <= ramps.NOT_A_RAMP + 5e-5:
        return []
    out: list = []
    longest, width = ramps.USES[use]
    most = ramps.limit(use, ramp.longest)
    if worst > most + 5e-5:
        out.append(("Over {p} % for a flight of {m} m.",
                    {"p": f"{most * 100:g}", "m": f"{ramp.longest:.2f}"}))
    if longest and ramp.longest > longest + 0.005:
        out.append(("A flight over {m} m.", {"m": f"{longest:g}"}))
    if width and ramp.width < width - 0.005:
        out.append(("Narrower than {m} m.", {"m": f"{width:.2f}"}))
    if use == "access" and ramp.tight_curve():
        out.append(("Accessible route: flights must be straight, or have a "
                    "radius of 30 m or more.", {}))
    if use != "car" and any(
            b - a < ramps.LEAST_LANDING - 1e-3 and _in_line(ramp.walk, a, b)
            for a, b in ramp.landings):
        out.append(("Landings in line need 1.50 m or more.", {}))
    return out
