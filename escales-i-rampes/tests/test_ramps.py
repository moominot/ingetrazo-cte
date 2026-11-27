"""Ramps over the same plans: closed solids and sensible slopes."""
import pytest

from test_engine import BUILDS, SHAPES, read, turned

from core.solids import solid_report
from cte_stairs import build, geom, plan, ramp
from cte_stairs.ramp_build import ramp_shells

KINDS = {k: v for k, v in BUILDS.items() if k != "plates_risers"}


def options(name, **kw):
    kw.setdefault("height", 0.8)
    if name.startswith("HELIX"):
        kw.setdefault("helix_turn", 330)
    return ramp.Options(**kw)


def closed(got, z0):
    for what, how in KINDS.items():
        for part in ramp_shells(got, z0, how):
            ok, volume = solid_report(build.mesh_of(part))
            assert ok, f"{part.name} is not closed ({what})"
            assert volume > 0


@pytest.mark.parametrize("name", SHAPES)
@pytest.mark.parametrize("turns", ["landing", "slope"])
@pytest.mark.parametrize("flip", [False, True])
@pytest.mark.parametrize("slope", [0.0, 14.0, 40.0])
def test_closed(name, turns, flip, slope):
    got = ramp.compute(read(name), options(name, turns=turns, flip=flip,
                                           slope=slope))
    closed(got, 0.0)


@pytest.mark.parametrize("name", SHAPES)
@pytest.mark.parametrize("degrees,dx,dy,z0,height", [
    (37.0, 12.3, -8.7, 3.15, 0.18), (163.0, -64.2, 41.9, -2.8, 2.9)])
def test_closed_wherever_and_however_high(name, degrees, dx, dy, z0, height):
    there = plan.analyse(turned(name, degrees, dx, dy))
    for turns in ("landing", "slope"):
        closed(ramp.compute(there, options(name, turns=turns,
                                           height=height)), z0)


@pytest.mark.parametrize("name", SHAPES)
@pytest.mark.parametrize("turns", ["landing", "slope"])
def test_it_only_climbs(name, turns):
    got = ramp.compute(read(name), options(name, turns=turns))
    assert got.lines[0][3] == 0 and got.lines[-1][3] == pytest.approx(0.8)
    for a, b in zip(got.lines, got.lines[1:]):
        assert b[0] >= a[0] - 1e-6 and b[1] >= a[1] - 1e-6
        assert b[2] > a[2] and b[3] >= a[3] - 1e-9
        flat = any(x - 1e-5 <= a[2] and b[2] <= y + 1e-5
                   for x, y in got.landings)
        slope = (b[3] - a[3]) / (b[2] - a[2])
        assert slope == pytest.approx(0.0 if flat else got.slope, abs=1e-3)


def test_fills_the_plan():
    got = ramp.compute(read("STRAIGHT"), options("STRAIGHT", height=0.3))
    assert got.slope == pytest.approx(0.3 / 4.48)
    assert got.spare == pytest.approx(0, abs=1e-6)


def test_a_slope_asked_for_uses_only_what_it_needs():
    got = ramp.compute(read("STRAIGHT"),
                       options("STRAIGHT", height=0.3, slope=10))
    assert got.slope == pytest.approx(0.10)
    assert got.run == pytest.approx(3.0)
    assert got.spare == pytest.approx(1.48)
    assert geom.dist(got.walk.pts[0], got.walk.pts[-1]) == pytest.approx(3.0)


def test_a_slope_the_plan_has_no_room_for():
    got = ramp.compute(read("STRAIGHT"),
                       options("STRAIGHT", height=0.6, slope=8))
    assert got.slope == pytest.approx(0.6 / 4.48)
    assert got.missing == pytest.approx(7.5 - 4.48)


def test_long_runs_get_landings():
    long = plan.analyse([((0, 0), (22, 0)), ((22, 0), (22, 1.5)),
                         ((22, 1.5), (0, 1.5)), ((0, 1.5), (0, 0))])
    got = ramp.compute(long, ramp.Options(height=1.1, use="access"))
    assert len(got.flights) == 3 and len(got.landings) == 2
    assert got.longest <= 9.0 + 1e-6
    assert all(b - a == pytest.approx(1.5) for a, b in got.landings)
    steeper = ramp.compute(long, ramp.Options(height=1.2, use="access"))
    # three flights would need 6 % at most: shorter ones may have 8 %
    assert steeper.longest <= 6.0 + 1e-6 and 0.06 < steeper.slope <= 0.08
    assert len(steeper.flights) > 3
    asked = ramp.compute(long, ramp.Options(height=1.2, slope=8))
    assert asked.longest <= 6.0 + 1e-6
    assert asked.slope == pytest.approx(0.08)
    gentle = ramp.compute(long, ramp.Options(height=0.7))
    assert len(gentle.flights) == 1                # under 4 %: not a ramp
    one = ramp.compute(long, ramp.Options(height=1.2, split=False))
    assert len(one.flights) == 1
    closed(got, 0.0)


def test_3_and_6_m_are_included():
    for run in (2.9999, 3.0):
        assert ramp.limit("access", run) == 0.10
    for run in (3.01, 5.9999, 6.0):
        assert ramp.limit("access", run) == 0.08
    assert ramp.limit("access", 6.01) == 0.06
    got = ramp.compute(read("STRAIGHT"),
                       options("STRAIGHT", height=0.3, slope=10))
    assert not got.missing and got.longest == pytest.approx(3.0)
    assert got.worst() <= ramp.limit("access", got.longest) + 1e-4


def test_a_centimetre_too_long_grows_the_landing_instead():
    got = ramp.compute(plan.analyse(
        [((0, 0), (1.5, 0)), ((1.5, 0), (1.5, 6.0)), ((1.5, 6.0), (7.5, 6.0)),
         ((7.5, 6.0), (7.5, 7.5)), ((7.5, 7.5), (0, 7.5)),
         ((0, 7.5), (0, 0))]), ramp.Options(height=0.9))
    assert len(got.flights) == 2 and got.longest == pytest.approx(6.0)
    assert got.worst() <= 0.08 + 1e-4
    closed(got, 0.0)


def test_a_curve_is_held_to_its_least_favourable_side():
    got = ramp.compute(read("HELIX_TWO"), options("HELIX_TWO"))
    assert got.worst() > got.slope * 1.3
    assert got.tight_curve()
    straight = ramp.compute(read("STRAIGHT"), options("STRAIGHT"))
    assert straight.worst() == pytest.approx(straight.slope, rel=1e-3)
    assert not straight.tight_curve()


@pytest.mark.parametrize("use,run,most", [
    ("access", 3.0, 0.10), ("access", 6.0, 0.08),
    ("access", 2.9, 0.10), ("access", 5.0, 0.08), ("access", 8.0, 0.06),
    ("walk", 8.0, 0.12), ("car", 20.0, 0.16)])
def test_limits(use, run, most):
    assert ramp.limit(use, run) == most


@pytest.mark.parametrize("name", SHAPES)
@pytest.mark.parametrize("turns", ["landing", "slope"])
def test_no_stringer_goes_missing(name, turns):
    got = ramp.compute(read(name), options(name, turns=turns))
    names = [p.name for p in ramp_shells(got, 0.0, KINDS["plates"])]
    assert "deck" in names
    wanted = 1 if got.column else 2
    assert sum(n.startswith("plate") for n in names) == wanted


def test_turn_landings():
    got = ramp.compute(read("L_SHAPE"), options("L_SHAPE"))
    assert len(got.landings) == 1 and len(got.flights) == 2
    sloped = ramp.compute(read("L_SHAPE"), options("L_SHAPE", turns="slope"))
    assert not sloped.landings
    assert sloped.steepest_side() > sloped.slope
