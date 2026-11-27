# SPDX-License-Identifier: GPL-3.0-or-later
"""Drives the extension in a real IngeTrazo window that is never shown on
screen, with throwaway settings: an end-to-end check of the tool (plan
taken, height typed, risers typed, side clicked, undo) and the pictures.

    python tools/shots.py <IngeTrazo source> <folder> [light|dark]
"""
import math
import os
import sys
import tempfile
from pathlib import Path

home = tempfile.mkdtemp(prefix="stairs-shot-")
os.environ["APPDATA"] = os.environ["XDG_DATA_HOME"] = home
sys.path.insert(0, sys.argv[1])
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
out = Path(sys.argv[2]).resolve()
out.mkdir(parents=True, exist_ok=True)
theme = sys.argv[3] if len(sys.argv) > 3 else "light"

from PySide6.QtCore import QCoreApplication, QEvent, QPointF, QSettings, Qt, QTimer  # noqa: E402
from PySide6.QtGui import QKeyEvent, QSurfaceFormat, QVector3D as V  # noqa: E402
from PySide6.QtWidgets import QApplication, QDockWidget  # noqa: E402

QSettings.setDefaultFormat(QSettings.IniFormat)
QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, home)
fmt = QSurfaceFormat()
fmt.setVersion(3, 3)
fmt.setProfile(QSurfaceFormat.CoreProfile)
fmt.setDepthBufferSize(24)
fmt.setStencilBufferSize(8)
fmt.setSamples(8)
QSurfaceFormat.setDefaultFormat(fmt)
app = QApplication([])
QCoreApplication.setOrganizationName("stairs-shot")
QCoreApplication.setApplicationName("stairs-shot")

from core import extensions, i18n  # noqa: E402
from views.theme import apply_theme  # noqa: E402
from core.paths import app_root  # noqa: E402

for name in ("set_language", "load_language", "install"):
    if hasattr(i18n, name):
        getattr(i18n, name)("ca")
        break

from core.group import Group  # noqa: E402
from core.mesh import Mesh  # noqa: E402
from core.snap import SnapResult  # noqa: E402
from core.solids import solid_report  # noqa: E402
from tools.base import ToolContext  # noqa: E402
from views.extension_api import ExtensionApp  # noqa: E402
from views.main_window import MainWindow  # noqa: E402

import plans  # noqa: E402
import cte_stairs  # noqa: E402
from cte_stairs import panel as st_panel, texts  # noqa: E402

extensions.plugin_dirs = lambda: [app_root() / "plugins"]
apply_theme(app, theme)
win = MainWindow()
win.setAttribute(Qt.WA_DontShowOnScreen)
win.resize(1500, 1000)
win.show()


def spin(n=15):
    for _ in range(n):
        app.processEvents()


spin(30)
ext = ExtensionApp(win, "cte_stairs")
cte_stairs.setup(ext)
texts.LANGUAGE = lambda: "ca"
dock = next(d for d in win.findChildren(QDockWidget)
            if d.objectName() == "extension_cte_stairs")
panel = win.findChildren(st_panel.StairPanel)[0]
tool = panel.tool
vp = win.viewport
scene = vp.scene
ext.show_panel(dock)
win.resizeDocks([dock], [290], Qt.Horizontal)


def plan_group(segments, dx=0.0, dy=0.0, name="Planta"):
    mesh = Mesh()
    for a, b in segments:
        mesh.add_edge(V(a[0] + dx, a[1] + dy, 0), V(b[0] + dx, b[1] + dy, 0))
    return Group(mesh, name=name)


def reset(*groups):
    panel.stop()
    spin(3)
    scene.selection.clear()
    scene.groups[:] = list(groups)
    vp.history.undo_stack.clear()
    vp.history.redo_stack.clear()
    scene.version += 1
    vp.notify_scene_changed()


def camera(target, yaw, pitch, distance):
    cam = vp.camera
    cam.target = V(*target)
    cam.yaw, cam.pitch = math.radians(yaw), math.radians(pitch)
    cam.distance = distance


def grab(name, whole=True):
    vp.update()
    spin(40)
    image = (win if whole else vp).grab()
    image.save(str(out / name))
    print("saved", name)


def stairs_in():
    return [g for g in scene.groups if "cte_stairs" in (g.ext or {})]


def check(group):
    parts = group.children or [group]
    for part in parts:
        ok, _volume = solid_report(part.mesh)
        assert ok, f"{group.name} / {part.name} is not a closed solid"
    return len(parts)


def press(key, text=""):
    for kind in (QEvent.KeyPress, QEvent.KeyRelease):
        QCoreApplication.sendEvent(vp, QKeyEvent(kind, key, Qt.NoModifier, text))


def type_value(text):
    """As the user types in the viewport, through its own value box."""
    for ch in text:
        key = Qt.Key_Period if ch == "." else Qt.Key_Comma if ch == "," \
            else getattr(Qt, f"Key_{ch.upper()}")
        press(key, ch)
    press(Qt.Key_Return, "\r")
    spin(3)


def click(point, screen=(-50, -50)):
    tool.on_click(ToolContext(vp, point, QPointF(*screen), Qt.NoModifier,
                              SnapResult(point, "none")))
    spin(3)


def run():
    # ---- 1. the tool, end to end, as a user ---------------------------------
    plan = plan_group(plans.L_SHAPE)
    reset(plan)
    before = [(e.a, e.b) for e in plan.mesh.edges]
    camera((1.5, 1.6, 0.9), -62, 34, 9.0)
    s = panel.settings
    s.kind, s.turns, s.height, s.risers, s.sides = "slab", "landing", 2.8, False, "both"
    panel.refresh()
    scene.selection.add(plan)
    panel.start()
    assert vp.active_tool is tool and tool.state == "height", tool.state
    grab("01-plan-taken.png")
    # hovering a point above shows the stair before it exists
    tool.hover_height, tool.hover_point, tool._cache = 2.8, V(0.5, 0.0, 2.8), None
    assert tool.preview_faces()
    grab("02-preview.png")
    type_value("3")                          # a height, in metres
    assert tool.state == "adjust", tool.state
    assert len(stairs_in()) == 1 and abs(s.height - 3.0) < 1e-6
    check(stairs_in()[0])
    type_value("2,8")                        # another height
    assert abs(s.height - 2.8) < 1e-6 and s.steps == 0, (s.height, s.steps)
    type_value("16")                         # sixteen risers
    assert s.steps == 16 and len(stairs_in()) == 1, (s.steps, s.height)
    assert len(vp.history.undo_stack) == 1, "one undo step"
    check(stairs_in()[0])
    from cte_stairs import dbsua
    assert panel.code_card.isVisibleTo(panel)
    assert all(panel.verdicts[use][1].isVisibleTo(panel) for use in dbsua.USES)
    assert not panel.verdicts["ramp"][1].isVisibleTo(panel)
    shown = {use: panel.verdicts[use][1].text() for use in dbsua.USES}
    assert "\u2713" in shown["restricted"], shown
    grab("03-adjust-16-risers.png")
    # choosing the side: a click at the other end starts there
    end = tool._layout()[0].walk.pts[-1]
    click(V(end[0], end[1], 0.0))
    assert s.flip, "clicking the far end starts the stair there"
    assert len(stairs_in()) == 1 and len(vp.history.undo_stack) == 1
    # the panel keeps changing the same stair
    panel.kind.buttons["plates"].click()
    panel.risers.setChecked(True)
    spin(5)
    assert len(stairs_in()) == 1 and len(vp.history.undo_stack) == 1
    assert check(stairs_in()[0]) > 20
    assert [(e.a, e.b) for e in plan.mesh.edges] == before \
        and plan in scene.groups, "the plan is untouched"
    grab("04-adjust-plates.png")
    vp.history.undo()
    assert not stairs_in() and plan in scene.groups

    # the top point clicked instead of typed
    click(V(3.2, 2.7, 3.1))                  # undone: the height is asked again
    assert len(stairs_in()) == 1 and abs(s.height - 3.1) < 1e-5, s.height
    print("end to end: OK")

    # an open line: a click beside it puts the stair on that side
    line = plan_group(plans.PATH_L)
    reset(line)
    scene.selection.add(line)
    panel.start()
    assert tool.make(vp, 2.8)
    click(V(0.5, 1.0, 0.0))                  # right of the first stretch
    assert s.side == "left", s.side          # the line is its left edge
    click(V(-0.5, 1.0, 0.0))
    assert s.side == "right", s.side
    click(V(0.0, 1.0, 0.0))
    assert s.side == "centre", s.side
    assert len(stairs_in()) == 1 and len(vp.history.undo_stack) == 1
    print("sides of an open line: OK")

    # ---- 2. the kinds of stair, side by side --------------------------------
    def make(segments, dx, dy, **values):
        group = plan_group(segments, dx, dy)
        scene.groups.append(group)
        scene.selection.clear()
        scene.selection.add(group)
        panel.stop()
        for key, value in dict(kind="solid", turns="landing", risers=False,
                               sides="both", width=1.0, side="centre",
                               helix_turn=330.0).items():
            setattr(panel.settings, key, value)
        panel.start()
        assert tool.state == "height", tool.state
        for key, value in values.items():
            setattr(panel.settings, key, value)
        assert tool.make(vp, values.get("height", 2.8))
        check(stairs_in()[-1])

    reset()
    make(plans.STRAIGHT, 0.0, 0.0, kind="solid")
    make(plans.L_SHAPE, 2.6, 0.0, kind="slab")
    make(plans.U_SHAPE, 7.4, 0.0, kind="plates", risers=False)
    make(plans.U_SHAPE, 11.4, 0.0, kind="slab", turns="winders")
    make(plans.L_SHAPE, 0.0, -6.2, kind="plates", risers=True, turns="winders")
    make(plans.HELIX_TWO, 6.0, -4.4, kind="plates")
    make(plans.HELIX_ONE, 9.4, -4.4, kind="slab")
    make(plans.CURVED, 13.6, -6.2, kind="solid")
    panel.stop()
    scene.selection.clear()
    camera((7.8, -1.2, 0.9), -97, 40, 23.0)
    grab("05-gallery.png", whole=False)
    vp.camera.perspective = False
    camera((7.4, -1.2, 0.0), -90, 89.9, 24.0)
    grab("06-gallery-top.png", whole=False)
    vp.camera.perspective = True

    # ---- 3. one of each construction, close up ------------------------------
    for name, values in (("07-solid", dict(kind="solid")),
                         ("08-slab", dict(kind="slab")),
                         ("09-plates", dict(kind="plates", risers=False)),
                         ("10-plates-risers", dict(kind="plates", risers=True))):
        reset()
        make(plans.L_SHAPE, 0, 0, **values)
        panel.stop()
        scene.selection.clear()
        camera((1.5, 1.6, 1.0), -38, 24, 7.6)
        grab(name + ".png", whole=False)
    reset()
    make(plans.L_SHAPE, 0, 0, kind="slab")
    panel.stop()
    scene.selection.clear()
    camera((1.5, 1.8, 1.2), 128, -14, 7.6)
    grab("11-slab-underside.png", whole=False)
    reset()
    make(plans.U_SHAPE, 0, 0, kind="solid", turns="winders")
    panel.stop()
    scene.selection.clear()
    vp.camera.perspective = False
    camera((1.0, 1.6, 0.6), -90, 89.9, 6.6)
    grab("12-winders-top.png", whole=False)
    vp.camera.perspective = True

    # ---- 4. drawn steps, an open line and a helix, with the panel -----------
    from cte_stairs import layout as lm, plan as pm
    made = lm.compute(pm.analyse(plans.L_SHAPE),
                      lm.Options(height=2.8, turns="winders"))
    drawn = plans.L_SHAPE + [made.line(k) for k in range(1, made.count - 1)]
    for name, segments in (("13-drawn-steps", drawn),
                           ("14-open-line", plans.PATH_L),
                           ("15-helix", plans.HELIX_ONE)):
        group = plan_group(segments)
        reset(group)
        panel.settings.kind = "plates" if name == "15-helix" else "slab"
        panel.settings.helix_turn = 360.0
        panel.settings.height = 2.8
        panel.settings.side = "centre"
        scene.selection.add(group)
        panel.start()
        if name == "15-helix":
            camera((0, 0, 1.3), -62, 28, 8.0)
        else:
            camera((1.4, 1.5, 0.8), -62, 36, 8.4)
        assert tool.make(vp, 2.8)
        check(stairs_in()[-1])
        if name == "15-helix":
            for use in ("restricted", "general", "public"):
                label = panel.verdicts[use][1]
                assert "\u2717" in label.text(), label.text()
                assert "<li>" in label.toolTip()
        grab(name + ".png")
    ramps()
    print("all pictures: OK")


def ramps():
    s = panel.settings
    long = plans.loop((0, 0), (1.5, 0), (1.5, 6.0), (7.5, 6.0), (7.5, 7.5),
                      (0, 7.5))
    plan = plan_group(long)
    reset(plan)
    s.kind, s.ramp_use, s.ramp_turns = "slab", "access", "landing"
    stair_height = s.height
    panel.mode.buttons["ramp"].click()
    assert s.mode == "ramp" and abs(s.height - 0.6) < 1e-6, s.height
    scene.selection.add(plan)
    panel.start()
    camera((3.6, 3.8, 0.2), -62, 40, 15.0)
    tool.hover_height, tool.hover_point, tool._cache = 0.7, V(7.5, 6.7, 0.7), None
    assert tool.preview_faces()
    grab("16-ramp-preview.png")
    type_value("0,9")
    assert tool.state == "adjust" and abs(s.height - 0.9) < 1e-6
    check(stairs_in()[0])
    filled = tool.measure()
    type_value("8")                          # the slope
    assert abs(s.slope - 8) < 1e-9, (s.slope, s.height)
    got = tool.measure()
    assert abs(got.slope - 0.08) < 1e-6 and got.spare > 0.1, got.slope
    assert len(stairs_in()) == 1 and len(vp.history.undo_stack) == 1
    check(stairs_in()[0])
    assert "\u2713" in panel.verdicts["ramp"][1].text()
    grab("17-ramp-slope-asked.png")
    assert filled.slope < got.slope
    panel.kind.buttons["plates"].click()
    spin(5)
    assert len(stairs_in()) == 1 and len(vp.history.undo_stack) == 1
    assert check(stairs_in()[0]) == 3
    panel.stop()
    scene.selection.clear()
    camera((3.2, 3.6, 0.2), -40, 22, 12.5)
    grab("18-ramp-plates.png", whole=False)

    def make(segments, dx, dy, height, **values):
        group = plan_group(segments, dx, dy)
        scene.groups.append(group)
        scene.selection.clear()
        scene.selection.add(group)
        panel.stop()
        for key, value in dict(kind="solid", ramp_turns="landing",
                               ramp_use="walk", ramp_width=1.2, side="centre",
                               helix_turn=330.0).items():
            setattr(s, key, value)
        panel.start()
        for key, value in values.items():
            setattr(s, key, value)
        assert tool.make(vp, height)
        check(stairs_in()[-1])

    reset()
    make(plans.STRAIGHT, 0.0, 0.0, 0.5, kind="solid")
    make(plans.L_SHAPE, 2.6, 0.0, 0.6, kind="slab")
    make(plans.U_SHAPE, 7.4, 0.0, 0.8, kind="plates")
    make(plans.CURVED, 11.4, -6.2, 0.7, kind="solid")
    make(plans.PATH_L, 0.0, -6.2, 0.6, kind="plates", ramp_turns="slope")
    make(plans.HELIX_TWO, 6.0, -4.4, 2.4, kind="slab", ramp_use="car")
    panel.stop()
    scene.selection.clear()
    camera((6.6, -1.4, 0.4), -97, 36, 20.0)
    grab("19-ramp-gallery.png", whole=False)
    panel.mode.buttons["stair"].click()
    assert abs(s.height - stair_height) < 1e-6 or s.height > 1.0


def main():
    code = 0
    try:
        run()
    except Exception:
        import traceback
        traceback.print_exc()
        code = 1
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)


QTimer.singleShot(2500, main)
app.exec()
