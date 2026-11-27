# SPDX-License-Identifier: GPL-3.0-or-later
"""Where the steps go. From a :class:`~stairs.plan.Plan` and the height:
the two sides of the stair and the line of every riser across them.

Words: **riser** the upright face of a step (davanter), **going** the
tread measured along the walking line (petjada), **walking line** where
that is measured: down the middle, or half a metre from the inner side
when the stair is wider than a metre.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from . import geom as g
from .plan import Plan, PlanError

#: The comfort rule: 2 risers + 1 going, metres.
RULE_MIN, RULE_AIM, RULE_MAX = 0.60, 0.63, 0.65
MAX_STEPS = 150
_CORNER = math.radians(30)
#: Two turns closer than this along the walking line are one (a U with a
#: narrow well has one landing, not two).
_JOIN = 0.6
#: The narrowest a balanced winder is let get at the inner side.
_MIN_INNER = 0.07


@dataclass
class Options:
    height: float = 2.80
    steps: int = 0                 # risers; 0 = by the rule
    turns: str = "landing"         # "landing" | "winders"
    use_drawn: bool = True         # take the step lines of the drawing
    flip: bool = False             # climb from the other end
    width: float = 1.00            # open line: the stair's width
    side: str = "centre"           # open line: "left" | "centre" | "right"
    helix_turn: float = 360.0      # circle: degrees climbed
    helix_start: float = 0.0       # circle: degrees added to the start
    column: float = 0.10           # one circle: radius of the central post


@dataclass
class Layout:
    left: g.Chain
    right: g.Chain
    risers: list                   # [(u, v)]: positions along left / right
    walk: g.Chain
    stations: list                 # distance of each riser along ``walk``
    height: float
    landings: set = field(default_factory=set)     # tread indices
    drawn: bool = False
    helix: bool = False
    column: float = 0.0
    centre: tuple = (0.0, 0.0)

    @property
    def count(self) -> int:
        return len(self.risers)

    @property
    def riser(self) -> float:
        return self.height / self.count

    def goings(self) -> list:
        """The goings along the walking line, landings left out."""
        return [self.stations[k + 1] - self.stations[k]
                for k in range(self.count - 1) if k not in self.landings]

    @property
    def going(self) -> float:
        got = self.goings()
        return sum(got) / len(got) if got else 0.0

    @property
    def rule(self) -> float:
        return 2.0 * self.riser + self.going

    def line(self, k: int) -> tuple:
        u, v = self.risers[k]
        return self.left.point(u), self.right.point(v)

    def tread_polygon(self, k: int) -> list:
        """Tread ``k`` (between risers ``k`` and ``k+1``), anticlockwise."""
        (u0, v0), (u1, v1) = self.risers[k], self.risers[k + 1]
        out = self.right.between(v0, v1) \
            + list(reversed(self.left.between(u0, u1)))
        return g.dedupe(out, 1e-5, closed=True)

    def inner_goings(self) -> tuple:
        """The narrowest and widest tread at either side."""
        widths = []
        for k in range(self.count - 1):
            if k in self.landings:
                continue
            (u0, v0), (u1, v1) = self.risers[k], self.risers[k + 1]
            widths.append(min(u1 - u0, v1 - v0))
        return (min(widths), max(widths)) if widths else (0.0, 0.0)


def score(riser: float, going: float) -> float:
    """How far a riser and a going are from a comfortable stair."""
    rule = 2 * riser + going
    return (max(0.0, RULE_MIN - rule, rule - RULE_MAX) * 10
            + abs(rule - RULE_AIM) * 2
            + max(0.0, riser - 0.185) * 30 + max(0.0, 0.14 - riser) * 10
            + max(0.0, 0.22 - going) * 20)


# ---- The walking line -----------------------------------------------------------

@dataclass
class _Turn:
    a: float                       # where it starts along the walking line
    b: float
    left: bool                     # turns to the left: the left side is inner
    arcs: list = field(default_factory=list)    # [(a, b, centre, left)]


def _width(left: g.Chain, right: g.Chain) -> float:
    gaps = []
    for k in range(21):
        gaps.append(right.nearest(left.point(left.length * (k + .5) / 21))[0])
        gaps.append(left.nearest(right.point(right.length * (k + .5) / 21))[0])
    gaps.sort()
    return gaps[len(gaps) // 2]


def _walking_line(left: g.Chain, right: g.Chain):
    """``(walk, turns, width)``: the walking line with its corners rounded
    about the inner corner, and where those turns are."""
    width = _width(left, right)
    inset = min(width / 2.0, 0.5)
    lp = left.pts
    total = sum(g.turn_angle(lp[i - 1], lp[i], lp[i + 1])
                for i in range(1, len(lp) - 1))
    rp = right.pts
    total += sum(g.turn_angle(rp[i - 1], rp[i], rp[i + 1])
                 for i in range(1, len(rp) - 1))
    inner_left = total >= 0
    if inner_left:
        base = g.offset_polyline(left.pts, -inset)
    else:
        base = g.offset_polyline(right.pts, inset)
    base = g.simplify(base)
    # its two ends on the end lines of the stair
    for end in (0, -1):
        a, b = left.pts[end], right.pts[end]
        p = base[end]
        q = base[1 if end == 0 else -2]
        d = g.sub(q, p)
        e = g.sub(b, a)
        den = g.cross(d, e)
        if abs(den) > 1e-9:
            s = g.cross(g.sub(a, p), e) / den
            if s < 0.95:
                base[end] = g.add(p, g.mul(d, s))
    n = len(base)
    angles = [0.0] + [g.turn_angle(base[i - 1], base[i], base[i + 1])
                      for i in range(1, n - 1)] + [0.0]
    sharp = [abs(a) > _CORNER for a in angles]
    out = [base[0]]
    arcs = []                      # (first out index, last, centre, left)
    for i in range(1, n - 1):
        if not sharp[i]:
            out.append(base[i])
            continue
        angle = angles[i]
        to_left = angle > 0
        radius = inset if to_left == inner_left else max(width - inset, 0.05)
        before, after = g.unit(g.sub(base[i], base[i - 1])), \
            g.unit(g.sub(base[i + 1], base[i]))
        tangent = radius * math.tan(min(abs(angle), 2.8) / 2.0)
        room0 = g.dist(base[i - 1], base[i]) * (0.5 if sharp[i - 1] else 1.0)
        room1 = g.dist(base[i], base[i + 1]) * (0.5 if sharp[i + 1] else 1.0)
        fit = min(1.0, room0 / tangent, room1 / tangent)
        tangent *= fit
        radius *= fit
        p0 = g.sub(base[i], g.mul(before, tangent))
        side = g.left_of(before) if to_left else g.mul(g.left_of(before), -1)
        centre = g.add(p0, g.mul(side, radius))
        a0 = math.atan2(p0[1] - centre[1], p0[0] - centre[0])
        first = len(out)
        steps = max(6, int(abs(angle) / math.radians(5)))
        for k in range(steps + 1):
            a = a0 + angle * k / steps
            out.append((centre[0] + radius * math.cos(a),
                        centre[1] + radius * math.sin(a)))
        arcs.append((first, len(out) - 1, centre, to_left))
    out.append(base[-1])
    walk = g.Chain(out)
    turns: list = []
    for first, last, centre, to_left in arcs:
        a = walk.nearest(out[first])[1]
        b = walk.nearest(out[last])[1]
        arc = (a, b, centre, to_left)
        if turns and turns[-1].left == to_left and a - turns[-1].b < _JOIN:
            turns[-1].b = b
            turns[-1].arcs.append(arc)
        else:
            turns.append(_Turn(a, b, to_left, [arc]))
    return walk, turns, width


class _Rays:
    """Riser lines square to the walking line."""

    def __init__(self, left, right, walk, turns, width) -> None:
        self.left, self.right, self.walk = left, right, walk
        self.turns, self.width = turns, width

    def normal(self, s: float):
        """Leftwards across the stair at ``s``."""
        for turn in self.turns:
            for a, b, centre, to_left in turn.arcs:
                if a + 1e-6 < s < b - 1e-6:
                    inward = g.unit(g.sub(centre, self.walk.point(s)))
                    return inward if to_left else g.mul(inward, -1)
        for turn in self.turns:        # at the ends of an arc: square to
            for a, b, _c, _l in turn.arcs:       # the straight part
                if abs(s - a) <= 1e-6:
                    return g.left_of(self.walk.tangent(max(0.0, s - 1e-3)))
                if abs(s - b) <= 1e-6:
                    return g.left_of(self.walk.tangent(
                        min(self.walk.length, s + 1e-3)))
        return g.left_of(self.walk.tangent(s))

    def at(self, s: float) -> tuple:
        p = self.walk.point(s)
        n = self.normal(s)
        out = []
        for chain, d in ((self.left, n), (self.right, g.mul(n, -1))):
            hit = chain.ray(p, d)
            if hit is None or hit[0] > 2.5 * self.width:
                out.append(chain.nearest(p)[1])
            else:
                out.append(chain.snap_to_corner(hit[1]))
        return tuple(out)


def _share(total: int, lengths: list) -> list:
    """``total`` treads shared among flights by their length, one at least
    for each."""
    whole = sum(lengths)
    out = [max(1, int(total * x / whole)) for x in lengths]
    while sum(out) > total:
        i = max((i for i in range(len(out)) if out[i] > 1),
                key=lambda i: out[i] - total * lengths[i] / whole)
        out[i] -= 1
    while sum(out) < total:
        i = max(range(len(out)), key=lambda i: lengths[i] / (out[i] + 1))
        out[i] += 1
    return out


# ---- With landings ---------------------------------------------------------------

def _with_landings(walk, turns, height, steps):
    """``(stations, landing treads)``."""
    S = walk.length
    marks = [[t.a, t.b] for t in turns]
    # a flight too short for a step is part of the landing beside it
    if marks and marks[0][0] < 0.15:
        marks[0][0] = 0.0
    if marks and S - marks[-1][1] < 0.15:
        marks[-1][1] = S
    i = 0
    while i + 1 < len(marks):
        if marks[i + 1][0] - marks[i][1] < 0.15:
            marks[i][1] = marks[i + 1][1]
            del marks[i + 1]
        else:
            i += 1
    flights, at = [], 0.0
    for a, b in marks:
        if a - at > 1e-6:
            flights.append((at, a))
        at = b
    if S - at > 1e-6:
        flights.append((at, S))
    if not flights:
        raise PlanError("all_landing")
    lengths = [b - a for a, b in flights]
    extra = len(flights) + (1 if marks and marks[0][0] == 0.0 else 0) \
        + (1 if marks and marks[-1][1] == S else 0)
    low = len(flights) + extra

    def pitch(treads):
        """One going for every flight: the one the tightest allows."""
        return min(x / t for x, t in zip(lengths, treads))

    def build(n):
        treads = _share(n - extra, lengths)
        going = pitch(treads)
        stations = []
        for (a, b), t in zip(flights, treads):
            # what a flight does not use goes to the landing: the first
            # starts at its end line, the last arrives at its own
            spare = (b - a) - going * t
            if a <= 1e-9:
                first = a
            elif b >= S - 1e-9:
                first = a + spare
            else:
                first = a + spare / 2
            stations += [first + going * j for j in range(t + 1)]
        if marks and marks[0][0] == 0.0:
            stations.insert(0, 0.0)
        if marks and marks[-1][1] == S:
            stations.append(S)
        return stations

    if steps:
        n = max(low, min(MAX_STEPS, steps))
    else:
        n = min(range(low, 70),
                key=lambda n: score(height / n,
                                    pitch(_share(n - extra, lengths))))
    stations = build(n)
    treads = _share(n - extra, lengths)
    landings = set()
    at = 0
    if marks and marks[0][0] == 0.0:
        landings.add(0)
        at = 1
    for i, t in enumerate(treads):
        at += t
        if i + 1 < len(treads) or (marks and marks[-1][1] == S):
            landings.add(at)
        at += 1
    return stations, landings


# ---- Balanced winders -------------------------------------------------------------

def _zones(turns, going, count, spread):
    """``[[first riser, last riser, turns]]`` to balance."""
    zones: list = []
    for turn in turns:
        lo = max(0, int(turn.a / going + 1e-6) - spread)
        hi = min(count - 1, int(math.ceil(turn.b / going - 1e-6)) + spread)
        if zones and lo <= zones[-1][1]:
            if zones[-1][2][-1].left == turn.left:
                zones[-1][1] = max(zones[-1][1], hi)
                zones[-1][2].append(turn)
                continue
            middle = (zones[-1][1] + lo) // 2
            zones[-1][1] = middle
            lo = middle
        zones.append([lo, hi, [turn]])
    return zones


def _balance(rays, stations, turns, spread=3):
    """Riser lines with the narrowing of the turns shared with the steps
    around them: at the inner side the goings shrink little by little."""
    count = len(stations)
    going = stations[1] - stations[0]
    natural = [rays.at(s) for s in stations]
    natural[0] = (0.0, 0.0)
    natural[-1] = (rays.left.length, rays.right.length)
    out = list(natural)
    zones = _zones(turns, going, count, spread)
    for z, (lo, hi, group) in enumerate(zones):
        inner_left = group[0].left
        side = 0 if inner_left else 1
        inner = rays.left if inner_left else rays.right
        outer = rays.right if inner_left else rays.left
        floor = zones[z - 1][1] if z else 0
        ceil = zones[z + 1][0] if z + 1 < len(zones) else count - 1
        while True:
            m = hi - lo
            if m < 2:
                widths = None
                break
            room = natural[hi][side] - natural[lo][side]
            weights = []
            for j in range(lo, hi):
                mid = (stations[j] + stations[j + 1]) / 2
                best = 0.0
                for t in group:
                    half = (t.b - t.a) / 2 + (spread + 0.5) * going
                    x = abs(mid - (t.a + t.b) / 2) / half
                    if x < 1:
                        best = max(best, 0.5 * (1 + math.cos(math.pi * x)))
                weights.append(best + 0.02)
            pull = (m * going - room) / sum(weights)
            widths = [going - pull * w for w in weights]
            if min(widths) >= _MIN_INNER or (lo <= floor and hi >= ceil):
                break
            lo, hi = max(floor, lo - 1), min(ceil, hi + 1)
        if widths is None:
            continue
        if min(widths) < 0.02:
            raised = [max(w, 0.02) for w in widths]
            scale = room / sum(raised)
            widths = [w * scale for w in raised]
        at = natural[lo][side]
        for j in range(lo + 1, hi):
            at += widths[j - 1 - lo]
            pos = inner.snap_to_corner(at, 0.003)
            q = inner.point(pos)
            p = rays.walk.point(stations[j])
            d = g.unit(g.sub(p, q))
            hit = outer.ray(q, d) if g.dist(p, q) > 1e-4 else None
            if hit is None or hit[0] > 3.0 * rays.width:
                other = outer.nearest(p)[1]
            else:
                other = outer.snap_to_corner(hit[1])
            out[j] = (pos, other) if inner_left else (other, pos)
    return out


# ---- The cases ----------------------------------------------------------------------

def _climbing_order(risers, left, right):
    """No riser line behind the one before it."""
    out = [risers[0]]
    for u, v in risers[1:]:
        u0, v0 = out[-1]
        out.append((min(left.length, max(u, u0)),
                    min(right.length, max(v, v0))))
    return out


def _crossing(walk, a, b):
    """Where the walking line crosses the riser line ``a b``."""
    d = g.sub(b, a)
    for i, (p, q) in enumerate(zip(walk.pts, walk.pts[1:])):
        got = g.line_hit(a, d, p, q)
        if got is None or not -0.02 <= got[0] <= 1.02:
            continue
        return walk.cum[i] + got[1] * (walk.cum[i + 1] - walk.cum[i])
    return walk.nearest(g.lerp(a, b, 0.5))[1]


def has_drawn_steps(plan: Plan) -> bool:
    return plan.kind == "outline" and len(plan.chords) >= 2


def _sides(plan: Plan, o: Options):
    """``(left chain, right chain, drawn lines)`` as climbed."""
    chords = list(plan.chords)
    if plan.kind == "outline":
        left, right = g.Chain(plan.left), g.Chain(plan.right)
        if o.flip:
            chords = sorted(((right.length - b, left.length - a)
                             for a, b in chords), key=lambda c: c[0] + c[1])
            left, right = right.reversed(), left.reversed()
        return left, right, chords
    path = list(plan.path)
    if o.flip:
        path.reverse()
    w = max(0.2, o.width)
    shift = {"left": (0.0, -w), "right": (w, 0.0),
             "centre": (w / 2, -w / 2)}[o.side]
    sides = [path if d == 0.0 else g.offset_polyline(path, d) for d in shift]
    return g.Chain(sides[0]), g.Chain(sides[1]), []


def _helix(plan: Plan, o: Options) -> Layout:
    outer = plan.radius
    column = 0.0
    inner = plan.inner_radius
    if inner <= 0.0:
        inner = column = max(0.03, min(o.column, outer - 0.3))
    width = outer - inner
    if width < 0.25:
        raise PlanError("narrow")
    walking = inner + min(width / 2, 0.5)
    total = math.radians(max(30.0, min(1440.0, o.helix_turn)))
    if o.steps:
        n = max(3, min(MAX_STEPS, o.steps))
    else:
        n = min(range(3, 90),
                key=lambda n: score(o.height / n,
                                    walking * total / (n - 1)))
    way = -1.0 if o.flip else 1.0
    start = plan.start_angle + math.radians(o.helix_start)
    step = total / (n - 1)
    parts = max(1, int(math.ceil(step / math.radians(6) - 1e-6)))

    def ring(radius):
        pts = []
        for k in range((n - 1) * parts + 1):
            a = start + way * step * k / parts
            pts.append((plan.centre[0] + radius * math.cos(a),
                        plan.centre[1] + radius * math.sin(a)))
        return g.Chain(pts)

    inside, outside, walk = ring(inner), ring(outer), ring(walking)
    # anticlockwise, the centre is on the climber's left
    left, right = (inside, outside) if way > 0 else (outside, inside)
    risers = [(left.cum[k * parts], right.cum[k * parts]) for k in range(n)]
    stations = [walk.cum[k * parts] for k in range(n)]
    return Layout(left, right, risers, walk, stations, o.height, helix=True,
                  column=column, centre=plan.centre)


def compute(plan: Plan, o: Options) -> Layout:
    if o.height <= 0.05:
        raise PlanError("no_height")
    if plan.kind == "circle":
        return _helix(plan, o)
    left, right, chords = _sides(plan, o)
    walk, turns, width = _walking_line(left, right)
    if walk.length < 0.3:
        raise PlanError("narrow")
    rays = _Rays(left, right, walk, turns, width)

    if has_drawn_steps(plan) and o.use_drawn and not o.steps:
        lines = [(0.0, 0.0)] \
            + [(left.snap_to_corner(a, 0.008), right.snap_to_corner(b, 0.008))
               for a, b in chords] \
            + [(left.length, right.length)]
        stations = [0.0]
        for u, v in lines[1:-1]:
            stations.append(_crossing(walk, left.point(u), right.point(v)))
        stations.append(walk.length)
        goings = sorted(b - a for a, b in zip(stations, stations[1:]))
        median = goings[len(goings) // 2]
        landings = {k for k in range(len(lines) - 1)
                    if stations[k + 1] - stations[k]
                    > max(1.9 * median, 0.62)}
        return Layout(left, right, lines, walk, stations, o.height,
                      landings=landings, drawn=True)

    if turns and o.turns == "landing":
        stations, landings = _with_landings(walk, turns, o.height, o.steps)
        risers = [rays.at(s) for s in stations]
    else:
        if o.steps:
            n = max(2, min(MAX_STEPS, o.steps))
        else:
            n = min(range(2, 90),
                    key=lambda n: score(o.height / n, walk.length / (n - 1)))
        stations = [walk.length * k / (n - 1) for k in range(n)]
        landings = set()
        if turns:
            risers = _balance(rays, stations, turns)
        else:
            risers = [rays.at(s) for s in stations]
    risers[0] = (0.0, 0.0)
    risers[-1] = (left.length, right.length)
    risers = _climbing_order(risers, left, right)
    return Layout(left, right, risers, walk, stations, o.height,
                  landings=landings)
