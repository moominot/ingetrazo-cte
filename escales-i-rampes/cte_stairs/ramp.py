# SPDX-License-Identifier: GPL-3.0-or-later
"""A ramp over the same plans as a stair.

By default it fills the plan: the height shared evenly along it, with flat
landings at the turns and, in long runs, in between. With a slope asked
for, it only runs as far as that slope needs (or says how much is missing).

The limits are those of the Spanish building code (CTE DB SUA 1, 4.3).
The landings of long runs are placed so that they are met; what the plan
or the asked slope cannot meet is warned about, never imposed.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from . import geom as g
from .layout import _balance, _Rays, _sides, _walking_line
from .layout import Options as StairOptions
from .plan import Plan, PlanError

#: use -> (longest flight in metres or 0, least width or 0). The width of a
#: ramp that is not on an accessible route depends on the evacuation (DB SI)
#: and the use of the building: it is not checked.
USES = {"access": (9.0, 1.20), "walk": (15.0, 0.0), "car": (0.0, 0.0)}
#: Up to this slope the code does not call it a ramp.
NOT_A_RAMP = 0.04
#: Accessible routes: flights are straight, or curve no tighter than this.
LEAST_RADIUS = 30.0
LEAST_LANDING = 1.50
#: How often a curved ramp gets a line across it.
_PITCH = 0.30


def limit(use: str, run: float) -> float:
    """The steepest slope (a fraction) for a flight ``run`` metres long in
    plan. On accessible routes: 10 % up to 3 m and 8 % up to 6 m, both
    included. The code's text says «less than»; the author's criterion
    accepts the round length itself."""
    if use == "car":
        return 0.16
    if use == "walk":
        return 0.12
    if run <= 3.0 + 1e-3:
        return 0.10
    return 0.08 if run <= 6.0 + 1e-3 else 0.06


@dataclass
class Options:
    height: float = 0.60
    slope: float = 0.0             # per cent asked for; 0 = fill the plan
    use: str = "access"            # "access" | "walk" | "car"
    turns: str = "landing"         # "landing" | "slope"
    split: bool = True             # landings in flights longer than allowed
    landing: float = 1.50          # length of those landings
    flip: bool = False
    width: float = 1.20
    side: str = "centre"
    helix_turn: float = 360.0
    helix_start: float = 0.0
    column: float = 0.10

    def sides(self) -> StairOptions:
        return StairOptions(flip=self.flip, width=self.width, side=self.side)


@dataclass
class Ramp:
    left: g.Chain
    right: g.Chain
    lines: list                    # [(u, v, distance along walk, rise)]
    walk: g.Chain
    height: float
    slope: float                   # of the flights, a fraction
    flights: list                  # [(from, to)] along the walking line
    landings: list                 # [(from, to)]
    width: float
    asked: float = 0.0             # the slope asked for, a fraction
    missing: float = 0.0           # metres of run the plan lacks for it
    spare: float = 0.0             # metres of the plan left unused
    helix: bool = False
    turned: float = 0.0            # helix: degrees actually climbed
    column: float = 0.0
    centre: tuple = (0.0, 0.0)

    @property
    def count(self) -> int:
        return len(self.lines)

    def line(self, k: int) -> tuple:
        u, v = self.lines[k][:2]
        return self.left.point(u), self.right.point(v)

    @property
    def run(self) -> float:
        """The sloping length, in plan along the walking line."""
        return sum(b - a for a, b in self.flights)

    @property
    def longest(self) -> float:
        return max(b - a for a, b in self.flights)

    def worst(self) -> float:
        """The slope the limits are held against: a curve's is measured at
        its least favourable side."""
        return max(self.slope, self.steepest_side())

    def tight_curve(self) -> bool:
        """Whether a flight curves tighter than an accessible route may."""
        for a, b in self.flights:
            pts = g.simplify(self.walk.between(a, b))
            turn = sum(abs(g.turn_angle(pts[i - 1], pts[i], pts[i + 1]))
                       for i in range(1, len(pts) - 1))
            if self.helix and turn <= 0:
                turn = (b - a) / LEAST_RADIUS * 2
            if turn > math.radians(2) and (b - a) / turn < LEAST_RADIUS:
                return True
        return False

    def steepest_side(self) -> float:
        """The slope at the side where it is steepest (the inside of a
        curve is shorter than the walking line)."""
        worst = 0.0
        for a, b in zip(self.lines, self.lines[1:]):
            rise = b[3] - a[3]
            if rise <= 1e-6:
                continue
            for side in (0, 1):
                run = b[side] - a[side]
                if run > 0.02:
                    worst = max(worst, rise / run)
        return worst


def _runs(S, marks, split, longest, landing):
    """``(flights, landings)`` along a walking line ``S`` long, with the
    turn landings ``marks`` and long flights cut."""
    marks = [list(m) for m in marks]
    if marks and S - marks[-1][1] < 0.15:
        marks[-1][1] = S
    if split and longest:
        # a flight a few centimetres too long (6.03 where 6 is the most) is
        # not cut in two: the turn landing beside it grows
        ends = [0.0] + [x for m in marks for x in m] + [S]
        for i in range(0, len(ends), 2):
            excess = ends[i + 1] - ends[i] - longest
            if 0.0 < excess <= 0.05 and marks:
                if i > 0:
                    marks[i // 2 - 1][1] += excess
                    ends[i] += excess
                else:
                    marks[0][0] -= excess
                    ends[1] -= excess
    pieces, at = [], 0.0
    for a, b in marks:
        pieces.append((at, a))
        at = b
    pieces.append((at, S))
    flights, landings = [], [tuple(m) for m in marks]
    for a, b in pieces:
        run = b - a
        if run < 0.05:
            continue
        parts = 1
        if split and longest and run > longest + 1e-3:
            parts = int(math.ceil((run + landing) / (longest + landing)
                                  - 1e-6))
        each = (run - (parts - 1) * landing) / parts
        for i in range(parts):
            start = a + i * (each + landing)
            flights.append((start, start + each))
            if i + 1 < parts:
                landings.append((start + each, start + each + landing))
    if not flights:
        raise PlanError("all_landing")
    return flights, sorted(landings)


def _cut(flights, landings, wanted):
    """The ramp ending where its flights add up to ``wanted``:
    ``(flights, landings, end)``."""
    done, kept = 0.0, []
    for a, b in flights:
        if done + (b - a) >= wanted - 1e-6:
            end = a + (wanted - done)
            kept.append((a, end))
            return kept, [m for m in landings if m[1] <= a + 1e-6], end
        kept.append((a, b))
        done += b - a
    return flights, landings, None


def _rise_at(s, flights, slope):
    return slope * sum(max(0.0, min(s, b) - a) for a, b in flights)


def _caps(use: str, asked: float) -> list:
    """The longest flights to try, the ones with fewest landings first."""
    if use != "access":
        return [USES[use][0]]
    if asked > 0:                          # the slope says how long
        if asked <= 0.08 + 1e-9:
            return [9.0] if asked <= 0.06 + 1e-9 else [6.0]
        return [3.0] if asked <= 0.10 + 1e-9 else [9.0]
    return [9.0, 6.0, 3.0]


def _split(o: Options, S: float, marks):
    """``(flights, landings)``: long runs cut so the use's limits are met;
    when they cannot be, as few landings as the longest flight allows."""
    asked = o.slope / 100.0
    if not o.split or 0 < asked <= NOT_A_RAMP:
        return _runs(S, marks, False, 0.0, o.landing)
    whole = _runs(S, marks, False, 0.0, o.landing)
    if not asked and o.height / sum(b - a for a, b in whole[0]) \
            <= NOT_A_RAMP + 1e-9:
        return whole
    first = None
    for cap in _caps(o.use, asked):
        try:
            flights, landings = _runs(S, marks, True, cap, o.landing)
        except PlanError:
            break
        run = sum(b - a for a, b in flights)
        if run < 0.5 * sum(b - a for a, b in whole[0]):
            break                          # more landing than ramp
        first = first or (flights, landings)
        longest = max(b - a for a, b in flights)
        if asked or o.height / run <= limit(o.use, longest) + 1e-9:
            return flights, landings
    return first or whole


def _solve(o: Options, S: float, marks):
    """``(flights, landings, slope, end, missing)``."""
    flights, landings = _split(o, S, marks)
    if o.slope > 0:
        # a landing more must not leave the asked slope without room: then
        # the flights stay whole, and the limit passed is warned about
        wanted = o.height / (o.slope / 100.0)
        if sum(b - a for a, b in flights) < wanted - 0.01:
            longest = USES[o.use][0] if o.split else 0.0
            for cap in (longest, 0.0):
                other = _runs(S, marks, cap > 0, cap, o.landing)
                if sum(b - a for a, b in other[0]) >= wanted - 0.01:
                    flights, landings = other
                    break
    run = sum(b - a for a, b in flights)
    end, missing = S, 0.0
    if o.slope > 0:
        wanted = o.height / (o.slope / 100.0)
        if wanted < run - 0.01:
            flights, landings, end = _cut(flights, landings, wanted)
            run = wanted
        elif wanted > run + 0.01:
            missing = wanted - run
    return flights, landings, o.height / run, end, missing


def _stations(walk, flights, landings, end, curved_everywhere):
    """Where the lines across go: the ends of every flight and landing, and
    along the curved stretches."""
    marks = {0.0, end}
    for a, b in flights + landings:
        marks.update((a, b))
    marks = sorted(m for m in marks if -1e-9 <= m <= end + 1e-9)
    out = [marks[0]]
    for a, b in zip(marks, marks[1:]):
        if b - a < 1e-4:
            continue
        mid = (a + b) / 2
        flat = any(x - 1e-6 <= mid <= y + 1e-6 for x, y in landings)
        bent = curved_everywhere or len(
            g.simplify(walk.between(a, b))) > 2
        n = int(math.ceil((b - a) / _PITCH)) if bent and not flat else 1
        out += [a + (b - a) * i / n for i in range(1, n + 1)]
    return out


def _helix(plan: Plan, o: Options) -> Ramp:
    outer = plan.radius
    column = 0.0
    inner = plan.inner_radius
    if inner <= 0.0:
        inner = column = max(0.03, min(o.column, outer - 0.3))
    width = outer - inner
    if width < 0.25:
        raise PlanError("narrow")
    walking = inner + width / 2
    total = math.radians(max(30.0, min(1440.0, o.helix_turn)))
    flights, landings, slope, end, missing = _solve(o, walking * total, [])
    way = -1.0 if o.flip else 1.0
    start = plan.start_angle + math.radians(o.helix_start)
    # a line every few degrees, and at the ends of every landing
    angles = {0.0, end / walking}
    for a, b in flights + landings:
        angles.update((a / walking, b / walking))
    angles = sorted(angles)
    marks = [angles[0]]
    for a, b in zip(angles, angles[1:]):
        if b - a < 1e-6:
            continue
        n = max(1, int(math.ceil((b - a) / math.radians(6) - 1e-6)))
        marks += [a + (b - a) * i / n for i in range(1, n + 1)]

    def ring(radius):
        return g.Chain([(plan.centre[0] + radius * math.cos(start + way * a),
                         plan.centre[1] + radius * math.sin(start + way * a))
                        for a in marks])

    inside, outside, walk = ring(inner), ring(outer), ring(walking)
    left, right = (inside, outside) if way > 0 else (outside, inside)
    lines = []
    for i, a in enumerate(marks):
        lines.append((left.cum[i], right.cum[i], walk.cum[i],
                      _rise_at(a * walking, flights, slope)))
    lines[-1] = lines[-1][:3] + (o.height,)
    return Ramp(left, right, lines, walk, o.height, slope, flights, landings,
                width, asked=o.slope / 100.0, missing=missing,
                spare=walking * total - end, helix=True,
                turned=math.degrees(end / walking), column=column,
                centre=plan.centre)


def compute(plan: Plan, o: Options) -> Ramp:
    if o.height <= 0.02:
        raise PlanError("no_height")
    if plan.kind == "circle":
        return _helix(plan, o)
    left, right, _chords = _sides(plan, o.sides())
    walk, turns, width = _walking_line(left, right)
    if walk.length < 0.3:
        raise PlanError("narrow")
    S = walk.length
    rays = _Rays(left, right, walk, turns, width)
    marks = []
    sloped = []                    # turns the slope goes round
    for t in turns:
        # a landing on the floor itself would be a ramp of no thickness
        if o.turns == "landing" and t.a > 0.15:
            marks.append((t.a, t.b))
        else:
            sloped.append(t)
    flights, landings, slope, end, missing = _solve(o, S, marks)

    if sloped:
        # equal steps all along, so the narrowing at the inside of a turn
        # can be shared out as with balanced winders
        n = max(2, int(round(S / _PITCH)))
        even = [S * i / n for i in range(n + 1)]
        across = _balance(rays, even, sloped, spread=2)
        fixed = {round(m, 6) for span in landings for m in span}
        chosen = [(s, pos) for s, pos in zip(even, across)
                  if s < end - 0.08
                  and all(abs(s - m) > 0.08 for m in fixed)
                  and not any(a < s < b for a, b in landings)]
        chosen += [(m, rays.at(m)) for m in fixed if m < end - 1e-6]
        chosen.append((end, rays.at(end) if end < S - 1e-6
                       else (left.length, right.length)))
        chosen.sort(key=lambda c: c[0])
    else:
        chosen = [(s, rays.at(s))
                  for s in _stations(walk, flights, landings, end, False)]

    lines = []
    for s, (u, v) in chosen:
        if lines:
            u, v = max(u, lines[-1][0]), max(v, lines[-1][1])
        lines.append((min(u, left.length), min(v, right.length), s,
                      _rise_at(s, flights, slope)))
    lines[0] = (0.0, 0.0, 0.0, 0.0)
    spare = S - end
    if end >= S - 1e-6:
        lines[-1] = (left.length, right.length, S, o.height)
    else:                          # the sides stop where the ramp does
        u, v = lines[-1][:2]
        lines[-1] = (u, v, end, o.height)
        left = g.Chain(left.between(0.0, u))
        right = g.Chain(right.between(0.0, v))
        lines = [(min(a, left.length), min(b, right.length), c, d)
                 for a, b, c, d in lines]
        lines[-1] = (left.length, right.length, end, o.height)
        walk = g.Chain(walk.between(0.0, end))
    return Ramp(left, right, lines, walk, o.height, slope, flights, landings,
                width, asked=o.slope / 100.0, missing=missing, spare=spare)
