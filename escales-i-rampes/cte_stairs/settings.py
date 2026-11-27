# SPDX-License-Identifier: GPL-3.0-or-later
"""The live values the panel and the tool share. All lengths in metres."""
from __future__ import annotations

import json

from . import build, layout, ramp

_STORE = "cte_stairs/settings"


class Settings:
    SAVED = ("height", "turns", "use_drawn", "width", "side", "helix_turn",
             "column", "kind", "slab", "tread", "risers", "plate", "depth",
             "sides", "mode", "ramp_use", "ramp_turns", "ramp_split",
             "ramp_landing", "ramp_width", "deck", "other_height")
    #: These belong to the plan in hand: a new one starts from nothing.
    PER_PLAN = {"steps": 0, "flip": False, "end_choice": 0,
                "helix_start": 0.0, "slope": 0.0}

    def __init__(self) -> None:
        o, b = layout.Options(), build.Build()
        self.height = o.height
        self.turns = o.turns
        self.use_drawn = o.use_drawn
        self.width = o.width
        self.side = o.side
        self.helix_turn = o.helix_turn
        self.column = o.column
        self.kind = b.kind
        self.slab = b.slab
        self.tread = b.tread
        self.risers = b.risers
        self.plate = b.plate
        self.depth = b.depth
        self.sides = b.sides
        r = ramp.Options()
        self.mode = "stair"                    # "stair" | "ramp"
        self.ramp_use = r.use
        self.ramp_turns = r.turns
        self.ramp_split = r.split
        self.ramp_landing = r.landing
        self.ramp_width = r.width
        self.deck = 0.03                       # steel ramp: deck thickness
        #: The height of the mode not in use (stair 2.80, ramp 0.60).
        self.other_height = r.height
        self.reset_plan()
        #: The plan being worked on (``plan.Plan``), this session only.
        self.plan = None
        self.on_change = None

    def reset_plan(self) -> None:
        for key, value in self.PER_PLAN.items():
            setattr(self, key, value)

    def load(self) -> None:
        from PySide6.QtCore import QSettings
        try:
            data = json.loads(str(QSettings().value(_STORE, "") or "{}"))
        except (TypeError, ValueError):
            return
        for key in self.SAVED:
            if key in data and isinstance(data[key], (bool, int, float, str)):
                setattr(self, key, data[key])

    def save(self) -> None:
        from PySide6.QtCore import QSettings
        QSettings().setValue(_STORE, json.dumps(
            {k: getattr(self, k) for k in self.SAVED}))

    def changed(self) -> None:
        if self.on_change is not None:
            self.on_change()

    def options(self, height=None) -> layout.Options:
        return layout.Options(
            height=self.height if height is None else height,
            steps=int(self.steps), turns=self.turns,
            use_drawn=bool(self.use_drawn), flip=bool(self.flip),
            width=self.width, side=self.side, helix_turn=self.helix_turn,
            helix_start=self.helix_start, column=self.column)

    def ramp_options(self, height=None) -> ramp.Options:
        return ramp.Options(
            height=self.height if height is None else height,
            slope=float(self.slope), use=self.ramp_use,
            turns=self.ramp_turns, split=bool(self.ramp_split),
            landing=self.ramp_landing, flip=bool(self.flip),
            width=self.ramp_width, side=self.side,
            helix_turn=self.helix_turn, helix_start=self.helix_start,
            column=self.column)

    def building(self) -> build.Build:
        tread = self.deck if self.mode == "ramp" else self.tread
        return build.Build(self.kind, self.slab, tread,
                           bool(self.risers), self.plate, self.depth,
                           self.sides)

    def info(self) -> dict:
        """What the stair was made with, kept in the group."""
        keys = self.SAVED + tuple(self.PER_PLAN)
        return {k: getattr(self, k) for k in keys}
