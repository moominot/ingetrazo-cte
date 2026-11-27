# SPDX-License-Identifier: GPL-3.0-or-later
"""The stair as geometry, from a :class:`~stairs.layout.Layout`.

Every part is first a :class:`Shell` — a list of outward-wound polygons —
and only then a mesh, so it can be checked and previewed as it is.

* **solid**: all there is under the steps, down to the floor;
* **slab**: a concrete slab under the steps, its soffit sloping with them;
* **plates**: two (or one) flat steel stringers at the sides, with treads
  between them and, if wanted, riser plates.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from . import geom as g
from .layout import Layout

KEY = "cte_stairs"
_EPS = 1e-6
#: How far above the line of the nosings a stringer plate's top runs.
_ABOVE = 0.05


@dataclass
class Build:
    kind: str = "solid"            # "solid" | "slab" | "plates"
    slab: float = 0.15             # concrete: thickness square to the slope
    tread: float = 0.04            # plates: tread thickness
    risers: bool = False           # plates: with riser plates
    plate: float = 0.012           # plates: thickness of stringers and risers
    depth: float = 0.30            # plates: height of the stringer
    sides: str = "both"            # plates: "both" | "left" | "right"


class Shell:
    def __init__(self, name: str) -> None:
        self.name = name
        self.faces: list = []      # [[(x, y, z), ...]]
        self.seams: list = []      # [(a, b, limit)]: soft when flat enough

    def face(self, points) -> None:
        out: list = []
        for p in points:
            if not out or math.dist(p, out[-1]) > 1e-5:
                out.append(p)
        if len(out) > 1 and math.dist(out[0], out[-1]) <= 1e-5:
            out.pop()
        if len(out) >= 3 and _area(out) > 1e-9:
            self.faces.append(out)

    def surface(self, points, seam_limit=0.9) -> None:
        """A face between two sides that may be warped: ``points`` is
        ``(first side forward, second side forward)``; flat, it is one
        face, else triangles whose inner edges are softened. Wound as
        ``first forward + second backward``."""
        first, second = points
        whole = list(first) + list(reversed(second))
        if _flat(whole):
            self.face(whole)
            return
        i = j = 0
        n = 0
        while i < len(first) - 1 or j < len(second) - 1:
            if j >= len(second) - 1:
                left = True
            elif i >= len(first) - 1:
                left = False
            else:
                left = math.dist(first[i + 1], second[j]) \
                    <= math.dist(first[i], second[j + 1])
            if n:
                self.seams.append((first[i], second[j], seam_limit))
            if left:
                self.face([first[i], first[i + 1], second[j]])
                i += 1
            else:
                self.face([first[i], second[j + 1], second[j]])
                j += 1
            n += 1

    def prism(self, polygon, z0: float, z1: float) -> None:
        """``polygon`` (plan, anticlockwise) from ``z0`` up to ``z1``."""
        if len(polygon) < 3 or z1 - z0 < 1e-4:
            return
        self.face([(x, y, z1) for x, y in polygon])
        self.face([(x, y, z0) for x, y in reversed(polygon)])
        for a, b in zip(polygon, polygon[1:] + polygon[:1]):
            self.face([(a[0], a[1], z0), (b[0], b[1], z0),
                       (b[0], b[1], z1), (a[0], a[1], z1)])


def _normal(points):
    nx = ny = nz = 0.0
    for (x0, y0, z0), (x1, y1, z1) in zip(points, points[1:] + points[:1]):
        nx += (y0 - y1) * (z0 + z1)
        ny += (z0 - z1) * (x0 + x1)
        nz += (x0 - x1) * (y0 + y1)
    return nx, ny, nz


def _area(points):
    return 0.5 * math.sqrt(sum(c * c for c in _normal(points)))


def _flat(points, tol=2e-5):
    n = _normal(points)
    size = math.sqrt(sum(c * c for c in n))
    if size < 1e-12:
        return False
    n = [c / size for c in n]
    p0 = points[0]
    return all(abs(sum(n[i] * (p[i] - p0[i]) for i in range(3))) < tol
               for p in points)


def _xyz(p, z):
    return (p[0], p[1], z)


# ---- Profiles along a side -------------------------------------------------------

def _interp(table, s):
    """``table`` = ``[(s, z)]`` in order of ``s``."""
    if s <= table[0][0]:
        return table[0][1]
    for (s0, z0), (s1, z1) in zip(table, table[1:]):
        if s <= s1:
            return z0 + (z1 - z0) * ((s - s0) / (s1 - s0) if s1 > s0 else 1.0)
    return table[-1][1]


def _profile(pairs, pick) -> list:
    """One height for each position: ``pick`` of the ones given for it."""
    out: list = []
    for s, z in sorted(pairs):
        if out and s - out[-1][0] < 1e-5:
            out[-1] = (out[-1][0], pick(out[-1][1], z))
        else:
            out.append((s, z))
    return out


def _samples(chain, table, s0, s1) -> list:
    """The positions between ``s0`` and ``s1`` where a side has a point:
    the profile's and the chain's own corners."""
    inner = {s for s, _z in table if s0 + 1e-5 < s < s1 - 1e-5}
    for c in chain.cum:
        if s0 + 1e-5 < c < s1 - 1e-5 \
                and not any(abs(c - s) < 1e-5 for s in inner):
            inner.add(c)
    return [s0] + sorted(inner) + ([s1] if s1 > s0 + 1e-5 else [])


# ---- Solid and slab -------------------------------------------------------------------

def _soffit(layout: Layout, z0: float, build: Build) -> list:
    """``[(u, v, z)]``: lines across the underside of the concrete slab."""
    h = layout.riser
    going = max(layout.going, 0.05)
    drop = build.slab / math.cos(math.atan2(h, going))
    raw = []
    for k in range(layout.count):
        u, v = layout.risers[k]
        # A landing is flat underneath, level with the flight that reaches
        # it; the next flight leaves from there (its first step a haunch).
        level = k - 1 if k - 1 in layout.landings and k > 1 else k
        raw.append((u, v, z0 + level * h - drop))
    out = []
    for i, (u, v, z) in enumerate(raw):
        out.append((u, v, max(z0, z)))
        if i + 1 < len(raw) and z < z0 < raw[i + 1][2]:
            u1, v1, z1 = raw[i + 1]
            f = (z0 - z) / (z1 - z)
            out.append((layout.left.snap_to_corner(u + (u1 - u) * f),
                        layout.right.snap_to_corner(v + (v1 - v) * f), z0))
    return _without_needless(layout, out)


def _without_needless(layout, lines) -> list:
    """Without the lines the underside runs straight through: a straight
    flight is one face."""
    i = 1
    while i + 1 < len(lines):
        a, b, c = lines[i - 1], lines[i], lines[i + 1]
        keep = False
        for side, chain in ((0, layout.left), (1, layout.right)):
            span = c[side] - a[side]
            if span < 1e-5 or not a[side] + 1e-5 < b[side] < c[side] - 1e-5:
                keep = True
                break
            f = (b[side] - a[side]) / span
            if abs(a[2] + (c[2] - a[2]) * f - b[2]) > 1e-5:
                keep = True
                break
            if any(a[side] + 1e-5 < x < c[side] - 1e-5 for x in chain.cum):
                keep = True
                break
        if keep:
            i += 1
        else:
            del lines[i]
    return lines


def _body(layout: Layout, z0: float, build: Build, name: str) -> Shell:
    shell = Shell(name)
    h, n = layout.riser, layout.count
    top = z0 + (n - 1) * h
    if build.kind == "slab":
        lines = _soffit(layout, z0, build)
    else:
        lines = [(0.0, 0.0, z0),
                 (layout.left.length, layout.right.length, z0)]
    chains = (layout.left, layout.right)
    under = [_profile([(ln[side], ln[2]) for ln in lines], min)
             for side in (0, 1)]

    def levels_at(side, s) -> list:
        """The heights where something meets the side's upright at ``s``."""
        zs = [_interp(under[side], s)]
        for k in range(n - 1):
            if abs(layout.risers[k][side] - s) < 1e-5:
                zs += [z0 + k * h, z0 + (k + 1) * h]
        return zs

    # the steps
    for k in range(n - 1):
        z = z0 + (k + 1) * h
        shell.face([(x, y, z) for x, y in layout.tread_polygon(k)])
        a, b = layout.line(k)
        low = z0 + k * h
        shell.face([_xyz(a, low), _xyz(b, low), _xyz(b, z), _xyz(a, z)])

    # the two sides, a face for each straight stretch
    for side, chain in enumerate(chains):
        positions = [layout.risers[k][side] for k in range(n - 1)]
        for p, q in zip(chain.cum, chain.cum[1:]):
            first = z0 + h * sum(1 for r in positions if r <= p + 1e-5)
            last = z0 + h * sum(1 for r in positions if r < q - 1e-5)
            bottom = [p] + [s for s, _z in under[side]
                            if p + 1e-5 < s < q - 1e-5] + [q]
            ring = [(s, _interp(under[side], s)) for s in bottom]
            ring += [(q, z) for z in sorted(set(levels_at(side, q)))
                     if ring[-1][1] + 1e-5 < z < last - 1e-5]
            ring.append((q, last))
            for k in range(n - 2, -1, -1):
                r = positions[k]
                if p + 1e-5 < r < q - 1e-5:
                    ring += [(r, z0 + (k + 1) * h), (r, z0 + k * h)]
            ring.append((p, first))
            low = _interp(under[side], p)
            ring += [(p, z) for z in sorted(set(levels_at(side, p)),
                                            reverse=True)
                     if low + 1e-5 < z < first - 1e-5]
            points = [_xyz(chain.point(s), z) for s, z in ring]
            shell.face(points if side == 1 else list(reversed(points)))

    # the underside
    if build.kind == "slab":
        for a, b in zip(lines, lines[1:]):
            sides = []
            for side, chain in enumerate(chains):
                ss = _samples(chain, under[side], a[side], b[side])
                sides.append([_xyz(chain.point(s), _interp(under[side], s))
                              for s in ss])
            shell.surface(sides, 0.97)
        for line in lines[1:-1]:
            shell.seams.append((
                _xyz(layout.left.point(line[0]), _interp(under[0], line[0])),
                _xyz(layout.right.point(line[1]), _interp(under[1], line[1])),
                0.985))
    else:
        left = [_xyz(p, z0) for p in layout.left.pts]
        right = [_xyz(p, z0) for p in layout.right.pts]
        shell.face(left + list(reversed(right)))

    # the far end
    a, b = layout.line(n - 1)
    ends = []
    for side, s in ((0, layout.left.length), (1, layout.right.length)):
        zs = sorted({z for z in levels_at(side, s) if z < top - 1e-5})
        ends.append(zs + [top])
    shell.face([_xyz(b, ends[1][0]), _xyz(a, ends[0][0])]
               + [_xyz(a, z) for z in ends[0][1:]]
               + [_xyz(b, z) for z in reversed(ends[1][1:])])
    return shell


# ---- Plates and treads --------------------------------------------------------------------

def _inset(layout: Layout, side: int, distance: float) -> list:
    """The side's points moved ``distance`` into the stair, its two ends
    kept on the end lines."""
    chain = (layout.left, layout.right)[side]
    if distance <= 0.0:
        return list(chain.pts)
    pts = g.offset_polyline(chain.pts, -distance if side == 0 else distance)
    for end, k in ((0, 0), (-1, layout.count - 1)):
        a, b = layout.line(k)
        near, nxt = pts[end], pts[1 if end == 0 else -2]
        d = g.sub(nxt, near)
        e = g.sub(b, a)
        den = g.cross(d, e)
        if abs(den) > 1e-9:
            pts[end] = g.add(near, g.mul(d, g.cross(g.sub(a, near), e) / den))
    return pts


def _on_chain(chain: g.Chain, origin, direction, near) -> float:
    """Where the line through ``origin`` crosses ``chain``, closest to the
    point ``near``."""
    best = None
    for i, (a, b) in enumerate(zip(chain.pts, chain.pts[1:])):
        got = g.line_hit(origin, direction, a, b)
        if got is None:
            continue
        s = chain.cum[i] + got[1] * (chain.cum[i + 1] - chain.cum[i])
        d = g.dist(chain.point(s), near)
        if best is None or d < best[0]:
            best = (d, s)
    if best is None or best[0] > 0.5:
        return chain.nearest(near)[1]
    return chain.snap_to_corner(best[1])


def _treads(layout, z0, build, inner) -> list:
    h, n = layout.riser, layout.count
    cuts = []
    for k in range(n):
        a, b = layout.line(k)
        d = g.sub(b, a)
        cuts.append((_on_chain(inner[0], a, d, a),
                     _on_chain(inner[1], a, d, b)))
    parts = []
    thick = min(build.tread, h - 0.01)
    for k in range(n - 1):
        (u0, v0), (u1, v1) = cuts[k], cuts[k + 1]
        polygon = g.dedupe(
            inner[1].between(v0, max(v0, v1))
            + list(reversed(inner[0].between(u0, max(u0, u1)))),
            1e-5, closed=True)
        shell = Shell(f"tread {k + 1}")
        z = z0 + (k + 1) * h
        shell.prism(polygon, z - thick, z)
        parts.append(shell)
    if build.risers:
        for k in range(n):
            a = inner[0].point(cuts[k][0])
            b = inner[1].point(cuts[k][1])
            across = g.unit(g.sub(a, b))
            ahead = (across[1], -across[0])
            # under the front of its own tread; the last one, which meets
            # the upper floor, behind its line
            step = g.mul(ahead, build.plate if k < n - 1 else -build.plate)
            moved = g.add(a, step)
            a1 = inner[0].point(_on_chain(inner[0], moved, across, moved))
            moved = g.add(b, step)
            b1 = inner[1].point(_on_chain(inner[1], moved, across, moved))
            polygon = [b, b1, a1, a] if k < n - 1 else [b1, b, a, a1]
            shell = Shell(f"riser {k + 1}")
            top = z0 + (k + 1) * h - (thick if k < n - 1 else 0.0)
            shell.prism(g.dedupe(polygon, 1e-5, closed=True), z0 + k * h, top)
            parts.append(shell)
    return parts


def _plate(layout, z0, build, side, inner_points) -> Shell:
    shell = Shell("plate left" if side == 0 else "plate right")
    chain = (layout.left, layout.right)[side]
    h, n = layout.riser, layout.count
    ceiling = z0 + layout.height
    depth = max(build.depth, _ABOVE + h + build.tread + 0.01)
    going = max(layout.going, 0.05)
    nosing = []
    for k in range(n):
        u = layout.risers[k][side]
        nosing.append((u, z0 + (k + 1) * h + _ABOVE))
        if k < n - 1 and k in layout.landings:
            span = layout.stations[k + 1] - layout.stations[k]
            if span > going * 1.05:
                u1 = layout.risers[k + 1][side]
                nosing.append((u + (u1 - u) * (1 - going / span),
                               z0 + (k + 1) * h + _ABOVE))
    upper = _profile(nosing, max)
    lower = [(s, z - depth) for s, z in _profile(nosing, min)]

    positions = {round(s, 6) for s, _z in upper} \
        | {round(s, 6) for s, _z in lower}
    # where the plate meets the floor below or the one above
    for table, limit in ((upper, ceiling), (lower, z0)):
        for (s0, a), (s1, b) in zip(table, table[1:]):
            if (a - limit) * (b - limit) < -1e-12:
                positions.add(round(s0 + (s1 - s0) * (limit - a) / (b - a), 6))
    # too near a corner, a point would fold the mitred inner face on itself
    reach = 2.5 * build.plate + 0.004
    positions = sorted(s for s in positions
                       if all(abs(s - c) > reach for c in chain.cum)
                       and 0 < s < chain.length)

    def heights(s):
        top = min(ceiling, _interp(upper, s))
        bottom = max(z0, _interp(lower, s))
        return bottom, top

    def inside(s, i):
        """The inner face's point across from ``s`` on stretch ``i``."""
        a, b = inner_points[i], inner_points[i + 1]
        _d, t = g.segment_distance(chain.point(s), a, b)
        return g.lerp(a, b, t)

    runs = []
    for i, (p, q) in enumerate(zip(chain.cum, chain.cum[1:])):
        run = [(p, chain.pts[i], inner_points[i]) + heights(p)]
        run += [(s, chain.point(s), inside(s, i)) + heights(s)
                for s in positions if p + 1e-5 < s < q - 1e-5]
        run.append((q, chain.pts[i + 1], inner_points[i + 1]) + heights(q))
        # drop the points the edges run straight through
        j = 1
        while j + 1 < len(run):
            a, b, c = run[j - 1], run[j], run[j + 1]
            f = (b[0] - a[0]) / (c[0] - a[0])
            if abs(a[3] + (c[3] - a[3]) * f - b[3]) < 1e-5 \
                    and abs(a[4] + (c[4] - a[4]) * f - b[4]) < 1e-5:
                del run[j]
            else:
                j += 1
        runs.append(run)

    for run in runs:
        outer_top = [_xyz(r[1], r[4]) for r in run]
        outer_low = [_xyz(r[1], r[3]) for r in run]
        inner_top = [_xyz(r[2], r[4]) for r in run]
        inner_low = [_xyz(r[2], r[3]) for r in run]
        if side == 0:
            left_top, left_low = outer_top, outer_low
            right_top, right_low = inner_top, inner_low
        else:
            left_top, left_low = inner_top, inner_low
            right_top, right_low = outer_top, outer_low
        shell.face(left_top + list(reversed(left_low)))
        shell.face(right_low + list(reversed(right_top)))
        for j in range(len(run) - 1):
            shell.surface((right_top[j:j + 2], left_top[j:j + 2]))
            shell.surface((left_low[j:j + 2], right_low[j:j + 2]))
        for j in range(1, len(run) - 1):
            shell.seams.append((left_top[j], right_top[j], 0.985))
            shell.seams.append((left_low[j], right_low[j], 0.985))

    for end, run, j in ((0, runs[0], 0), (1, runs[-1], -1)):
        r = run[j]
        a, b = (r[1], r[2]) if side == 0 else (r[2], r[1])    # left, right
        if end == 0:
            shell.face([_xyz(a, r[3]), _xyz(b, r[3]),
                        _xyz(b, r[4]), _xyz(a, r[4])])
        else:
            shell.face([_xyz(b, r[3]), _xyz(a, r[3]),
                        _xyz(a, r[4]), _xyz(b, r[4])])
    return shell


def _column(layout: Layout, z0: float) -> Shell:
    shell = Shell("column")
    cx, cy = layout.centre
    r = layout.column
    ring = [(cx + r * math.cos(math.tau * i / 24),
             cy + r * math.sin(math.tau * i / 24)) for i in range(24)]
    shell.prism(ring, z0, z0 + layout.height)
    for x, y in ring:
        shell.seams.append(((x, y, z0), (x, y, z0 + layout.height), 0.9))
    return shell


def shells(layout: Layout, z0: float, build: Build) -> list:
    """The stair's parts."""
    if build.kind in ("solid", "slab"):
        parts = [_body(layout, z0, build, "body")]
    else:
        wanted = [side for side, key in ((0, "left"), (1, "right"))
                  if build.sides in ("both", key)]
        if layout.column > 0:        # the post holds the treads: no stringer
            wanted = [side for side in wanted
                      if g.dist((layout.left, layout.right)[side].pts[0],
                                layout.centre) > layout.column + 0.01]
        moved = [_inset(layout, side, build.plate if side in wanted else 0.0)
                 for side in (0, 1)]
        inner = [g.Chain(points) for points in moved]
        parts = _treads(layout, z0, build, inner)
        parts += [_plate(layout, z0, build, side, moved[side])
                  for side in wanted]
    if layout.column > 0:
        parts.append(_column(layout, z0))
    return [p for p in parts if p.faces]


# ---- Into the model ----------------------------------------------------------------------------

def mesh_of(shell: Shell):
    from PySide6.QtGui import QVector3D

    from core.mesh import Mesh
    mesh = Mesh()
    for points in shell.faces:
        mesh.add_face([QVector3D(*p) for p in points])
    for a, b, limit in shell.seams:
        va, vb = mesh.vertex_at(QVector3D(*a)), mesh.vertex_at(QVector3D(*b))
        if va is None or vb is None or va is vb:
            continue
        edge = mesh.find_edge(va, vb)
        if edge is None or len(edge.faces) != 2:
            continue
        one, two = (f.normal().normalized() for f in edge.faces)
        if QVector3D.dotProduct(one, two) > limit:
            edge.soft = True
    _soften_curves(mesh)
    return mesh


def _soften_curves(mesh) -> None:
    """The upright edges where a curved side goes from one facet to the
    next."""
    from PySide6.QtGui import QVector3D
    for e in mesh.edges:
        if len(e.faces) != 2:
            continue
        d = e.b - e.a
        if math.hypot(d.x(), d.y()) > 1e-4:
            continue
        one, two = (f.normal().normalized() for f in e.faces)
        if abs(one.z()) < 0.01 and abs(two.z()) < 0.01 \
                and QVector3D.dotProduct(one, two) > 0.96:
            e.soft = True


def group_of(parts, name: str, part_name, info=None):
    """One group: the stair's only mesh, or a container of its parts.
    ``part_name(key)`` names a part ("tread 3" -> «Graó 3»)."""
    from PySide6.QtGui import QMatrix4x4

    from core.group import Group
    from core.mesh import Mesh
    if len(parts) == 1:
        group = Group(mesh_of(parts[0]), name=name)
    else:
        children = []
        for part in parts:
            child = Group(mesh_of(part), name=part_name(part.name))
            child.xform = QMatrix4x4()
            child.component = False
            children.append(child)
        group = Group(Mesh(), name=name)
        group.adopt(children)
        group.component = False
    if info is not None:
        group.ext = {KEY: info}
    return group


def preview_of(parts) -> tuple:
    """``(faces, lines)`` to draw before the stair exists."""
    from PySide6.QtGui import QVector3D

    from core.geometry import Face
    faces, lines, seen = [], [], set()
    for part in parts:
        soft = {_edge_key(a, b) for a, b, _limit in part.seams}
        for points in part.faces:
            faces.append(Face([QVector3D(*p) for p in points]))
            for a, b in zip(points, points[1:] + points[:1]):
                key = _edge_key(a, b)
                if key not in seen and key not in soft:
                    seen.add(key)
                    lines.append((QVector3D(*a), QVector3D(*b)))
    return faces, lines


def _edge_key(a, b):
    ka = tuple(round(c, 4) for c in a)
    kb = tuple(round(c, 4) for c in b)
    return (ka, kb) if ka <= kb else (kb, ka)
