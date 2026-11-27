# SPDX-License-Identifier: GPL-3.0-or-later
"""Plain 2D geometry on ``(x, y)`` tuples: no Qt, no IngeTrazo."""
from __future__ import annotations

import bisect
import math


def add(a, b):
    return (a[0] + b[0], a[1] + b[1])


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def mul(a, k):
    return (a[0] * k, a[1] * k)


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1]


def cross(a, b):
    return a[0] * b[1] - a[1] * b[0]


def length(a):
    return math.hypot(a[0], a[1])


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def unit(a):
    d = length(a)
    return (a[0] / d, a[1] / d) if d > 1e-12 else (0.0, 0.0)


def left_of(d):
    """``d`` turned a quarter anticlockwise."""
    return (-d[1], d[0])


def lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def turn_angle(a, b, c):
    """How much the way a -> b -> c turns at ``b`` (radians, + to the left)."""
    u, v = sub(b, a), sub(c, b)
    return math.atan2(cross(u, v), dot(u, v))


def segment_distance(p, a, b):
    ab = sub(b, a)
    d2 = dot(ab, ab)
    t = 0.0 if d2 < 1e-18 else max(0.0, min(1.0, dot(sub(p, a), ab) / d2))
    q = lerp(a, b, t)
    return dist(p, q), t


def line_hit(p, d, a, b):
    """Where the line ``p + s d`` crosses the segment ``a b``: ``(s, t)``
    with ``t`` along the segment (0..1), or ``None``."""
    e = sub(b, a)
    den = cross(d, e)
    if abs(den) < 1e-12:
        return None
    w = sub(a, p)
    s = cross(w, e) / den
    t = cross(w, d) / den
    if t < -1e-7 or t > 1.0 + 1e-7:
        return None
    return s, min(1.0, max(0.0, t))


def dedupe(points, tol=1e-6, closed=False):
    out: list = []
    for p in points:
        if not out or dist(p, out[-1]) > tol:
            out.append(p)
    if closed and len(out) > 1 and dist(out[0], out[-1]) <= tol:
        out.pop()
    return out


def simplify(points, closed=False, angle=math.radians(0.4)):
    """Without the points where the way goes straight on."""
    pts = dedupe(points, 1e-5, closed)
    changed = True
    while changed and len(pts) > (3 if closed else 2):
        changed = False
        rng = range(len(pts)) if closed else range(1, len(pts) - 1)
        for i in rng:
            a, b, c = pts[i - 1], pts[i], pts[(i + 1) % len(pts)]
            if abs(turn_angle(a, b, c)) < angle:
                del pts[i]
                changed = True
                break
    return pts


class Chain:
    """An open polyline measured by the distance run along it."""

    def __init__(self, points) -> None:
        self.pts = dedupe(points)
        if len(self.pts) < 2:
            raise ValueError("a chain needs two points")
        self.cum = [0.0]
        for a, b in zip(self.pts, self.pts[1:]):
            self.cum.append(self.cum[-1] + dist(a, b))

    @property
    def length(self) -> float:
        return self.cum[-1]

    def segment_at(self, s: float) -> int:
        i = bisect.bisect_right(self.cum, s) - 1
        return min(len(self.pts) - 2, max(0, i))

    def point(self, s: float):
        s = min(self.length, max(0.0, s))
        i = self.segment_at(s)
        span = self.cum[i + 1] - self.cum[i]
        return lerp(self.pts[i], self.pts[i + 1], (s - self.cum[i]) / span)

    def tangent(self, s: float):
        i = self.segment_at(s)
        return unit(sub(self.pts[i + 1], self.pts[i]))

    def between(self, s0: float, s1: float) -> list:
        """The points from ``s0`` to ``s1``, the chain's corners in between
        included."""
        out = [self.point(s0)]
        out += [p for p, c in zip(self.pts, self.cum)
                if s0 + 1e-6 < c < s1 - 1e-6]
        out.append(self.point(s1))
        return dedupe(out)

    def nearest(self, p):
        """``(distance, s)`` of the closest point to ``p``."""
        best = (math.inf, 0.0)
        for i, (a, b) in enumerate(zip(self.pts, self.pts[1:])):
            d, t = segment_distance(p, a, b)
            if d < best[0]:
                best = (d, self.cum[i] + t * (self.cum[i + 1] - self.cum[i]))
        return best

    def snap_to_corner(self, s: float, tol: float = 0.004) -> float:
        """A position almost on a corner (or an end) is on it: two points a
        hair apart would be welded by the mesh and open the solid."""
        i = bisect.bisect_left(self.cum, s)
        for j in (i - 1, i):
            if 0 <= j < len(self.cum) and abs(self.cum[j] - s) < tol:
                return self.cum[j]
        return s

    def ray(self, origin, direction, near=None):
        """The first hit of the half line from ``origin``, as ``(t, s)``,
        or ``None``. ``near``: of several, the one whose position along the
        chain is closest to it (a stair that turns past itself)."""
        hits = []
        for i, (a, b) in enumerate(zip(self.pts, self.pts[1:])):
            got = line_hit(origin, direction, a, b)
            if got is None or got[0] < -1e-6:
                continue
            s = self.cum[i] + got[1] * (self.cum[i + 1] - self.cum[i])
            hits.append((got[0], s))
        if not hits:
            return None
        first = min(hits)
        if near is not None:
            close = [h for h in hits if h[0] <= first[0] * 1.8 + 0.05]
            return min(close, key=lambda h: abs(h[1] - near))
        return first

    def reversed(self) -> "Chain":
        return Chain(list(reversed(self.pts)))


def offset_polyline(points, distance, closed=False):
    """``points`` moved ``distance`` to their left (negative: right), the
    corners mitred. One point out for each point in."""
    n = len(points)
    dirs = [unit(sub(points[(i + 1) % n], points[i]))
            for i in range(n if closed else n - 1)]
    out = []
    for i, p in enumerate(points):
        before = dirs[i - 1] if (closed or i > 0) else dirs[0]
        after = dirs[i] if (closed or i < n - 1) else dirs[-1]
        n0, n1 = left_of(before), left_of(after)
        den = 1.0 + dot(n0, n1)
        if den < 0.15:                       # nearly turning back
            out.append(add(p, mul(n1, distance)))
        else:
            out.append(add(p, mul(add(n0, n1), distance / den)))
    return out
