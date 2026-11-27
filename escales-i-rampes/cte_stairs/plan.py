# SPDX-License-Identifier: GPL-3.0-or-later
"""Reading the plan drawing: what kind of stair its lines describe.

* **outline** — a closed contour (the two sides and the two ends). Lines
  drawn across it, from side to side, are taken as the steps.
* **path** — an open line (straight, broken, arcs): the way the stair runs;
  the width is given apart.
* **circle** — one or two concentric circles: a helical stair.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from . import geom as g

_WELD = 0.003


class PlanError(ValueError):
    """The drawing cannot be read as a stair. The text is a key of texts."""


@dataclass
class Plan:
    kind: str                                   # "outline" | "path" | "circle"
    left: list = field(default_factory=list)    # outline: the two sides, both
    right: list = field(default_factory=list)   #   from the start to the end
    chords: list = field(default_factory=list)  # outline: drawn step lines
    path: list = field(default_factory=list)    # path
    centre: tuple = (0.0, 0.0)                  # circle
    radius: float = 0.0
    inner_radius: float = 0.0                   # 0: only one circle was drawn
    start_angle: float = -math.pi / 2


# ---- The drawing as a planar graph ---------------------------------------------

def _graph(segments):
    """``(nodes, adjacency)``: ends welded, and every segment cut where
    another one touches or crosses it."""
    nodes: list = []
    grid: dict = {}

    def node(p):
        kx, ky = int(math.floor(p[0] / _WELD)), int(math.floor(p[1] / _WELD))
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for i in grid.get((kx + dx, ky + dy), ()):
                    if g.dist(nodes[i], p) <= _WELD:
                        return i
        nodes.append((p[0], p[1]))
        grid.setdefault((kx, ky), []).append(len(nodes) - 1)
        return len(nodes) - 1

    segs = [(a, b) for a, b in segments if g.dist(a, b) > _WELD]
    cuts = [[0.0, 1.0] for _ in segs]
    boxes = [(min(a[0], b[0]) - _WELD, min(a[1], b[1]) - _WELD,
              max(a[0], b[0]) + _WELD, max(a[1], b[1]) + _WELD)
             for a, b in segs]
    order = sorted(range(len(segs)), key=lambda i: boxes[i][0])
    for pos, i in enumerate(order):
        for j in order[pos + 1:]:
            if boxes[j][0] > boxes[i][2]:
                break
            if boxes[j][1] > boxes[i][3] or boxes[j][3] < boxes[i][1]:
                continue
            for one, other in ((i, j), (j, i)):
                a, b = segs[one]
                for p in segs[other]:
                    d, t = g.segment_distance(p, a, b)
                    if d <= _WELD and 1e-4 < t < 1 - 1e-4:
                        cuts[one].append(t)
            a, b = segs[i]
            c, d = segs[j]
            got = g.line_hit(a, g.sub(b, a), c, d)
            if got is not None and 1e-4 < got[0] < 1 - 1e-4 \
                    and 1e-4 < got[1] < 1 - 1e-4:
                cuts[i].append(got[0])
                cuts[j].append(got[1])
    adj: dict = {}
    for (a, b), ts in zip(segs, cuts):
        ids = [node(g.lerp(a, b, t)) for t in sorted(ts)]
        for u, v in zip(ids, ids[1:]):
            if u != v:
                adj.setdefault(u, set()).add(v)
                adj.setdefault(v, set()).add(u)
    return nodes, adj


def _components(adj):
    seen: set = set()
    for start in adj:
        if start in seen:
            continue
        stack, comp = [start], []
        seen.add(start)
        while stack:
            u = stack.pop()
            comp.append(u)
            for v in adj[u]:
                if v not in seen:
                    seen.add(v)
                    stack.append(v)
        yield comp


def _extent(nodes, ids):
    xs = [nodes[i][0] for i in ids]
    ys = [nodes[i][1] for i in ids]
    return math.hypot(max(xs) - min(xs), max(ys) - min(ys)) if ids else 0.0


def _core(adj):
    """The graph without its loose ends: what is left holds closed loops."""
    core = {u: set(vs) for u, vs in adj.items()}
    loose = [u for u, vs in core.items() if len(vs) < 2]
    while loose:
        u = loose.pop()
        for v in core.pop(u, ()):
            if v in core:
                core[v].discard(u)
                if len(core[v]) < 2:
                    loose.append(v)
    return core


def _outer_loop(nodes, adj, comp):
    """The outer boundary of a component, anticlockwise."""
    start = min(comp, key=lambda i: (nodes[i][1], nodes[i][0]))
    back = -math.pi / 2
    loop, u, first = [], start, None
    for _ in range(4 * len(comp) + 8):
        def key(v):
            a = math.atan2(nodes[v][1] - nodes[u][1],
                           nodes[v][0] - nodes[u][0])
            turn = (a - back) % math.tau
            return turn if turn > 1e-9 else math.tau
        v = min(adj[u], key=key)
        if (u, v) == first:
            return loop
        if first is None:
            first = (u, v)
        loop.append(u)
        back = math.atan2(nodes[u][1] - nodes[v][1],
                          nodes[u][0] - nodes[v][0])
        u = v
    raise PlanError("open_outline")


# ---- Circles -------------------------------------------------------------------

def _as_circle(points):
    """``(centre, radius)`` when the loop is a circle."""
    if len(points) < 12:
        return None
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    c = ((max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2)
    # a centre from three spread corners: exact for a drawn polygon
    n = len(points)
    a, b, d = points[0], points[n // 3], points[2 * n // 3]
    den = 2 * (a[0] * (b[1] - d[1]) + b[0] * (d[1] - a[1])
               + d[0] * (a[1] - b[1]))
    if abs(den) > 1e-9:
        sa, sb, sd = g.dot(a, a), g.dot(b, b), g.dot(d, d)
        c = ((sa * (b[1] - d[1]) + sb * (d[1] - a[1]) + sd * (a[1] - b[1])) / den,
             (sa * (d[0] - b[0]) + sb * (a[0] - d[0]) + sd * (b[0] - a[0])) / den)
    radii = [g.dist(p, c) for p in points]
    r = sum(radii) / len(radii)
    if r < 0.05 or max(abs(x - r) for x in radii) > max(0.004, r * 0.006):
        return None
    sides = [g.dist(points[i - 1], points[i]) for i in range(n)]
    if max(sides) > r * 0.6:
        return None
    return c, r


def _circle_plan(nodes, adj, centre, radius):
    plan = Plan("circle", centre=centre, radius=radius)
    inner: dict = {}
    radial = []
    for u in adj:
        for v in adj[u]:
            if u > v:
                continue
            a, b = nodes[u], nodes[v]
            ra, rb = g.dist(a, centre), g.dist(b, centre)
            e = g.unit(g.sub(b, a))
            off = abs(g.cross(e, g.sub(centre, a)))
            if off < 0.01 and abs(ra - rb) > 0.03:
                far = a if ra > rb else b
                radial.append((max(ra, rb), math.atan2(far[1] - centre[1],
                                                       far[0] - centre[0])))
            elif abs(ra - rb) < 0.004 and ra < radius - 0.05 and ra > 0.02 \
                    and off > ra * 0.8:
                inner.setdefault(round(ra, 2), []).append(ra)
    rings = [(len(v), sum(v) / len(v)) for v in inner.values() if len(v) >= 6]
    if rings:
        plan.inner_radius = max(rings)[1]
    if radial:
        plan.start_angle = max(radial)[1]
    return plan


# ---- Outline -------------------------------------------------------------------

def _split_loop(loop, i, j):
    """Taking edges ``i`` and ``j`` (edge k joins corner k and k+1) as the
    two ends of the stair: ``(right side, left side)``, both running from
    end ``i`` to end ``j``. ``loop`` is anticlockwise."""
    n = len(loop)
    first = [loop[k % n] for k in range(i + 1, i + 1 + ((j - i - 1) % n) + 1)]
    second = [loop[k % n] for k in range(j + 1, j + 1 + ((i - j - 1) % n) + 1)]
    second.reverse()
    return first, second


def _median(values):
    v = sorted(values)
    return v[len(v) // 2] if v else 0.0


def _samples(chain, count=24):
    return [chain.point(chain.length * (k + 0.5) / count) for k in range(count)]


def _score_ends(loop, i, j, chords):
    n = len(loop)
    a, b = _split_loop(loop, i, j)
    if len(a) < 2 or len(b) < 2:
        return None
    ca, cb = g.Chain(a), g.Chain(b)
    gaps = [cb.nearest(p)[0] for p in _samples(ca)] \
        + [ca.nearest(p)[0] for p in _samples(cb)]
    width = _median(gaps)
    if width < 0.15:
        return None
    spread = _median([abs(x - width) for x in gaps]) / width
    mean = sum(abs(x - width) for x in gaps) / len(gaps) / width
    ends = [g.dist(loop[i], loop[(i + 1) % n]),
            g.dist(loop[j], loop[(j + 1) % n])]
    score = spread + 0.5 * mean + sum(abs(e - width) / width for e in ends)
    run = (ca.length + cb.length) / 2
    if run < width * 1.15:
        score += 1.0 + (width * 1.15 - run) / width
    if chords:
        # drawn steps go from one side to the other
        good = sum(1 for p, q in chords
                   if _side_pair(ca, cb, p, q) is not None)
        score += 4.0 * (1.0 - good / len(chords))
    return score


def _side_pair(ca, cb, p, q, tol=0.012):
    """``(sa, sb)`` when the line ``p q`` joins the two chains."""
    for first, second in ((p, q), (q, p)):
        da, sa = ca.nearest(first)
        db, sb = cb.nearest(second)
        if da <= tol and db <= tol:
            return sa, sb
    return None


def _merge_collinear(segments, tol=0.004):
    """Pieces of one straight line that touch or overlap, as one again (a
    step line the walking arrow cut in two)."""
    items = [[a, b] for a, b in segments]
    merged = True
    while merged:
        merged = False
        for i in range(len(items)):
            a, b = items[i]
            d = g.unit(g.sub(b, a))
            for j in range(i + 1, len(items)):
                c, e = items[j]
                if abs(g.cross(d, g.sub(c, a))) > tol \
                        or abs(g.cross(d, g.sub(e, a))) > tol:
                    continue
                ts = [0.0, g.dist(a, b)]
                other = sorted((g.dot(g.sub(c, a), d), g.dot(g.sub(e, a), d)))
                if other[0] > ts[1] + tol or other[1] < ts[0] - tol:
                    continue
                lo, hi = min(ts[0], other[0]), max(ts[1], other[1])
                items[i] = [g.add(a, g.mul(d, lo)), g.add(a, g.mul(d, hi))]
                del items[j]
                merged = True
                break
            if merged:
                break
    return [(a, b) for a, b in items]


def _outline_plan(nodes, adj, comp, loop_ids, end_choice=0):
    raw = [nodes[i] for i in loop_ids]
    if len(set(loop_ids)) != len(loop_ids):
        raise PlanError("touching_outline")
    loop = g.simplify(raw, closed=True)
    n = len(loop)
    if n < 4:
        raise PlanError("no_ends")
    border = {frozenset((loop_ids[k - 1], loop_ids[k]))
              for k in range(len(loop_ids))}
    inside = [(nodes[u], nodes[v]) for u in comp for v in adj[u]
              if u < v and frozenset((u, v)) not in border]
    ring = list(zip(loop, loop[1:] + loop[:1]))
    chords = [c for c in _merge_collinear(inside) if g.dist(*c) > 0.2]

    turns = [g.turn_angle(loop[k - 1], loop[k], loop[(k + 1) % n])
             for k in range(n)]
    sharp = [k for k in range(n)
             if turns[k] > math.radians(35)
             and turns[(k + 1) % n] > math.radians(35)]
    if len(sharp) < 2:
        raise PlanError("no_ends")
    scored = []
    for x, i in enumerate(sharp):
        for j in sharp[x + 1:]:
            if (j - i) % n in (1, n - 1):
                continue
            score = _score_ends(loop, i, j, chords)
            if score is not None:
                scored.append((score, i, j))
    if not scored:
        raise PlanError("no_ends")
    scored.sort()
    _score, i, j = scored[end_choice % len(scored)]

    right, left = _split_loop(loop, i, j)
    # Where there is a choice, the stair starts at the lower (then the
    # leftmost) end; «reverse» in the panel swaps it.
    ei = g.lerp(loop[i], loop[(i + 1) % n], 0.5)
    ej = g.lerp(loop[j], loop[(j + 1) % n], 0.5)
    if (round(ej[1], 2), round(ej[0], 2)) < (round(ei[1], 2), round(ei[0], 2)):
        left, right = list(reversed(right)), list(reversed(left))
    plan = Plan("outline", left=left, right=right)
    ca, cb = g.Chain(left), g.Chain(right)
    for p, q in chords:
        got = _side_pair(ca, cb, p, q)
        if got is None:
            continue
        sa, sb = got
        if (sa < 0.02 and sb < 0.02) or (sa > ca.length - 0.02
                                         and sb > cb.length - 0.02):
            continue                                    # one of the ends
        plan.chords.append((sa, sb))
    plan.chords.sort(key=lambda c: c[0] + c[1])
    del ring
    return plan


# ---- Open line -----------------------------------------------------------------

def _longest_path(nodes, adj, comp):
    def far(start):
        best, parent, run = start, {start: None}, {start: 0.0}
        stack = [start]
        while stack:
            u = stack.pop()
            for v in adj[u]:
                if v not in run:
                    run[v] = run[u] + g.dist(nodes[u], nodes[v])
                    parent[v] = u
                    stack.append(v)
                    if run[v] > run[best]:
                        best = v
        return best, parent

    a, _ = far(comp[0])
    b, parent = far(a)
    out = []
    while b is not None:
        out.append(nodes[b])
        b = parent[b]
    return out


# ---- The whole ------------------------------------------------------------------

def analyse(segments, end_choice: int = 0) -> Plan:
    """The :class:`Plan` of ``segments`` (``[((x, y), (x, y))]``).
    ``end_choice``: for a contour that could be walked more than one way,
    which pair of ends (0 = the likeliest)."""
    nodes, adj = _graph(segments)
    if not adj:
        raise PlanError("empty")
    whole = _extent(nodes, list(adj))
    core = _core(adj)
    loops = sorted(_components(core), key=lambda c: -_extent(nodes, c))
    if loops and _extent(nodes, loops[0]) > 0.45 * whole:
        comp = loops[0]
        ids = _outer_loop(nodes, core, comp)
        circle = _as_circle([nodes[i] for i in ids])
        if circle is not None:
            return _circle_plan(nodes, adj, *circle)
        return _outline_plan(nodes, core, comp, ids, end_choice)
    comp = max(_components(adj), key=lambda c: _extent(nodes, c))
    path = g.simplify(_longest_path(nodes, adj, comp))
    if len(path) < 2 or _extent(nodes, comp) < 0.3:
        raise PlanError("empty")
    run = g.Chain(path).length
    if len(path) > 3 and g.dist(path[0], path[-1]) < min(0.15, run / 8):
        raise PlanError("not_closed")        # a contour left a little open
    # from the lower (then leftmost) end
    if (round(path[-1][1], 2), round(path[-1][0], 2)) \
            < (round(path[0][1], 2), round(path[0][0], 2)):
        path.reverse()
    return Plan("path", path=path)


def group_segments(group):
    """``(segments, z, flat)`` of a group's lines, nested ones included:
    its plan, its height and whether it lies in one plane."""
    from PySide6.QtGui import QVector3D

    from core.group import iter_placements
    segments, zs = [], []
    for part, matrix in iter_placements(group):
        for e in part.mesh.edges:
            a, b = QVector3D(e.a), QVector3D(e.b)
            if matrix is not None:
                a, b = matrix.map(a), matrix.map(b)
            zs += [a.z(), b.z()]
            if math.hypot(a.x() - b.x(), a.y() - b.y()) > _WELD:
                segments.append(((a.x(), a.y()), (b.x(), b.y())))
    if not segments:
        raise PlanError("empty")
    zs.sort()
    return segments, zs[0], zs[-1] - zs[0] < 0.01
