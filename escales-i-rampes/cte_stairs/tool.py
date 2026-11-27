# SPDX-License-Identifier: GPL-3.0-or-later
"""Raising the stair: take the plan, say how high, then adjust.

Three moments:

* **pick** — click the group that holds the plan;
* **height** — click the point the stair arrives at, or type the height
  (Enter alone: the panel's);
* **adjust** — the stair is made. Until another tool is taken, a whole
  number is the number of risers, a length is a new height, a click picks
  the side it starts from (an open line: the side the stair goes) and the
  panel changes it. Each change replaces the stair in the same undo step.

The plan drawing is never touched.
"""
from __future__ import annotations

import re

from PySide6.QtCore import Qt
from PySide6.QtGui import QVector3D

from core.history import InsertGroupCommand
from tools.base import Tool, ToolContext

from . import build, geom, layout, plan as planmod, ramp
from .ramp_build import ramp_shells
from .texts import tr

#: Below this above the plan, a point does not say a height.
_MIN_RISE = 0.30
#: A whole number up to this, typed on a made stair, counts risers.
_MAX_TYPED_STEPS = 80
#: The same on a made ramp: the slope, per cent.
_MAX_TYPED_SLOPE = 40


class StairTool(Tool):
    name = "Stairs"
    description = "Raise a stair from its plan drawing."
    vcb_label = "Height"
    axis_source = True
    axis_source_empty_only = True
    wireframe_color = (0.91, 0.45, 0.16, 1.0)
    wireframe_depth_tested = True

    def __init__(self, settings, on_state=None, on_layout=None) -> None:
        self.settings = settings
        self.on_state = on_state
        #: Told ``(layout or None, error text or "")`` after every change.
        self.on_layout = on_layout
        self._forget()

    def _forget(self) -> None:
        self.state = "pick"
        self.segments = None
        self.plan_uid = None
        self.z0 = 0.0
        self.command = None
        self.hover_height = None
        self.hover_point = None
        self.start_point = None
        self.work_plane = None
        self.chain_first_point = None
        self.chain_vertices: list = []
        self._cache = None
        self.settings.plan = None
        self.settings.reset_plan()

    # ---- Lifecycle -----------------------------------------------------------------
    @property
    def ramp(self) -> bool:
        return self.settings.mode == "ramp"

    def on_activate(self, viewport) -> None:
        self.name = tr("CTE Stairs and ramps")
        self._forget()
        if self.on_state is not None:
            self.on_state(True)

    def on_deactivate(self, viewport) -> None:
        self._forget()
        if self.on_state is not None:
            self.on_state(False)

    # ---- The plan --------------------------------------------------------------------
    def load(self, viewport, group) -> bool:
        """Take ``group`` as the plan. ``False``, with the reason shown, when
        its lines do not make a stair."""
        try:
            segments, z0, flat = planmod.group_segments(group)
            read = planmod.analyse(segments)
        except planmod.PlanError as error:
            self._say(viewport, tr(str(error)), 7000)
            self._report(None, tr(str(error)))
            return False
        self._forget()
        self.segments, self.z0, self.plan_uid = segments, z0, group.uid
        self.settings.plan = read
        self.state = "height"
        self._aim(viewport)
        self.settings.changed()
        if not flat:
            self._say(viewport, tr("The plan is not flat: its lowest height "
                                   "is the floor."), 6000)
        self._hint(viewport)
        viewport.update()
        return True

    def _read_again(self) -> None:
        """Another pair of ends of the same contour."""
        self.settings.plan = planmod.analyse(self.segments,
                                             self.settings.end_choice)

    def _foot(self) -> QVector3D:
        """The middle of the first riser, on the floor: where the height is
        measured from."""
        try:
            lay = self.measure()
        except planmod.PlanError:
            return QVector3D(0, 0, self.z0)
        p = lay.walk.point(0.0)
        return QVector3D(p[0], p[1], self.z0)

    def _aim(self, viewport) -> None:
        """While the height is asked for: inferences from the foot of the
        stair, and the free cursor on an upright plane through it."""
        if self.state != "height":
            self.start_point = None
            self.work_plane = None
            return
        foot = self._foot()
        self.start_point = foot
        ahead = viewport.camera.forward()
        flat = QVector3D(ahead.x(), ahead.y(), 0.0)
        if flat.length() < 0.15:
            flat = QVector3D(0.0, 1.0, 0.0)
        self.work_plane = (foot, flat.normalized())

    # ---- Computing --------------------------------------------------------------------
    def measure(self, height=None):
        """The stair's or the ramp's layout, as the settings stand."""
        s = self.settings
        if self.ramp:
            return ramp.compute(s.plan, s.ramp_options(height))
        return layout.compute(s.plan, s.options(height))

    def _layout(self, height=None):
        """``(layout, parts)``."""
        lay = self.measure(height)
        make = ramp_shells if self.ramp else build.shells
        return lay, make(lay, self.z0, self.settings.building())

    def invalidate(self, viewport=None) -> None:
        self._cache = None
        if self.state == "height" and viewport is not None:
            self._aim(viewport)
        self._refresh_report()

    def _refresh_report(self) -> None:
        if self.settings.plan is None:
            self._report(None, "")
            return
        try:
            lay = self.measure()
        except planmod.PlanError as error:
            self._report(None, tr(str(error)))
            return
        self._report(lay, "")

    def _report(self, lay, error) -> None:
        if self.on_layout is not None:
            self.on_layout(lay, error)

    def _group(self):
        s = self.settings
        _lay, parts = self._layout()
        names = {"solid": tr("Solid stair"), "slab": tr("Concrete stair"),
                 "plates": tr("Steel stair")}
        if self.ramp:
            names = {"solid": tr("Solid ramp"), "slab": tr("Concrete ramp"),
                     "plates": tr("Steel ramp")}
        info = {"settings": s.info(), "floor": round(self.z0, 6),
                "plan": [[[round(c, 5) for c in a], [round(c, 5) for c in b]]
                         for a, b in self.segments]}
        return build.group_of(parts, names[s.kind], _part_name, info)

    # ---- Making and remaking -------------------------------------------------------------
    def _alive(self, viewport) -> bool:
        """Whether the stair made is still the last thing done."""
        stack = viewport.history.undo_stack
        return bool(stack) and stack[-1] is self.command

    def _check(self, viewport) -> None:
        """A made stair that was undone, or left behind by another edit,
        is no longer adjusted: the height is asked for again."""
        if self.state == "adjust" and not self._alive(viewport):
            self.state = "height"
            self.command = None
            self.hover_height = None
            self._cache = None
            self._aim(viewport)
            self._hint(viewport)

    def make(self, viewport, height: float) -> bool:
        self.settings.height = float(height)
        try:
            group = self._group()
        except planmod.PlanError as error:
            self._say(viewport, tr(str(error)), 6000)
            return False
        command = InsertGroupCommand(group)
        if viewport.history.execute(command) is False:
            return False
        self.command = command
        self.state = "adjust"
        self.hover_height = None
        self._cache = None
        self._aim(viewport)
        # not «settings.changed»: that would make the stair a second time
        self._refresh_report()
        if self.on_state is not None:
            self.on_state(True)
        self._changed_model(viewport)
        self._hint(viewport)
        return True

    def remake(self, viewport) -> bool:
        """The made stair again, with the settings as they are now."""
        if self.state != "adjust":
            return False
        self._check(viewport)
        if self.state != "adjust":
            return False
        try:
            group = self._group()
        except planmod.PlanError as error:
            self._say(viewport, tr(str(error)), 6000)
            return False
        viewport.history.undo()
        command = InsertGroupCommand(group)
        viewport.history.execute(command)
        self.command = command
        self._changed_model(viewport)
        return True

    def _changed_model(self, viewport) -> None:
        notify = getattr(viewport, "notify_scene_changed", None)
        if callable(notify):
            notify()
        viewport.update()

    def done(self, viewport) -> None:
        """Ready for the next plan."""
        self._forget()
        self.settings.changed()
        self._hint(viewport)
        viewport.update()

    # ---- Events -------------------------------------------------------------------------------
    def _height_at(self, point):
        rise = point.z() - self.z0
        return rise if rise > _MIN_RISE else None

    def on_hover(self, ctx: ToolContext) -> None:
        self._check(ctx.viewport)
        if self.state != "height":
            return
        self.hover_point = QVector3D(ctx.world)
        rise = self._height_at(ctx.world)
        if rise != self.hover_height:
            self.hover_height = rise
            self._cache = None
        self._aim(ctx.viewport)
        ctx.viewport.update()

    def on_click(self, ctx: ToolContext) -> None:
        vp = ctx.viewport
        self._check(vp)
        if self.state == "height":
            rise = self._height_at(ctx.world)
            if rise is None:
                self._say(vp, tr("Click a point above the plan, or type the "
                                 "height (Enter: the panel's)."), 4000)
                return
            self.make(vp, rise)
            return
        picked = vp.pick_group(ctx.screen.x(), ctx.screen.y())
        if self.state == "pick":
            if picked is None:
                self._say(vp, tr("Click the group that holds the plan."), 3500)
            elif build.KEY in (picked.ext or {}):
                self._say(vp, tr("That is a stair already: click its plan."),
                          3500)
            else:
                self.load(vp, picked)
            return
        # adjust: another plan starts another stair; else a side
        if (picked is not None and picked.uid != self.plan_uid
                and build.KEY not in (picked.ext or {})):
            if self.load(vp, picked):
                return
        self.pick_side(vp, (ctx.world.x(), ctx.world.y()))

    def pick_side(self, viewport, point) -> None:
        """A click on a made stair: the end it starts from, or, for an open
        line, the side of the line it stands on."""
        s = self.settings
        if s.plan is None or s.plan.kind == "circle":
            return
        try:
            lay = self.measure()
        except planmod.PlanError:
            return
        if s.plan.kind == "outline":
            start = geom.lerp(*lay.line(0), 0.5)
            end = geom.lerp(*lay.line(lay.count - 1), 0.5)
            if self.ramp and lay.spare > 0.05:
                # a short ramp ends before the plan does: the plan's far end
                far = self.measure_full_end()
                end = far if far is not None else end
            if geom.dist(point, end) + 0.05 >= geom.dist(point, start):
                return
            s.flip = not s.flip
        else:
            path = list(s.plan.path)
            if s.flip:
                path.reverse()
            chain = geom.Chain(path)
            distance, at = chain.nearest(point)
            width = s.ramp_width if self.ramp else s.width
            if distance > 1.6 * width:
                return
            off = geom.cross(chain.tangent(at), geom.sub(point,
                                                         chain.point(at)))
            if distance < 0.12:
                side = "centre"
            else:
                # ``side`` says where the LINE is: the stair is across
                side = "right" if off > 0 else "left"
            if side == s.side:
                return
            s.side = side
        s.changed()

    def measure_full_end(self):
        """The middle of the plan's far end, as climbed."""
        read = self.settings.plan
        a, b = (read.left[-1], read.right[-1])
        if self.settings.flip:
            a, b = (read.left[0], read.right[0])
        return geom.lerp(a, b, 0.5)

    def on_cancel(self, viewport) -> None:
        self.done(viewport)

    def reverse(self, viewport) -> None:
        self.settings.flip = not self.settings.flip
        self.settings.changed()
        self._say(viewport, tr("Climbs the other way"), 2000)

    def next_ends(self, viewport) -> None:
        """A contour whose ends were guessed wrong: the next likely pair."""
        if self.settings.plan is None or self.settings.plan.kind != "outline":
            return
        self.settings.end_choice += 1
        self.settings.flip = False
        try:
            self._read_again()
        except planmod.PlanError as error:
            self._say(viewport, tr(str(error)), 5000)
            return
        self.settings.changed()

    def on_key(self, viewport, key: int, modifiers) -> bool:
        self._check(viewport)
        if key in (int(Qt.Key_Return), int(Qt.Key_Enter)):
            if self.state == "height":
                self.make(viewport, self.settings.height)
                return True
            if self.state == "adjust":
                self.done(viewport)
                return True
        return False

    def on_key_release(self, viewport, key: int) -> bool:
        if key == int(Qt.Key_Control) and self.state != "pick" \
                and self.ctrl_tapped(viewport):
            self.reverse(viewport)
        return False

    def on_value(self, viewport, value) -> bool:
        self._check(viewport)
        if self.state == "pick" or isinstance(value, bool) \
                or not isinstance(value, (int, float)):
            return False
        if self.state == "height":
            if value <= 0.05:
                return False
            return self.make(viewport, value)
        typed = str(getattr(viewport, "_value_buffer", "") or "").strip()
        most = _MAX_TYPED_SLOPE if self.ramp else _MAX_TYPED_STEPS
        if re.fullmatch(r"\d+", typed) and 2 <= int(typed) <= most:
            if self.ramp:
                self.set_slope(viewport, int(typed))
            else:
                self.set_steps(viewport, int(typed))
            return True
        if value <= 0.05:
            return False
        self.settings.height = float(value)
        self.settings.changed()
        return True

    def set_steps(self, viewport, count: int) -> None:
        self.settings.steps = count
        self.settings.changed()
        self._say(viewport, tr("{n} risers", n=count), 2000)

    def set_slope(self, viewport, percent: float) -> None:
        self.settings.slope = float(percent)
        self.settings.changed()
        self._say(viewport, tr("Slope {p} %", p=f"{percent:g}"), 2000)

    # ---- What is shown ----------------------------------------------------------------------------
    def _preview(self):
        if self._cache is None:
            self._cache = self._make_preview()
        return self._cache

    def _make_preview(self):
        if self.state != "height" or self.settings.plan is None:
            return [], []
        try:
            lay, parts = self._layout(self.hover_height)
        except planmod.PlanError:
            return [], []
        draw = _ramp_lines if self.ramp else _plan_lines
        lines = draw(lay, self.z0 + 0.004)
        if self.hover_height is None:
            return [], lines
        faces, edges = build.preview_of(parts)
        return faces, lines + edges

    def preview_faces(self):
        return self._preview()[0]

    def rubber_band_lines(self):
        return self._preview()[1]

    def value_label(self):
        if self.state != "height" or self.hover_height is None \
                or self.hover_point is None:
            return None
        from core.units import fmt_len
        try:
            lay = self.measure(self.hover_height)
        except planmod.PlanError:
            return None
        text = "{} · {}".format(fmt_len(self.hover_height), summary(lay))
        return text, self.hover_point

    def status_clause(self) -> str:
        if self.state == "pick":
            return tr("Click the group that holds the plan")
        if self.state == "height":
            return tr("Click the top point or type the height (Enter: the "
                      "panel's) · Ctrl = reverse")
        side = ""
        if self.settings.plan is not None:
            kind = self.settings.plan.kind
            if kind == "outline":
                side = tr(" · click an end = start there")
            elif kind == "path":
                side = tr(" · click beside the line = that side")
        if self.ramp:
            first = tr("Type the slope in % (e.g. 8) or a height (e.g. 0.60) "
                       "· Ctrl = reverse")
        else:
            first = tr("Type the risers (e.g. 16) or a height (e.g. 2.90) · "
                       "Ctrl = reverse")
        return first + side + tr(" · Enter = done")

    def _hint(self, viewport) -> None:
        self.refresh_hint(viewport)

    def _say(self, viewport, text, ms) -> None:
        viewport.flash_status(text, ms)


def summary(lay) -> str:
    """«16 × 17.5 / 29.9 cm»: risers, their height and the going. A ramp:
    «8.0 % · 7.50 m»."""
    if hasattr(lay, "flights"):
        return "{p} % · {m} m".format(p=_num(lay.slope * 100, 1),
                                      m=_num(lay.run, 2))
    return "{n} × {h} / {g} cm".format(
        n=lay.count, h=_cm(lay.riser), g=_cm(lay.going))


def _num(value, places) -> str:
    return f"{value:.{places}f}".replace(".", tr("."))


def _cm(metres) -> str:
    return _num(metres * 100, 1)


def _arrow(lay, seg) -> list:
    tip = lay.walk.pts[-1]
    back = geom.mul(lay.walk.tangent(lay.walk.length), -0.18)
    wing = geom.mul(geom.left_of(back), 0.55)
    return [seg(tip, geom.add(tip, geom.add(back, wing))),
            seg(tip, geom.add(tip, geom.sub(back, wing)))]


def _ramp_lines(lay, z):
    """The ramp read in the plan: sides, walking line, where each flight
    and landing begins, and the arrow."""
    def seg(a, b):
        return (QVector3D(a[0], a[1], z), QVector3D(b[0], b[1], z))

    out = []
    for chain in (lay.left, lay.right, lay.walk):
        out += [seg(a, b) for a, b in zip(chain.pts, chain.pts[1:])]
    marks = {round(m, 5) for span in lay.flights + lay.landings for m in span}
    for k, line in enumerate(lay.lines):
        if round(line[2], 5) in marks:
            out.append(seg(*lay.line(k)))
    return out + _arrow(lay, seg)


def _plan_lines(lay, z):
    """What was read in the plan, flat on it: the sides, every riser, the
    walking line and an arrow the way it climbs."""
    def seg(a, b):
        return (QVector3D(a[0], a[1], z), QVector3D(b[0], b[1], z))

    out = []
    for chain in (lay.left, lay.right, lay.walk):
        out += [seg(a, b) for a, b in zip(chain.pts, chain.pts[1:])]
    out += [seg(*lay.line(k)) for k in range(lay.count)]
    return out + _arrow(lay, seg)


def _part_name(key: str) -> str:
    if key == "deck":
        return tr("Deck")
    kind, _, number = key.partition(" ")
    if kind == "tread":
        return tr("Tread {n}", n=number)
    if kind == "riser":
        return tr("Riser {n}", n=number)
    return tr({"body": "Body", "column": "Column",
               "plate left": "Left stringer",
               "plate right": "Right stringer"}.get(key, key))
