# SPDX-License-Identifier: GPL-3.0-or-later
"""The «Stairs» tab."""
from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QDoubleSpinBox,
                               QFormLayout, QGridLayout, QHBoxLayout, QLabel, QScrollArea,
                               QSizePolicy, QSpinBox, QToolButton,
                               QVBoxLayout, QWidget)

from . import (dbsua, icons, layout as layoutmod, ramp as rampmod,
               wheel_guard)
from .settings import Settings
from .texts import tr
from .tool import StairTool, _cm, _num
from .ui import Card, CentredButton, flat_style

_WARN = "#d9731f"
_OK = "#2e8b57"


def _length_box(minimum=0.001, maximum=1000.0):
    try:
        from views.length_field import LengthSpinBox
        box = LengthSpinBox(minimum=minimum, maximum=maximum)
    except ImportError:
        box = QDoubleSpinBox()
        box.setDecimals(3)
        box.setRange(minimum, maximum)
        box.setSuffix(" m")
    box.setKeyboardTracking(False)
    return box


def _angle_box(minimum, maximum, step):
    box = QDoubleSpinBox()
    box.setRange(minimum, maximum)
    box.setDecimals(0)
    box.setSingleStep(step)
    box.setSuffix("°")
    box.setKeyboardTracking(False)
    return box


def _button(text, icon_key, tip="", above=False, checkable=False):
    b = QToolButton() if above else CentredButton()
    b.setText(text)
    b.setIcon(icons.icon(icon_key))
    b.setToolTip(tip)
    b.setCheckable(checkable)
    b.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
    if above:                              # side by side: icon over the words
        b.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        b.setIconSize(QSize(22, 22))
        b.setMinimumHeight(46)
        font = b.font()
        font.setPixelSize(10)
        b.setFont(font)
    else:
        b.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        b.setIconSize(QSize(18, 18))
        b.setMinimumHeight(28)
    return b


def _caption(text=""):
    label = QLabel(text)
    label.setWordWrap(True)
    return label


def _form():
    host = QWidget()
    form = QFormLayout(host)
    form.setContentsMargins(0, 0, 0, 0)
    form.setRowWrapPolicy(QFormLayout.WrapLongRows)
    return host, form


def _table(rows) -> str:
    return "<table cellspacing='1'>" + "".join(
        f"<tr><td>{a}&nbsp;&nbsp;</td><td><b>{b}</b></td></tr>"
        for a, b in rows) + "</table>"


def _localised(values: dict) -> dict:
    """Measures with the language's decimal mark."""
    return {k: str(v).replace(".", tr(".")) for k, v in values.items()}


class Choice(QWidget):
    """Two or three side-by-side buttons, one of them on."""

    def __init__(self, options, on_pick, parent=None) -> None:
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)
        self.group = QButtonGroup(self)
        self.buttons: dict = {}
        for value, text, icon_key, tip in options:
            b = _button(text, icon_key, tip, above=True, checkable=True)
            self.group.addButton(b)
            row.addWidget(b, 1)
            self.buttons[value] = b
            b.clicked.connect(lambda _c=False, v=value: on_pick(v))

    def set(self, value) -> None:
        if value in self.buttons:
            self.buttons[value].setChecked(True)


class StairPanel(QScrollArea):
    def __init__(self, app) -> None:
        super().__init__()
        self.app = app
        self.settings = Settings()
        self.settings.load()
        self.settings.on_change = self._settings_changed
        self._loading = False
        self._busy = False
        self._layout_got = (None, "")
        self.tool = StairTool(self.settings, self._tool_state,
                              self._show_layout)
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        page = QWidget()
        page.setStyleSheet(flat_style())
        self.setWidget(page)
        lay = QVBoxLayout(page)
        lay.setContentsMargins(6, 8, 6, 6)
        lay.setSpacing(6)

        self.mode = Choice([
            ("stair", tr("Stair"), "stairs", ""),
            ("ramp", tr("Ramp"), "ramp", "")],
            lambda v: self._set("mode", v))
        lay.addWidget(self.mode)
        self._build_plan(lay)
        self._build_steps(lay)
        self._build_slope(lay)
        self._build_code(lay)
        self._build_construction(lay)

        self.draw = CentredButton()
        self.draw.setText(tr("Raise the stair"))
        self.draw.setIcon(icons.icon("stairs"))
        self.draw.setIconSize(QSize(22, 22))
        self.draw.setMinimumHeight(42)
        self.draw.setCheckable(True)
        self.draw.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.draw.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.draw.clicked.connect(
            lambda on: self.start() if on else self.stop())
        lay.addWidget(self.draw)
        self.message = _caption()
        self.message.setStyleSheet("color: palette(mid);")
        lay.addWidget(self.message)
        lay.addStretch(1)
        wheel_guard.watch(self)
        self.refresh()

    # ---- The cards -----------------------------------------------------------------------
    def _build_plan(self, lay) -> None:
        card = self.plan_card = Card(tr("Plan"), "plan", icon="plan",
                                     kind="column")
        box = card.body_layout
        take = self.take = _button(tr("Take the selected plan"), "take")
        take.clicked.connect(lambda _c=False: self.start(complain=True))
        box.addWidget(take)
        self.plan_label = _caption()
        box.addWidget(self.plan_label)

        self.path_rows, form = _form()
        self.width_box = _length_box(0.3, 20.0)
        self.width_box.valueChanged.connect(lambda v: self._set(
            "ramp_width" if self.settings.mode == "ramp" else "width", v))
        form.addRow(tr("Width"), self.width_box)
        side_label = _caption(tr("The line is"))
        side_label.setToolTip(tr("As seen going up"))
        form.addRow(side_label)
        self.side = Choice([
            ("left", tr("Left"), "side_left", tr("As seen going up")),
            ("centre", tr("Centre"), "side_centre", ""),
            ("right", tr("Right"), "side_right", tr("As seen going up"))],
            lambda v: self._set("side", v))
        form.addRow(self.side)
        box.addWidget(self.path_rows)

        self.helix_rows, form = _form()
        self.turn_box = _angle_box(30, 1440, 15)
        self.turn_box.valueChanged.connect(
            lambda v: self._set("helix_turn", v))
        form.addRow(tr("Total turn"), self.turn_box)
        self.start_box = _angle_box(-360, 360, 15)
        self.start_box.setToolTip(tr(
            "Turns the first step about the centre."))
        self.start_box.valueChanged.connect(
            lambda v: self._set("helix_start", v))
        form.addRow(tr("Start at"), self.start_box)
        box.addWidget(self.helix_rows)
        self.column_rows, form = _form()
        self.column_box = _length_box(0.03, 3.0)
        self.column_box.valueChanged.connect(
            lambda v: self._set("column", v))
        form.addRow(tr("Post radius"), self.column_box)
        box.addWidget(self.column_rows)

        row = self.turn_buttons = QWidget()
        inside = QVBoxLayout(row)
        inside.setContentsMargins(0, 0, 0, 0)
        inside.setSpacing(4)
        self.reverse = _button(tr("Reverse"), "reverse",
                               tr("Climb from the other end (Ctrl)."))
        self.reverse.clicked.connect(
            lambda _c=False: self.tool.reverse(self.app.viewport))
        self.ends = _button(tr("Other ends"), "ends", tr(
            "When the contour could start somewhere else: tries the next "
            "pair of ends."))
        self.ends.clicked.connect(
            lambda _c=False: self.tool.next_ends(self.app.viewport))
        inside.addWidget(self.reverse)
        inside.addWidget(self.ends)
        box.addWidget(row)
        lay.addWidget(card)

    def _build_steps(self, lay) -> None:
        card = self.steps_card = Card(tr("Steps"), "steps", icon="steps",
                                      kind="column")
        box = card.body_layout
        host, form = _form()
        self.height_box = _length_box(0.1, 50.0)
        self.height_box.valueChanged.connect(
            lambda v: self._set("height", v))
        form.addRow(tr("Height"), self.height_box)
        self.steps_box = QSpinBox()
        self.steps_box.setRange(0, layoutmod.MAX_STEPS)
        self.steps_box.setSpecialValueText(tr("Automatic"))
        self.steps_box.setKeyboardTracking(False)
        self.steps_box.setToolTip(tr(
            "Number of risers. Automatic: by the rule 2 risers + 1 going = "
            "60–65 cm."))
        self.steps_box.valueChanged.connect(lambda v: self._set("steps", v))
        form.addRow(tr("Risers"), self.steps_box)
        box.addWidget(host)
        self.turns_label = _caption(tr("At the turns"))
        box.addWidget(self.turns_label)
        self.turns = Choice([
            ("landing", tr("Landing"), "landing",
             tr("A flat landing at each turn.")),
            ("winders", tr("Winders"), "winders", tr(
                "Balanced winders: the narrowing is shared with the steps "
                "around the turn."))],
            lambda v: self._set("turns", v))
        box.addWidget(self.turns)
        self.drawn = QCheckBox(tr("Follow the drawn steps"))
        self.drawn.toggled.connect(self._set_drawn)
        box.addWidget(self.drawn)
        self.result = _caption()
        self.result.setTextFormat(Qt.RichText)
        box.addWidget(self.result)
        lay.addWidget(card)

    def _build_slope(self, lay) -> None:
        card = self.slope_card = Card(tr("Slope"), "slope", icon="ramp",
                                      kind="column")
        box = card.body_layout
        host, form = _form()
        self.rise_box = _length_box(0.03, 50.0)
        self.rise_box.valueChanged.connect(lambda v: self._set("height", v))
        form.addRow(tr("Height"), self.rise_box)
        self.slope_box = QDoubleSpinBox()
        self.slope_box.setRange(0.0, 100.0)
        self.slope_box.setDecimals(2)
        self.slope_box.setSuffix(" %")
        self.slope_box.setSpecialValueText(tr("Automatic"))
        self.slope_box.setKeyboardTracking(False)
        self.slope_box.setToolTip(tr(
            "Automatic: the ramp fills the plan. With a slope, it runs only "
            "as far as that slope needs."))
        self.slope_box.valueChanged.connect(lambda v: self._set("slope", v))
        form.addRow(tr("Slope"), self.slope_box)
        box.addWidget(host)
        use_label = _caption(tr("Use"))
        use_label.setToolTip(tr(
            "Landings in long runs and warnings, after CTE DB SUA 1, 4.3 "
            "(Spain). Lengths in plan."))
        box.addWidget(use_label)
        self.use = Choice([
            ("access", tr("Accessible"), "access", tr(
                "Accessible route: 10 % up to 3 m, 8 % up to 6 m, then 6 %; "
                "flights of 9 m at most.")),
            ("walk", tr("People"), "walk",
             tr("12 % at most; flights up to 15 m.")),
            ("car", tr("Cars"), "car", tr(
                "Car park ramps also walked on: 16 % at most."))],
            lambda v: self._set("ramp_use", v))
        box.addWidget(self.use)
        self.ramp_turns_label = _caption(tr("At the turns"))
        box.addWidget(self.ramp_turns_label)
        self.ramp_turns = Choice([
            ("landing", tr("Landing"), "landing",
             tr("A flat landing at each turn.")),
            ("slope", tr("Sloping"), "winders",
             tr("The slope goes on round the turn."))],
            lambda v: self._set("ramp_turns", v))
        box.addWidget(self.ramp_turns)
        self.split = QCheckBox(tr("Landings in long runs"))
        self.split.setToolTip(tr(
            "A flight longer than the use allows is cut by a landing."))
        self.split.toggled.connect(lambda v: self._set("ramp_split", v))
        box.addWidget(self.split)
        self.landing_rows, form = _form()
        self.landing_box = _length_box(0.3, 20.0)
        self.landing_box.valueChanged.connect(
            lambda v: self._set("ramp_landing", v))
        form.addRow(tr("Landing length"), self.landing_box)
        box.addWidget(self.landing_rows)
        self.slope_result = _caption()
        self.slope_result.setTextFormat(Qt.RichText)
        box.addWidget(self.slope_result)
        lay.addWidget(card)

    def _build_code(self, lay) -> None:
        """The box with what CTE DB SUA 1 says."""
        card = self.code_card = Card("DB SUA 1", "code", icon="code",
                                     kind="column")
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setVerticalSpacing(6)
        grid.setColumnStretch(0, 1)
        #: use (or "ramp") -> (its name, its verdict)
        self.verdicts = {}
        for row, key in enumerate(dbsua.USES + ("ramp",)):
            name, verdict = _caption(), QLabel()
            verdict.setTextFormat(Qt.RichText)
            grid.addWidget(name, row, 0)
            grid.addWidget(verdict, row, 1, Qt.AlignRight | Qt.AlignVCenter)
            self.verdicts[key] = (name, verdict)
        card.body_layout.addLayout(grid)
        self.reasons = _caption()
        self.reasons.setStyleSheet(f"color: {_WARN};")
        card.body_layout.addWidget(self.reasons)
        card.setVisible(False)
        lay.addWidget(card)

    def _build_construction(self, lay) -> None:
        card = self.build_card = Card(tr("Construction"), "construction",
                                      icon="solid", kind="column")
        box = card.body_layout
        self.kind = Choice([
            ("solid", tr("Solid"), "solid",
             tr("Everything under the steps, down to the floor.")),
            ("slab", tr("Slab"), "slab",
             tr("A sloping concrete slab under the steps.")),
            ("plates", tr("Plates"), "plates", tr(
                "Steel stringers at the sides, with treads between them."))],
            lambda v: self._set("kind", v))
        box.addWidget(self.kind)

        self.slab_rows, form = _form()
        self.slab_box = _length_box(0.03, 1.0)
        self.slab_box.setToolTip(tr("Measured square to the slope."))
        self.slab_box.valueChanged.connect(lambda v: self._set("slab", v))
        form.addRow(tr("Slab thickness"), self.slab_box)
        box.addWidget(self.slab_rows)

        self.plate_rows = QWidget()
        col = QVBoxLayout(self.plate_rows)
        col.setContentsMargins(0, 0, 0, 0)
        self.risers = QCheckBox(tr("Closed risers"))
        self.risers.toggled.connect(lambda v: self._set("risers", v))
        col.addWidget(self.risers)
        col.addWidget(_caption(tr("Stringers")))
        self.sides = Choice([
            ("left", tr("Left"), "plate_left", tr("As seen going up")),
            ("both", tr("Both"), "plate_both", ""),
            ("right", tr("Right"), "plate_right", tr("As seen going up"))],
            lambda v: self._set("sides", v))
        col.addWidget(self.sides)
        host, form = _form()
        self.tread_box = _length_box(0.005, 0.2)
        self.tread_box.valueChanged.connect(lambda v: self._set("tread", v))
        form.addRow(tr("Tread thickness"), self.tread_box)
        self.tread_form, self.deck_box = form, _length_box(0.003, 0.3)
        self.deck_box.valueChanged.connect(lambda v: self._set("deck", v))
        form.addRow(tr("Deck thickness"), self.deck_box)
        self.plate_box = _length_box(0.003, 0.1)
        self.plate_box.setToolTip(tr(
            "Thickness of the stringers and the riser plates."))
        self.plate_box.valueChanged.connect(lambda v: self._set("plate", v))
        form.addRow(tr("Plate thickness"), self.plate_box)
        self.depth_box = _length_box(0.1, 1.5)
        self.depth_box.setToolTip(tr(
            "Measured upright; made taller when the steps need it."))
        self.depth_box.valueChanged.connect(lambda v: self._set("depth", v))
        form.addRow(tr("Stringer height"), self.depth_box)
        col.addWidget(host)
        box.addWidget(self.plate_rows)
        lay.addWidget(card)

    # ---- Values <-> widgets ----------------------------------------------------------------
    def _set(self, key, value) -> None:
        if self._loading:
            return
        setattr(self.settings, key, value)
        if key == "mode":
            self._swap_mode(value)
        self.settings.changed()

    def _swap_mode(self, mode) -> None:
        """A stair's height and a ramp's are seldom the same: each keeps
        its own."""
        other = self.settings.other_height
        self.settings.other_height = self.settings.height
        self.settings.height = other
        self._layout_got = (None, "")

    def _set_drawn(self, on) -> None:
        if self._loading:
            return
        self.settings.use_drawn = on
        if on:
            self.settings.steps = 0
        self.settings.changed()

    def _settings_changed(self) -> None:
        if self._busy:
            return
        self._busy = True
        try:
            self.settings.save()
            vp = self.app.viewport
            active = vp.active_tool is self.tool
            self.tool.invalidate(vp if active else None)
            if active:
                self.tool.remake(vp)
                self.tool.refresh_hint(vp)
            vp.update()
        finally:
            self._busy = False
        self.refresh()

    def refresh(self) -> None:
        s = self.settings
        self._loading = True
        try:
            ramp = s.mode == "ramp"
            self.mode.set(s.mode)
            for box, value in ((self.width_box,
                                s.ramp_width if ramp else s.width),
                               (self.rise_box, s.height),
                               (self.slope_box, s.slope),
                               (self.landing_box, s.ramp_landing),
                               (self.deck_box, s.deck),
                               (self.turn_box, s.helix_turn),
                               (self.start_box, s.helix_start),
                               (self.column_box, s.column),
                               (self.height_box, s.height),
                               (self.slab_box, s.slab),
                               (self.tread_box, s.tread),
                               (self.plate_box, s.plate),
                               (self.depth_box, s.depth)):
                if abs(box.value() - value) > 1e-9:
                    box.setValue(value)
            self.steps_box.setValue(int(s.steps))
            self.side.set(s.side)
            self.turns.set(s.turns)
            self.kind.set(s.kind)
            self.sides.set(s.sides)
            self.risers.setChecked(bool(s.risers))
            read = s.plan
            kind = read.kind if read is not None else None
            drawn = read is not None and layoutmod.has_drawn_steps(read) \
                and not ramp
            self.plan_label.setText(self._plan_text(read))
            self.path_rows.setVisible(kind == "path")
            self.helix_rows.setVisible(kind == "circle")
            self.column_rows.setVisible(kind == "circle"
                                        and read.inner_radius <= 0)
            self.turn_buttons.setVisible(read is not None)
            self.ends.setVisible(kind == "outline")
            self.drawn.setVisible(drawn)
            following = drawn and bool(s.use_drawn) and not s.steps
            self.drawn.setChecked(following)
            turns = kind in (None, "outline", "path") and not following
            self.turns.setVisible(turns)
            self.turns_label.setVisible(turns)
            self.slab_rows.setVisible(s.kind == "slab")
            self.plate_rows.setVisible(s.kind == "plates")
            self.steps_card.setVisible(not ramp)
            self.slope_card.setVisible(ramp)
            self.use.set(s.ramp_use)
            self.ramp_turns.set(s.ramp_turns)
            self.split.setChecked(bool(s.ramp_split))
            turning = kind in (None, "outline", "path")
            self.ramp_turns.setVisible(turning)
            self.ramp_turns_label.setVisible(turning)
            self.split.setVisible(s.ramp_use != "car")
            self.landing_rows.setVisible(s.ramp_use != "car"
                                         and bool(s.ramp_split))
            self.risers.setVisible(not ramp)
            self.tread_form.setRowVisible(self.tread_box, not ramp)
            self.tread_form.setRowVisible(self.deck_box, ramp)
            self.draw.setText(tr("Raise the ramp") if ramp
                              else tr("Raise the stair"))
            self.draw.setIcon(icons.icon("ramp" if ramp else "stairs"))
            self._write_result()
        finally:
            self._loading = False

    def _plan_text(self, read) -> str:
        if read is None:
            return tr("No plan taken")
        if read.kind == "circle":
            return tr("Circle (helical stair)")
        if read.kind == "path":
            return tr("Open line")
        if read.chords:
            return tr("Contour with {n} drawn steps", n=len(read.chords))
        return tr("Contour")

    def _show_layout(self, lay, error) -> None:
        self._layout_got = (lay, error)
        if hasattr(self, "slope_result") and not self._busy:
            self._write_result()

    def _write_result(self) -> None:
        ramp = self.settings.mode == "ramp"
        text = self._ramp_text() if ramp else self._result_text()
        for label in (self.result, self.slope_result):
            label.setText(text)
            label.setVisible(bool(text))
        self._write_verdict()

    def _write_verdict(self) -> None:
        """Whether the stair complies, use by use, or the ramp for its own.
        Why not: in each line's tooltip, and for a ramp written below too."""
        lay, error = self._layout_got
        ramp = self.settings.mode == "ramp"
        known = not (error or lay is None or self.settings.plan is None
                     or hasattr(lay, "flights") != ramp)
        self.code_card.setVisible(known)
        if not known:
            return
        for key, row in self.verdicts.items():
            for label in row:
                label.setVisible((key == "ramp") == ramp)
        self.reasons.setVisible(False)
        if ramp:
            failed = dbsua.check_ramp(lay, self.settings.ramp_use)
            names = {"access": tr("Accessible"), "walk": tr("People"),
                     "car": tr("Cars")}
            self._show_verdict(
                "ramp", names[self.settings.ramp_use], failed, tr(
                    "Not checked: widths off accessible routes, the level "
                    "1.20 m at the ends of flights, landings at turns, doors, "
                    "cross slope, handrails, kerbs, DB SUA 7."))
            self.reasons.setText("\n".join(
                tr(key, **_localised(values)) for key, values in failed))
            self.reasons.setVisible(bool(failed))
            return
        names = {"restricted": tr("Restricted use"),
                 "general": tr("General use"),
                 "public": tr("Public or no lift")}
        unchecked = tr(
            "Sizes only. Not checked: the width of table 4.1 and DB SI, "
            "handrails, guards, closed risers, headroom, doors by the "
            "landings.")
        for use in dbsua.USES:
            self._show_verdict(use, names[use], dbsua.check(lay, use),
                               unchecked)

    def _show_verdict(self, key, title, failed, unchecked) -> None:
        colour, words = (_WARN, "\u2717 " + tr("Does not comply")) if failed \
            else (_OK, "\u2713 " + tr("Complies"))
        name, verdict = self.verdicts[key]
        name.setText(title)
        verdict.setText(f'<b style="color:{colour}">{words}</b>')
        tip = "".join(f"<li>{tr(k, **_localised(values))}</li>"
                      for k, values in failed)
        tip = f"<ul>{tip}</ul>" if tip else ""
        for label in (name, verdict):
            label.setToolTip(f"<qt>{tip}{unchecked}</qt>")

    def _ramp_text(self) -> str:
        lay, error = self._layout_got
        if error:
            return f'<span style="color:{_WARN}">{error}</span>'
        if lay is None or self.settings.plan is None \
                or not hasattr(lay, "flights"):
            return ""
        failed = dbsua.check_ramp(lay, self.settings.ramp_use)
        steep = any(key.startswith("Over {p}") for key, _v in failed)
        slope = f"{_num(lay.slope * 100, 2)} %"
        if steep:
            slope = f'<span style="color:{_WARN}">{slope}</span>'
        rows = [(tr("Slope"), slope),
                (tr("Sloping length"), f"{_num(lay.run, 2)} m"),
                (tr("Flights"), f"{len(lay.flights)}"),
                (tr("Longest flight"), f"{_num(lay.longest, 2)} m")]
        text = _table(rows)
        for w in self._ramp_warnings(lay):
            text += f'<div style="color:{_WARN}">{w}</div>'
        if lay.spare > 0.05:
            text += "<div>" + tr("The plan has {m} m to spare.",
                                 m=_num(lay.spare, 2)) + "</div>"
        return text

    def _ramp_warnings(self, lay) -> list:
        s = self.settings
        out = []
        if lay.worst() <= rampmod.NOT_A_RAMP + 5e-5:
            out.append(tr("Up to 4 % the code does not call it a ramp."))
        if lay.missing > 0.005:
            out.append(tr("{m} m of run missing for {p} %: the plan is "
                          "filled.", m=_num(lay.missing, 2),
                          p=f"{lay.asked * 100:g}"))
        side = lay.steepest_side()
        if side > lay.slope * 1.01:
            out.append(tr("At the least favourable side: {p} % (it is the "
                          "one that counts).", p=_num(side * 100, 2)))
        if lay.helix:
            if s.slope:
                out.append(tr("Turns {a}°.", a=f"{lay.turned:.0f}"))
            if lay.turned > 360.5:
                out.append(tr("A solid stair over one turn would run into "
                              "itself: use slab or plates.")
                           if s.kind == "solid"
                           else tr("Over one turn: check the headroom."))
        return out

    def _result_text(self) -> str:
        lay, error = self._layout_got
        if error:
            return f'<span style="color:{_WARN}">{error}</span>'
        if lay is None or self.settings.plan is None \
                or hasattr(lay, "flights"):
            return ""
        warnings = self._warnings(lay)
        in_rule = layoutmod.RULE_MIN - 5e-4 <= lay.rule \
            <= layoutmod.RULE_MAX + 5e-4
        rule = f"{_cm(lay.rule)} cm"
        if not in_rule:
            rule = f'<span style="color:{_WARN}">{rule}</span>'
        rows = [(tr("Risers"), f"{lay.count}"),
                (tr("Riser"), f"{_cm(lay.riser)} cm"),
                (tr("Going"), f"{_cm(lay.going)} cm"),
                (tr("2 risers + going"), rule)]
        text = _table(rows)
        if lay.landings:
            n = len(lay.landings)
            text += tr("{n} landing" if n == 1 else "{n} landings", n=n)
        for w in warnings:
            text += f'<div style="color:{_WARN}">{w}</div>'
        return text

    def _warnings(self, lay) -> list:
        s = self.settings
        out = []
        if not layoutmod.RULE_MIN - 5e-4 <= lay.rule \
                <= layoutmod.RULE_MAX + 5e-4:
            out.append(tr("Outside the rule (60–65)."))
        goings = lay.goings()
        if lay.drawn and goings and max(goings) - min(goings) > 0.02:
            out.append(tr("The drawn goings are uneven."))
        if lay.helix and s.helix_turn > 360.5:
            out.append(tr("A solid stair over one turn would run into itself: "
                          "use slab or plates.") if s.kind == "solid"
                       else tr("Over one turn: check the headroom."))
        return out

    # ---- The tool -------------------------------------------------------------------------------
    def _selected_plan(self):
        from core.group import Group

        from .build import KEY
        groups = [e for e in self.app.scene.selection
                  if isinstance(e, Group) and KEY not in (e.ext or {})]
        return groups[0] if len(groups) == 1 else None

    def start(self, complain=False) -> None:
        """Take up the tool, on the selected plan if there is one."""
        picked = self._selected_plan()
        if complain and picked is None:
            self.message.setText(tr("Select one group: the one with the "
                                    "plan."))
            return
        self.message.clear()
        vp = self.app.viewport
        if vp.active_tool is not self.tool:
            vp.set_active_tool(self.tool)
        self.draw.setChecked(True)
        if picked is not None:
            self.tool.load(vp, picked)
        self.tool.refresh_hint(vp)
        vp.setFocus()
        self.refresh()

    def stop(self) -> None:
        vp = self.app.viewport
        if vp.active_tool is not self.tool:
            self.draw.setChecked(False)
            return
        go = getattr(self.app.window, "_activate_tool", None)
        if callable(go):
            go("select")
        else:
            vp.set_active_tool(None)

    def _tool_state(self, active: bool) -> None:
        if not hasattr(self, "draw"):
            return
        self.draw.setChecked(active)
        if active:
            self.settings.save()           # a height just clicked
        else:
            self.message.clear()
            self._layout_got = (None, "")
        self.refresh()
