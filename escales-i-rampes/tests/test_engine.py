"""The stairs read from each kind of plan, and every part a closed solid.

    INGETRAZO_SRC=<IngeTrazo source> python -m pytest tests
"""
import math
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.environ.get("INGETRAZO_SRC", "."))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import plans  # noqa: E402
from core.solids import solid_report  # noqa: E402
from cte_stairs import build, geom, layout, plan  # noqa: E402

SHAPES = ["STRAIGHT", "L_SHAPE", "U_SHAPE", "S_SHAPE", "CURVED", "DRAWN",
          "DRAWN_WINDERS", "PATH_L", "PATH_ARC", "HELIX_TWO", "HELIX_ONE"]

BUILDS = {
    "solid": build.Build("solid"),
    "slab": build.Build("slab"),
    "plates": build.Build("plates"),
    "plates_risers": build.Build("plates", risers=True),
    "one_plate": build.Build("plates", risers=True, sides="left"),
}


def read(name):
    return plan.analyse(getattr(plans, name))


def options(name, **kw):
    kw.setdefault("height", 2.8)
    if name.startswith("HELIX"):
        kw.setdefault("helix_turn", 330)      # under one turn: no overlap
    return layout.Options(**kw)


@pytest.mark.parametrize("name,kind", [
    ("STRAIGHT", "outline"), ("L_SHAPE", "outline"), ("U_SHAPE", "outline"),
    ("S_SHAPE", "outline"), ("CURVED", "outline"), ("DRAWN", "outline"),
    ("DRAWN_WINDERS", "outline"), ("PATH_L", "path"), ("PATH_ARC", "path"),
    ("HELIX_TWO", "circle"), ("HELIX_ONE", "circle")])
def test_kind(name, kind):
    assert read(name).kind == kind


@pytest.mark.parametrize("name", SHAPES)
@pytest.mark.parametrize("turns", ["landing", "winders"])
@pytest.mark.parametrize("flip", [False, True])
@pytest.mark.parametrize("what", list(BUILDS))
def test_closed_solids(name, turns, flip, what):
    got = layout.compute(read(name), options(name, turns=turns, flip=flip))
    for part in build.shells(got, 0.0, BUILDS[what]):
        ok, volume = solid_report(build.mesh_of(part))
        assert ok, f"{part.name} is not closed"
        assert volume > 0


@pytest.mark.parametrize("name", SHAPES)
@pytest.mark.parametrize("turns", ["landing", "winders"])
def test_steps_make_sense(name, turns):
    got = layout.compute(read(name), options(name, turns=turns))
    assert got.riser == pytest.approx(2.8 / got.count)
    previous = (-1.0, -1.0)
    for u, v in got.risers:
        assert u >= previous[0] - 1e-6 and v >= previous[1] - 1e-6
        previous = (u, v)
    assert got.stations == sorted(got.stations)
    for k in range(got.count - 1):
        polygon = got.tread_polygon(k)
        area = 0.5 * sum(geom.cross(a, b) for a, b in
                         zip(polygon, polygon[1:] + polygon[:1]))
        assert area > 0.005, f"tread {k} has no room"


def test_straight_follows_the_rule():
    got = layout.compute(read("STRAIGHT"), options("STRAIGHT"))
    assert layout.RULE_MIN <= got.rule <= layout.RULE_MAX
    assert got.count == 16
    assert got.going == pytest.approx(4.48 / 15, abs=1e-3)


def test_steps_typed_win_over_the_rule_and_the_drawing():
    assert layout.compute(read("STRAIGHT"),
                          options("STRAIGHT", steps=15)).count == 15
    assert layout.compute(read("DRAWN"),
                          options("DRAWN", steps=17)).count == 17


def test_drawn_steps_are_taken():
    p = read("DRAWN")
    assert len(p.chords) == 12
    got = layout.compute(p, options("DRAWN"))
    assert got.drawn and got.count == 14
    assert got.going == pytest.approx(0.30, abs=1e-3)
    winders = layout.compute(read("DRAWN_WINDERS"),
                             options("DRAWN_WINDERS"))
    assert winders.drawn and winders.count == 16


@pytest.mark.parametrize("name,landings", [
    ("L_SHAPE", 1), ("U_SHAPE", 1), ("S_SHAPE", 2), ("STRAIGHT", 0)])
def test_landings(name, landings):
    got = layout.compute(read(name), options(name))
    assert len(got.landings) == landings


@pytest.mark.parametrize("name", ["L_SHAPE", "U_SHAPE", "S_SHAPE", "PATH_L"])
@pytest.mark.parametrize("steps", [0, 15, 18, 21])
def test_one_going_in_every_flight(name, steps):
    got = layout.compute(read(name), options(name, steps=steps))
    goings = got.goings()
    assert max(goings) - min(goings) < 1e-3


@pytest.mark.parametrize("turns", ["landing", "winders"])
def test_steps_drawn_over_a_plan_read_back_the_same(turns):
    made = layout.compute(read("L_SHAPE"), options("L_SHAPE", turns=turns))
    lines = [made.line(k) for k in range(1, made.count - 1)]
    again = layout.compute(plan.analyse(plans.L_SHAPE + lines),
                           options("L_SHAPE"))
    assert again.drawn and again.count == made.count
    assert again.going == pytest.approx(made.going, abs=0.004)
    assert again.landings == made.landings
    for k in range(made.count):
        for a, b in zip(made.line(k), again.line(k)):
            assert geom.dist(a, b) < 0.01


def test_a_post_needs_no_stringer():
    got = layout.compute(read("HELIX_ONE"), options("HELIX_ONE"))
    names = [p.name for p in build.shells(got, 0.0, BUILDS["plates"])]
    assert "column" in names
    assert sum(n.startswith("plate") for n in names) == 1


def test_flip_starts_at_the_other_end():
    a = layout.compute(read("L_SHAPE"), options("L_SHAPE"))
    b = layout.compute(read("L_SHAPE"), options("L_SHAPE", flip=True))
    assert geom.dist(a.walk.pts[0], b.walk.pts[-1]) < 0.01


def test_balanced_winders_leave_room_at_the_inner_side():
    got = layout.compute(read("U_SHAPE"),
                         options("U_SHAPE", turns="winders", height=3.0))
    assert not got.landings
    narrow, _wide = got.inner_goings()
    assert narrow >= 0.065


def test_a_contour_left_open_is_said_so():
    gap = plans.line((0, 0), (1, 0), (1, 4), (0, 4), (0, 0.06))
    with pytest.raises(plan.PlanError, match="not_closed"):
        plan.analyse(gap)


def test_nothing_drawn():
    with pytest.raises(plan.PlanError):
        plan.analyse([])


def turned(name, degrees, dx, dy):
    a = math.radians(degrees)

    def move(p):
        return (p[0] * math.cos(a) - p[1] * math.sin(a) + dx,
                p[0] * math.sin(a) + p[1] * math.cos(a) + dy)
    return [(move(p), move(q)) for p, q in getattr(plans, name)]


@pytest.mark.parametrize("name", SHAPES)
@pytest.mark.parametrize("degrees,dx,dy,z0", [
    (37.0, 12.3, -8.7, 3.15), (163.0, -64.2, 41.9, -2.8),
    (271.5, 148.0, 93.0, 6.4)])
def test_closed_wherever_it_is_drawn(name, degrees, dx, dy, z0):
    read_there = plan.analyse(turned(name, degrees, dx, dy))
    assert read_there.kind == read(name).kind
    for turns in ("landing", "winders"):
        got = layout.compute(read_there, options(name, turns=turns))
        straight = layout.compute(read(name), options(name, turns=turns))
        assert got.count == straight.count
        for what in BUILDS.values():
            for part in build.shells(got, z0, what):
                ok, _volume = solid_report(build.mesh_of(part))
                assert ok, f"{part.name} is not closed ({turns}, {what})"


@pytest.mark.parametrize("name", SHAPES)
@pytest.mark.parametrize("height", [0.54, 1.05, 3.9, 6.2])
def test_closed_at_any_height(name, height):
    for turns in ("landing", "winders"):
        try:
            got = layout.compute(read(name),
                                 options(name, turns=turns, height=height))
        except plan.PlanError:
            continue
        for what in BUILDS.values():
            for part in build.shells(got, 0.0, what):
                ok, _volume = solid_report(build.mesh_of(part))
                assert ok, f"{part.name} is not closed ({turns}, {what})"


@pytest.mark.parametrize("name", ["STRAIGHT", "L_SHAPE", "U_SHAPE", "PATH_L",
                                  "HELIX_TWO"])
@pytest.mark.parametrize("steps", [2, 3, 5, 9, 28, 45])
def test_closed_with_any_number_of_typed_steps(name, steps):
    for turns in ("landing", "winders"):
        got = layout.compute(read(name),
                             options(name, turns=turns, steps=steps))
        for what in BUILDS.values():
            for part in build.shells(got, 0.0, what):
                ok, _volume = solid_report(build.mesh_of(part))
                assert ok, f"{part.name} is not closed ({turns}, {what})"
