# SPDX-License-Identifier: GPL-3.0-or-later
"""CTE Stairs and ramps, the first of a series of IngeTrazo extensions
tied to the Spanish building code (CTE): raise a stair from its drawing in plan — straight, L,
U, helical, with landings or balanced winders; and ramps over the same
plans. Solid, concrete slab, or steel stringers.

An extension for IngeTrazo (setup(app), docs/plugins.md).

Install: copy the ``cte_stairs`` folder into IngeTrazo's plugins folder
(Extensions ▸ Open plugins folder) and restart IngeTrazo.
"""
from __future__ import annotations

__version__ = "0.3.0"


def _language() -> str:
    from core.i18n import current_language
    return current_language()


def setup(app) -> None:
    from . import icons, texts
    texts.LANGUAGE = _language
    from .panel import StairPanel
    panel = StairPanel(app)
    dock = app.add_panel(texts.tr("CTE Stairs and ramps"), panel,
                         **icons.panel_icon(app, "stairs"))
    app.add_menu_action(
        texts.tr("CTE Stairs and ramps…"), lambda: app.show_panel(dock),
        tip=texts.tr("Show the tab: stairs and ramps raised from a plan "
                     "drawing."))
