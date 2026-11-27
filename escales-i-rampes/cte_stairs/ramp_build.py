# SPDX-License-Identifier: GPL-3.0-or-later
"""A ramp as geometry, with the same three constructions as a stair.

Everything is a *ribbon*: a body between two sides, given by lines across
it with a bottom and a top height. The solid ramp, the concrete slab, the
deck of a steel ramp and each stringer are ribbons.
"""
from __future__ import annotations

import math

from . import geom as g
from .build import (_ABOVE, Build, Shell, _column, _inset, _interp,
                    _on_chain, _profile, _samples, _xyz)


def _ribbon(name: str, chains, lines) -> Shell:
    """``lines`` = ``[(u, v, bottom, top)]`` from one end to the other.
    Sides and lines may bend; where bottom and top meet, the body ends in
    an edge."""
    shell = Shell(name)
    tops = [_profile([(ln[side], ln[3]) for ln in lines], max)
            for side in (0, 1)]
    lows = [_profile([(ln[side], ln[2]) for ln in lines], min)
            for side in (0, 1)]

    def points(side, table, s0, s1):
        chain = chains[side]
        both = tops[side] + lows[side]
        return [_xyz(chain.point(s), _interp(table[side], s))
                for s in _samples(chain, both, s0, s1)]

    for a, b in zip(lines, lines[1:]):
        shell.surface([points(1, tops, a[1], b[1]),
                       points(0, tops, a[0], b[0])], 0.2)
        shell.surface([points(0, lows, a[0], b[0]),
                       points(1, lows, a[1], b[1])], 0.2)
    # A line across is drawn only where the slope changes: the others are
    # just how a curved or twisted surface is cut into flat pieces.
    middles = [g.lerp(chains[0].point(ln[0]), chains[1].point(ln[1]), 0.5)
               for ln in lines]
    for k in range(1, len(lines) - 1):
        ln = lines[k]
        for column, tables in ((3, tops), (2, lows)):
            before, after = (
                (lines[j + 1][column] - lines[j][column])
                / max(g.dist(middles[j], middles[j + 1]), 1e-6)
                for j in (k - 1, k))
            if abs(after - before) > 0.35 * max(abs(before), abs(after),
                                                0.01):
                continue
            shell.seams.append((
                _xyz(chains[0].point(ln[0]), _interp(tables[0], ln[0])),
                _xyz(chains[1].point(ln[1]), _interp(tables[1], ln[1])),
                0.2))
    for side, chain in enumerate(chains):
        for p, q in zip(chain.cum, chain.cum[1:]):
            inner = {s for s, _z in tops[side] + lows[side]
                     if p + 1e-5 < s < q - 1e-5}
            stops = [p] + sorted(inner) + [q]
            ring = [_xyz(chain.point(s), _interp(lows[side], s))
                    for s in stops]
            ring += [_xyz(chain.point(s), _interp(tops[side], s))
                     for s in reversed(stops)]
            shell.face(ring if side == 1 else list(reversed(ring)))
    for end, ln in ((0, lines[0]), (1, lines[-1])):
        a, c = chains[0].point(ln[0]), chains[1].point(ln[1])
        left = [_interp(lows[0], ln[0]), _interp(tops[0], ln[0])]
        right = [_interp(lows[1], ln[1]), _interp(tops[1], ln[1])]
        if end == 0:
            shell.face([_xyz(a, left[0]), _xyz(c, right[0]),
                        _xyz(c, right[1]), _xyz(a, left[1])])
        else:
            shell.face([_xyz(c, right[0]), _xyz(a, left[0]),
                        _xyz(a, left[1]), _xyz(c, right[1])])
    return shell


def _clipped(chains, lines, floor, ceiling) -> list:
    """``lines`` with the heights held between floor and ceiling, and a line
    more wherever one of them starts to be held."""
    out = []
    for i, ln in enumerate(lines):
        out.append(ln)
        if i + 1 == len(lines):
            break
        nxt = lines[i + 1]
        cuts = []
        for column, limit in ((2, floor), (3, floor), (2, ceiling),
                              (3, ceiling)):
            if (ln[column] - limit) * (nxt[column] - limit) < -1e-10:
                cuts.append((limit - ln[column]) / (nxt[column] - ln[column]))
        for f in sorted(cuts):
            mixed = [a + (c - a) * f for a, c in zip(ln, nxt)]
            mixed[0] = chains[0].snap_to_corner(mixed[0])
            mixed[1] = chains[1].snap_to_corner(mixed[1])
            out.append(tuple(mixed))
    return [(u, v, max(floor, min(ceiling, low)),
             max(floor, min(ceiling, top))) for u, v, low, top in out]


def _lines(ramp, z0, thickness) -> list:
    """``[(u, v, bottom, top)]``; ``thickness`` square to the slope, or
    ``None`` for solid down to the floor."""
    if thickness is None:
        return [(u, v, z0, z0 + rise) for u, v, _s, rise in ramp.lines]
    drop = thickness * math.hypot(1.0, ramp.slope)
    return [(u, v, z0 + rise - drop, z0 + rise)
            for u, v, _s, rise in ramp.lines]


def _stringer(ramp, z0, build, side, inner: g.Chain) -> Shell:
    outer = (ramp.left, ramp.right)[side]
    table = _profile([(ln[side], ln[3]) for ln in ramp.lines], max)
    depth = max(build.depth, _ABOVE + build.tread + 0.01)
    reach = 2.5 * build.plate + 0.004
    positions = [s for s, _z in table
                 if all(abs(s - c) > reach for c in outer.cum)]
    positions = sorted(positions + list(outer.cum))
    lines = []
    for s in positions:
        corner = next((i for i, c in enumerate(outer.cum)
                       if abs(c - s) < 1e-6), None)
        if corner is not None:               # mitred corners stay paired
            across = inner.cum[corner]
        else:
            j = outer.segment_at(s)
            a, b = inner.pts[j], inner.pts[j + 1]
            _d, t = g.segment_distance(outer.point(s), a, b)
            across = inner.cum[j] + t * (inner.cum[j + 1] - inner.cum[j])
        top = z0 + _interp(table, s) + _ABOVE
        pair = (s, across) if side == 0 else (across, s)
        lines.append((pair[0], pair[1], top - depth, top))
    chains = (outer, inner) if side == 0 else (inner, outer)
    lines = _clipped(chains, lines, z0, z0 + ramp.height + _ABOVE)
    return _ribbon("plate left" if side == 0 else "plate right", chains,
                   lines)


def ramp_shells(ramp, z0: float, build: Build) -> list:
    """The parts of a ramp: one body, or stringers with a deck between."""
    ceiling = z0 + ramp.height
    chains = (ramp.left, ramp.right)
    if build.kind in ("solid", "slab"):
        lines = _lines(ramp, z0,
                       None if build.kind == "solid" else build.slab)
        parts = [_ribbon("body", chains,
                         _clipped(chains, lines, z0, ceiling))]
    else:
        wanted = [side for side, key in ((0, "left"), (1, "right"))
                  if build.sides in ("both", key)]
        if ramp.column > 0:
            wanted = [side for side in wanted
                      if g.dist(chains[side].pts[0], ramp.centre)
                      > ramp.column + 0.01]
        moved = [_inset(ramp, side, build.plate if side in wanted else 0.0)
                 for side in (0, 1)]
        inner = [g.Chain(points) for points in moved]
        deck = []
        for k, (_u, _v, low, top) in enumerate(_lines(ramp, z0, build.tread)):
            if k == 0:
                u, v = 0.0, 0.0
            elif k == ramp.count - 1:
                u, v = inner[0].length, inner[1].length
            else:
                a, b = ramp.line(k)
                d = g.sub(b, a)
                u = _on_chain(inner[0], a, d, a)
                v = _on_chain(inner[1], a, d, b)
                u, v = max(u, deck[-1][0]), max(v, deck[-1][1])
            deck.append((u, v, low, top))
        parts = [_ribbon("deck", inner,
                         _clipped(inner, deck, z0, ceiling))]
        for side in wanted:
            if len(inner[side].pts) == len(chains[side].pts):
                parts.append(_stringer(ramp, z0, build, side, inner[side]))
    if ramp.column > 0:
        parts.append(_column(ramp, z0))
    return [p for p in parts if p.faces]
