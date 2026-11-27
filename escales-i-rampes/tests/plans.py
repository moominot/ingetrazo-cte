"""Plan drawings the tests and the pictures use, as lists of segments."""
import math


def loop(*pts):
    return list(zip(pts, pts[1:] + pts[:1]))


def line(*pts):
    return list(zip(pts, pts[1:]))


def arc(cx, cy, r, a0, a1, n):
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / n)))
            for i in range(n + 1)]


STRAIGHT = loop((0, 0), (1.0, 0), (1.0, 4.48), (0, 4.48))

# up the y axis, then to the right
L_SHAPE = loop((0, 0), (1, 0), (1, 2.2), (3.2, 2.2), (3.2, 3.2), (0, 3.2))

# up, turn right, back down, a well 12 cm wide
U_SHAPE = loop((0, 0), (1, 0), (1, 2.2), (1.12, 2.2), (1.12, 0), (2.12, 0),
               (2.12, 3.2), (0, 3.2))

# two turns of opposite hands
S_SHAPE = loop((0, 0), (1, 0), (1, 1.8), (3.0, 1.8), (3.0, 4.6), (2.0, 4.6),
               (2.0, 2.8), (0, 2.8))

# a quarter ring, drawn as an outline
CURVED = loop(*(arc(0, 0, 3.4, 0, 120, 24) + arc(0, 0, 2.3, 120, 0, 24)))

# a stair whose steps are drawn, with the walking arrow across them
DRAWN = (loop((0, 0), (1, 0), (1, 3.9), (0, 3.9))
         + [((0, 0.3 * k), (1, 0.3 * k)) for k in range(1, 13)]
         + line((0.5, 0.15), (0.5, 3.75))
         + line((0.4, 3.6), (0.5, 3.75), (0.6, 3.6)))

# compensated steps drawn by hand: not square to the walls
DRAWN_WINDERS = (L_SHAPE + [
    ((0, 0.3), (1, 0.3)), ((0, 0.6), (1, 0.6)), ((0, 0.9), (1, 0.9)),
    ((0, 1.25), (1, 1.2)), ((0, 1.65), (1, 1.5)), ((0, 2.15), (1, 1.8)),
    ((0, 3.0), (1, 2.1)), ((0.55, 3.2), (1.15, 2.2)),
    ((1.35, 3.2), (1.45, 2.2)), ((1.75, 3.2), (1.75, 2.2)),
    ((2.05, 3.2), (2.05, 2.2)), ((2.35, 3.2), (2.35, 2.2)),
    ((2.65, 3.2), (2.65, 2.2)), ((2.95, 3.2), (2.95, 2.2))])

PATH_L = line((0, 0), (0, 2.6), (2.8, 2.6))

PATH_ARC = line(*arc(0, 0, 2.2, 180, 30, 30))

HELIX_TWO = (loop(*arc(0, 0, 1.3, 0, 360, 48)[:-1])
             + loop(*arc(0, 0, 0.2, 0, 360, 24)[:-1])
             + [((0.2, 0), (1.3, 0))])

HELIX_ONE = loop(*arc(0, 0, 1.2, 0, 360, 48)[:-1])
