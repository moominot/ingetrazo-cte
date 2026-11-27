"""The verdict on CTE DB SUA 1, 4.1 and 4.2."""
import pytest

import plans
from test_engine import read

from cte_stairs import dbsua, layout, plan, ramp


def failed(got, use):
    return {key for key, _values in dbsua.check(got, use)}


def straight(length, height, steps, width=1.0):
    p = plan.analyse(plans.loop((0, 0), (width, 0), (width, length),
                                (0, length)))
    return layout.compute(p, layout.Options(height=height, steps=steps))


def helix(inner, outer, turn, height, steps):
    two = (plans.loop(*plans.arc(0, 0, outer, 0, 360, 72)[:-1])
           + plans.loop(*plans.arc(0, 0, inner, 0, 360, 48)[:-1]))
    return layout.compute(plan.analyse(two), layout.Options(
        height=height, steps=steps, helix_turn=turn))


def test_a_comfortable_straight_stair_complies():
    got = straight(4.2, 2.8, 16)                    # 17.5 and 28
    for use in dbsua.USES:
        if use == "public":                         # 2.80 in one flight
            assert failed(got, use) == {"db_flight_height"}
        else:
            assert failed(got, use) == set()


def test_short_going_and_high_riser():
    got = straight(3.0, 2.8, 14)                    # 20 and 23.1
    assert "db_going_min" in failed(got, "general")
    assert "db_riser_max" in failed(got, "general")
    assert failed(got, "restricted") == set()


def test_a_wide_curve_complies():
    # radii 2.00 - 3.20: 31 cm at 50 cm from inside, 39 cm outside
    got = helix(2.0, 3.2, 100, 2.4, 15)
    inner = dbsua._Tread(got, 3)
    assert inner.curved
    assert inner.going(0.5) == pytest.approx(0.312, abs=0.003)
    assert inner.going(inner.width) == pytest.approx(0.399, abs=0.003)
    assert failed(got, "general") == set()


def test_a_curve_too_wide_outside():
    got = helix(2.0, 3.8, 100, 2.4, 15)
    assert "db_curve_wide" in failed(got, "general")


def test_a_spiral_about_a_thin_post():
    got = layout.compute(read("HELIX_ONE"),
                         layout.Options(height=2.8, helix_turn=330))
    general = failed(got, "general")
    assert {"db_curve_inner", "db_width"} <= general
    assert "db_curve_narrow" in failed(got, "restricted")   # under 5 cm


def test_a_spiral_for_restricted_use():
    got = helix(0.15, 1.0, 330, 2.7, 15)
    assert failed(got, "restricted") == set()
    assert "db_curve_inner" not in failed(got, "restricted")


def test_a_flight_of_two_steps():
    got = straight(0.6, 0.35, 2)
    assert "db_few_steps" in failed(got, "general")


@pytest.mark.parametrize("name", ["L_SHAPE", "U_SHAPE", "CURVED", "DRAWN",
                                  "DRAWN_WINDERS", "PATH_L", "HELIX_TWO"])
@pytest.mark.parametrize("turns", ["landing", "winders"])
def test_every_stair_gets_a_verdict(name, turns):
    got = layout.compute(read(name), layout.Options(height=2.8, turns=turns))
    for use in dbsua.USES:
        for key, values in dbsua.check(got, use):
            assert key.startswith("db_")


def ramp_failed(got, use):
    return {key.split()[0] for key, _values in dbsua.check_ramp(got, use)}


def long_ramp(height, use="access", width=1.5, **kw):
    p = plan.analyse(plans.loop((0, 0), (width, 0), (width, 6.0),
                                (7.5, 6.0), (7.5, 6.0 + width),
                                (0, 6.0 + width)))
    return ramp.compute(p, ramp.Options(height=height, use=use, **kw))


def test_a_ramp_that_complies():
    assert dbsua.check_ramp(long_ramp(0.9, slope=8), "access") == []


def test_a_ramp_too_steep_or_too_narrow():
    assert ramp_failed(long_ramp(1.4), "access") == {"Over"}
    assert ramp_failed(long_ramp(1.4, use="walk"), "walk") == set()
    assert "Narrower" in ramp_failed(long_ramp(0.7, width=1.0), "access")
    assert ramp_failed(long_ramp(0.7, width=1.0, use="walk"), "walk") == set()


def test_up_to_4_per_cent_nothing_applies():
    assert dbsua.check_ramp(long_ramp(0.3, width=1.0), "access") == []


def test_a_short_landing_counts_only_in_line():
    p = plan.analyse(plans.loop((0, 0), (22, 0), (22, 1.5), (0, 1.5)))
    got = ramp.compute(p, ramp.Options(height=1.1, landing=1.2))
    assert "Landings" in ramp_failed(got, "access")
    turn = long_ramp(0.9, landing=1.2)             # only the turn's landing
    assert "Landings" not in ramp_failed(turn, "access")


def test_an_accessible_curve_does_not_comply():
    got = ramp.compute(read("CURVED"), ramp.Options(height=0.4))
    assert "Accessible" in ramp_failed(got, "access")
