# SPDX-License-Identifier: GPL-3.0-or-later
"""Icons in the style of IngeTrazo's own, drawn by code (the base is the
style guide's)."""
from __future__ import annotations

import math

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, Qt
from PySide6.QtGui import (
    QColor, QIcon, QIconEngine, QPainter, QPainterPath, QPen, QPixmap,
    QPolygonF)
from PySide6.QtWidgets import QApplication

_PX = 48
#: Line width as IngeTrazo draws it (3.0 at 65 %): about 1 px at 24 px.
_WIDTH = 3.0 * 0.65


def _ink() -> QColor:
    try:
        from views.theme import icon_ink
        return icon_ink()
    except Exception:  # noqa: BLE001 - outside the app
        app = QApplication.instance()
        if app is not None:
            c = app.palette().windowText().color()
            return QColor(c.red(), c.green(), c.blue())
        return QColor(40, 44, 52)


def _accent() -> QColor:
    try:
        from views.theme import accent_color
        return accent_color()
    except Exception:  # noqa: BLE001
        return QColor(232, 116, 42)


def _pen(color: QColor, width: float = _WIDTH, style=Qt.SolidLine) -> QPen:
    pen = QPen(color, width, style)
    pen.setJoinStyle(Qt.RoundJoin)
    pen.setCapStyle(Qt.RoundCap)
    return pen


def _fill(p: QPainter, shape, alpha: int) -> None:
    """``shape`` (a polygon or path) filled with the accent, no outline."""
    p.save()
    p.setPen(Qt.NoPen)
    c = _accent()
    c.setAlpha(alpha)
    p.setBrush(c)
    if isinstance(shape, QPainterPath):
        p.drawPath(shape)
    else:
        p.drawPolygon(shape)
    p.restore()


def _dot(p: QPainter, x: float, y: float, r: float = 3.0) -> None:
    p.save()
    p.setPen(Qt.NoPen)
    p.setBrush(_accent())
    p.drawEllipse(QPointF(x, y), r, r)
    p.restore()


def _cube(p: QPainter, ink: QColor, cx: float, cy: float, r: float) -> None:
    """A cube seen corner-on, ``r`` from its centre to its top vertex,
    its faces tinted as IngeTrazo's boxes are."""
    k = 0.866 * r
    t, b = QPointF(cx, cy - r), QPointF(cx, cy + r)
    ul, ur = QPointF(cx - k, cy - r / 2), QPointF(cx + k, cy - r / 2)
    ll, lr = QPointF(cx - k, cy + r / 2), QPointF(cx + k, cy + r / 2)
    c = QPointF(cx, cy)
    left, right, lid = (QPolygonF([ul, c, b, ll]), QPolygonF([c, ur, lr, b]),
                        QPolygonF([t, ur, c, ul]))
    _fill(p, left, 150)
    _fill(p, right, 90)
    _fill(p, lid, 50)
    p.setBrush(Qt.NoBrush)
    for face in (left, right, lid):
        p.drawPolygon(face)


def _line(p, *pts):
    p.drawPolyline(QPolygonF([QPointF(x, y) for x, y in pts]))


def _box(p, x, y, w, h, alpha=90):
    r = QRectF(x, y, w, h)
    _fill(p, QPolygonF([r.topLeft(), r.topRight(), r.bottomRight(), r.bottomLeft()]), alpha)
    p.drawRect(r)


def _poly(p, pts, alpha=90):
    shape = [QPointF(x, y) for x, y in pts]
    _fill(p, QPolygonF(shape), alpha)
    _line(p, *pts, pts[0])


_FLIGHT = [(6, 42), (6, 32), (16, 32), (16, 24), (26, 24), (26, 16),
           (36, 16), (36, 8), (42, 8)]


def _stairs(p, ink):
    _poly(p, _FLIGHT + [(42, 42)])


def _solid(p, ink):
    _poly(p, _FLIGHT + [(42, 42)], 150)


def _slab(p, ink):
    _poly(p, _FLIGHT + [(42, 18), (18, 42)], 150)


def _plates(p, ink):
    _poly(p, [(6, 34), (34, 8), (42, 8), (42, 16), (14, 42), (6, 42)], 60)
    p.save()
    p.setPen(_pen(_accent(), 4.0))
    for x, y in ((10, 32), (20, 23), (30, 14)):
        _line(p, (x - 4, y), (x + 12, y))
    p.restore()


def _ramp(p, ink):
    _poly(p, [(4, 42), (30, 16), (44, 16), (44, 42)], 150)


def _access(p, ink):                          # a wheelchair, plainly
    _dot(p, 20, 8, 4.5)
    _line(p, (20, 15), (20, 28), (31, 28), (36, 40), (42, 38))
    _line(p, (20, 21), (29, 21))
    p.drawArc(QRectF(8, 20, 22, 22), 40 * 16, -275 * 16)


def _walk(p, ink):
    _dot(p, 27, 8, 4.5)
    _line(p, (25, 15), (22, 28), (30, 34), (31, 44))
    _line(p, (22, 28), (14, 42))
    _line(p, (25, 17), (17, 23), (15, 30))
    _line(p, (25, 17), (32, 25), (39, 26))


def _code(p, ink):                           # a sheet with a tick
    _poly(p, [(10, 6), (30, 6), (38, 14), (38, 42), (10, 42)], 40)
    _line(p, (30, 6), (30, 14), (38, 14))
    p.save()
    p.setPen(_pen(_accent(), 4.5))
    _line(p, (16, 28), (22, 35), (33, 21))
    p.restore()


def _car(p, ink):
    _poly(p, [(6, 34), (6, 26), (12, 24), (17, 15), (32, 15), (38, 24),
              (43, 26), (43, 34)], 90)
    for x in (14, 35):
        _dot(p, x, 35, 5.0)


def _plan(p, ink):                            # a stair seen from above
    _poly(p, [(8, 6), (24, 6), (24, 26), (42, 26), (42, 42), (8, 42)], 50)
    for y in (13, 20, 26):
        _line(p, (8, y), (24, y))
    for x in (24, 33):
        _line(p, (x, 26), (x, 42))


def _steps(p, ink):
    _line(p, *_FLIGHT)
    _dot(p, 6, 42, 3.5)
    _dot(p, 42, 8, 3.5)


def _landing(p, ink):
    _poly(p, [(8, 6), (42, 6), (42, 40), (24, 40), (24, 24), (8, 24)], 40)
    _poly(p, [(8, 6), (24, 6), (24, 24), (8, 24)], 160)
    _line(p, (33, 24), (42, 24))
    _line(p, (24, 32), (42, 32))


def _winders(p, ink):
    _poly(p, [(8, 6), (42, 6), (42, 40), (26, 40), (26, 24), (8, 24)], 40)
    for x, y in ((8, 15), (8, 6), (22, 6), (36, 6), (42, 14), (42, 28)):
        _line(p, (26, 24), (x, y))


def _side(p, x):                              # the drawn line against the stair
    _box(p, 14, 14, 20, 22, 60)
    for y in (21, 29):
        _line(p, (14, y), (34, y))
    p.save()
    p.setPen(_pen(_accent(), 4.0))
    _line(p, (x, 6), (x, 44))
    p.restore()


def _side_left(p, ink):
    _side(p, 14)


def _side_centre(p, ink):
    _side(p, 24)


def _side_right(p, ink):
    _side(p, 34)


def _plate_marks(p, *xs):
    _box(p, 10, 12, 28, 26, 30)
    for y in (20, 29):
        _line(p, (10, y), (38, y))
    p.save()
    p.setPen(_pen(_accent(), 5.0))
    for x in xs:
        _line(p, (x, 8), (x, 42))
    p.restore()


def _plate_left(p, ink):
    _plate_marks(p, 10)


def _plate_both(p, ink):
    _plate_marks(p, 10, 38)


def _plate_right(p, ink):
    _plate_marks(p, 38)


def _reverse(p, ink):
    _line(p, (8, 16), (40, 16))
    _line(p, (33, 9), (40, 16), (33, 23))
    p.save()
    p.setPen(_pen(_accent(), 3.0))
    _line(p, (40, 34), (8, 34))
    _line(p, (15, 27), (8, 34), (15, 41))
    p.restore()


def _ends(p, ink):
    _box(p, 10, 10, 28, 28, 40)
    p.save()
    p.setPen(_pen(_accent(), 5.0))
    _line(p, (10, 38), (38, 38))
    _line(p, (38, 10), (38, 38))
    p.restore()


def _take(p, ink):                            # an arrow pointing at something
    pts = [(14, 8), (14, 36), (22, 29), (28, 41), (34, 38), (28, 27), (38, 26)]
    _fill(p, QPolygonF([QPointF(x, y) for x, y in pts]), 120)
    _line(p, *pts, pts[0])


def _side(p, x):                              # the traced line against the profile
    _box(p, 14, 14, 20, 22)
    p.save()
    p.setPen(_pen(_accent(), 4.0))
    _line(p, (x, 6), (x, 44))
    p.restore()


def _side_left(p, ink):
    _side(p, 14)


def _side_centre(p, ink):
    _side(p, 24)


def _side_right(p, ink):
    _side(p, 34)


_DRAW = {
    "code": _code,
    "ramp": _ramp, "access": _access, "walk": _walk, "car": _car,
    "stairs": _stairs, "solid": _solid, "slab": _slab, "plates": _plates,
    "plan": _plan, "steps": _steps, "landing": _landing,
    "winders": _winders, "take": _take, "side_left": _side_left,
    "side_centre": _side_centre, "side_right": _side_right,
    "plate_left": _plate_left, "plate_both": _plate_both,
    "plate_right": _plate_right, "reverse": _reverse, "ends": _ends,
}


class _Engine(QIconEngine):
    """Paints the drawing at whatever size is asked, with the ink and the
    accent of the moment (so a theme change needs no redrawing)."""

    def __init__(self, key: str) -> None:
        super().__init__()
        self._key = key

    def clone(self):
        return _Engine(self._key)

    def key(self):
        return "ingetrazo-ext-icon"

    def paint(self, painter, rect, mode, state):
        draw = _DRAW.get(self._key)
        if draw is None:
            return
        ink = _ink()
        painter.save()
        if mode == QIcon.Disabled:
            painter.setOpacity(painter.opacity() * 0.35)      # all of it, the accent too: half of it lit looked usable
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.translate(rect.x(), rect.y())
        painter.scale(rect.width() / _PX, rect.height() / _PX)
        painter.setPen(_pen(ink))
        painter.setBrush(Qt.NoBrush)
        draw(painter, ink)
        painter.restore()

    def pixmap(self, size, mode, state):
        pm = QPixmap(size)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        self.paint(p, QRect(QPoint(0, 0), size), mode, state)
        p.end()
        return pm


def icon(key: str) -> QIcon:
    """The icon for ``key`` (a null icon for an unknown key)."""
    if key not in _DRAW:
        return QIcon()
    return QIcon(_Engine(key))


def panel_icon(app, key: str) -> dict:
    """``{"icon": icon(key)}`` to splat into ``app.add_panel(...)`` when
    this IngeTrazo takes one (older versions would refuse the argument
    and keep showing the title's initial)."""
    import inspect
    try:
        if "icon" in inspect.signature(app.add_panel).parameters:
            return {"icon": icon(key)}
    except (TypeError, ValueError):
        pass
    return {}
