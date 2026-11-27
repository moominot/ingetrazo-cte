"""A drawing with one plan of each kind, to try the extension on.

    python tools/demo_file.py <IngeTrazo source> <file.igz>
"""
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path[:0] = [sys.argv[1], str(root), str(root / "tests")]

from PySide6.QtGui import QVector3D as V  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication([])

from core.group import Group  # noqa: E402
from core.mesh import Mesh  # noqa: E402
from core.scene import Scene  # noqa: E402
from formats.igz import load_into, save_scene  # noqa: E402

import plans  # noqa: E402
from cte_stairs import layout, plan  # noqa: E402

made = layout.compute(plan.analyse(plans.L_SHAPE),
                      layout.Options(height=2.8, turns="winders"))
drawn = plans.L_SHAPE + [made.line(k) for k in range(1, made.count - 1)]

PLANS = [
    ("Planta recta", plans.STRAIGHT, 0.0, 0.0),
    ("Planta en L", plans.L_SHAPE, 2.5, 0.0),
    ("Planta en U", plans.U_SHAPE, 7.2, 0.0),
    ("Planta en L amb graons dibuixats", drawn, 10.8, 0.0),
    ("Planta corbada", plans.CURVED, 14.0, -6.0),
    ("Línia de traç en L", plans.PATH_L, 0.0, -6.0),
    ("Helicoidal amb ull", plans.HELIX_TWO, 6.0, -4.5),
    ("Helicoidal amb pilar", plans.HELIX_ONE, 9.5, -4.5),
    ("Rampa llarga en L", plans.loop((0, 0), (1.5, 0), (1.5, 6.0), (7.5, 6.0),
                                     (7.5, 7.5), (0, 7.5)), 0.0, -16.0),
]

scene = Scene()
scene.groups[:] = []
for name, segments, dx, dy in PLANS:
    mesh = Mesh()
    for a, b in segments:
        mesh.add_edge(V(a[0] + dx, a[1] + dy, 0), V(b[0] + dx, b[1] + dy, 0))
    scene.groups.append(Group(mesh, name=name))

target = Path(sys.argv[2]).resolve()
save_scene(scene, target)

# read it back: every plan must still be understood
again = Scene()
load_into(again, target)
for group in again.groups:
    segments, _z, _flat = plan.group_segments(group)
    print(group.name, "->", plan.analyse(segments).kind)
