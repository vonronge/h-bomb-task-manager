from __future__ import annotations

import math

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

_CACHE: dict[tuple[str, str, int], QIcon] = {}


def nav_icon(name: str, color: QColor, size: int = 18) -> QIcon:
    key = (name, color.name(), size)
    hit = _CACHE.get(key)
    if hit is not None:
        return hit
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(color, 1.4)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    r = QRect(2, 2, size - 4, size - 4)
    _draw(p, name, r, color)
    p.end()
    icon = QIcon(pm)
    _CACHE[key] = icon
    return icon


def _draw(p: QPainter, name: str, r: QRect, color: QColor) -> None:
    x, y, w, h = r.x(), r.y(), r.width(), r.height()
    if name == "summary":
        p.drawLine(x + w * 0.15, y + h * 0.55, x + w * 0.5, y + h * 0.2)
        p.drawLine(x + w * 0.5, y + h * 0.2, x + w * 0.85, y + h * 0.55)
        p.drawRect(int(x + w * 0.28), int(y + h * 0.5), int(w * 0.44), int(h * 0.38))
    elif name == "performance":
        path = QPainterPath()
        path.moveTo(x, y + h * 0.7)
        path.lineTo(x + w * 0.22, y + h * 0.45)
        path.lineTo(x + w * 0.42, y + h * 0.62)
        path.lineTo(x + w * 0.62, y + h * 0.22)
        path.lineTo(x + w * 0.82, y + h * 0.4)
        path.lineTo(x + w, y + h * 0.28)
        p.drawPath(path)
    elif name == "processes":
        p.drawRect(x, y, int(w * 0.28), int(h * 0.28))
        p.drawRect(int(x + w * 0.4), y, int(w * 0.6), int(h * 0.22))
        p.drawRect(x, int(y + h * 0.38), int(w * 0.28), int(h * 0.28))
        p.drawRect(int(x + w * 0.4), int(y + h * 0.38), int(w * 0.6), int(h * 0.22))
        p.drawRect(x, int(y + h * 0.74), int(w * 0.28), int(h * 0.26))
        p.drawRect(int(x + w * 0.4), int(y + h * 0.76), int(w * 0.6), int(h * 0.22))
    elif name == "sysinfo":
        p.drawEllipse(r)
        p.drawLine(int(x + w * 0.5), int(y + h * 0.42), int(x + w * 0.5), int(y + h * 0.78))
        p.drawPoint(int(x + w * 0.5), int(y + h * 0.28))
    elif name == "startup":
        path = QPainterPath()
        path.moveTo(x + w * 0.15, y + h * 0.75)
        path.lineTo(x + w * 0.55, y + h * 0.18)
        path.lineTo(x + w * 0.85, y + h * 0.55)
        path.closeSubpath()
        p.drawPath(path)
        p.drawLine(int(x + w * 0.2), int(y + h * 0.8), int(x + w * 0.45), int(y + h * 0.55))
    elif name == "users":
        p.drawEllipse(int(x + w * 0.12), int(y + h * 0.08), int(w * 0.32), int(h * 0.32))
        p.drawArc(int(x), int(y + h * 0.42), int(w * 0.55), int(h * 0.55), 20 * 16, 140 * 16)
        p.drawEllipse(int(x + w * 0.52), int(y + h * 0.22), int(w * 0.28), int(h * 0.28))
        p.drawArc(int(x + w * 0.42), int(y + h * 0.52), int(w * 0.55), int(h * 0.48), 20 * 16, 140 * 16)
    elif name == "services":
        p.drawEllipse(int(x + w * 0.28), int(y + h * 0.12), int(w * 0.44), int(h * 0.44))
        p.drawLine(int(x + w * 0.5), int(y + h * 0.56), int(x + w * 0.5), int(y + h * 0.92))
        p.drawLine(int(x + w * 0.32), int(y + h * 0.78), int(x + w * 0.68), int(y + h * 0.78))
    elif name == "power":
        path = QPainterPath()
        path.moveTo(x + w * 0.55, y)
        path.lineTo(x + w * 0.28, y + h * 0.52)
        path.lineTo(x + w * 0.52, y + h * 0.52)
        path.lineTo(x + w * 0.42, y + h)
        path.lineTo(x + w * 0.78, y + h * 0.4)
        path.lineTo(x + w * 0.52, y + h * 0.4)
        path.closeSubpath()
        p.drawPath(path)
    elif name == "connections":
        p.drawEllipse(r)
        p.drawEllipse(int(x + w * 0.22), y, int(w * 0.56), h)
        p.drawLine(x, int(y + h * 0.5), x + w, int(y + h * 0.5))
    elif name == "apps":
        for i in range(2):
            for j in range(2):
                p.drawRoundedRect(
                    int(x + i * (w * 0.55)),
                    int(y + j * (h * 0.55)),
                    int(w * 0.4),
                    int(h * 0.4),
                    2,
                    2,
                )
    elif name == "disk":
        p.drawRoundedRect(r, 3, 3)
        p.drawLine(x, int(y + h * 0.35), x + w, int(y + h * 0.35))
        p.drawEllipse(int(x + w * 0.7), int(y + h * 0.08), int(w * 0.16), int(h * 0.16))
    elif name == "more":
        for i in range(3):
            for j in range(3):
                p.drawEllipse(
                    int(x + w * (0.12 + i * 0.32)),
                    int(y + h * (0.12 + j * 0.32)),
                    int(w * 0.16),
                    int(h * 0.16),
                )
    elif name == "benchmarks":
        p.drawArc(r, 20 * 16, 140 * 16)
        p.drawLine(int(x + w * 0.5), int(y + h * 0.55), int(x + w * 0.78), int(y + h * 0.28))
        p.drawEllipse(int(x + w * 0.42), int(y + h * 0.48), int(w * 0.16), int(h * 0.16))
    elif name == "flight":
        p.drawEllipse(r.adjusted(1, 1, -1, -1))
        p.setBrush(color)
        p.drawEllipse(int(x + w * 0.32), int(y + h * 0.32), int(w * 0.36), int(h * 0.36))
        p.setBrush(Qt.BrushStyle.NoBrush)
    elif name == "journal":
        p.drawRoundedRect(r, 2, 2)
        p.drawLine(int(x + w * 0.22), int(y + h * 0.3), int(x + w * 0.78), int(y + h * 0.3))
        p.drawLine(int(x + w * 0.22), int(y + h * 0.5), int(x + w * 0.78), int(y + h * 0.5))
        p.drawLine(int(x + w * 0.22), int(y + h * 0.7), int(x + w * 0.62), int(y + h * 0.7))
    elif name == "mounts":
        p.drawRect(int(x + w * 0.15), int(y + h * 0.2), int(w * 0.7), int(h * 0.55))
        p.drawLine(int(x + w * 0.3), int(y + h * 0.75), int(x + w * 0.3), int(y + h * 0.9))
        p.drawLine(int(x + w * 0.7), int(y + h * 0.75), int(x + w * 0.7), int(y + h * 0.9))
        p.drawLine(int(x + w * 0.2), int(y + h * 0.9), int(x + w * 0.8), int(y + h * 0.9))
    elif name == "settings":
        p.drawEllipse(int(x + w * 0.28), int(y + h * 0.28), int(w * 0.44), int(h * 0.44))
        cx, cy = x + w / 2, y + h / 2
        for i in range(8):
            a = i * math.pi / 4
            p.drawLine(
                QPoint(int(cx + math.cos(a) * w * 0.22), int(cy + math.sin(a) * h * 0.22)),
                QPoint(int(cx + math.cos(a) * w * 0.46), int(cy + math.sin(a) * h * 0.46)),
            )
    elif name == "colors":
        p.drawEllipse(int(x + w * 0.08), int(y + h * 0.28), int(w * 0.44), int(h * 0.44))
        p.drawEllipse(int(x + w * 0.38), int(y + h * 0.08), int(w * 0.4), int(h * 0.4))
        p.drawEllipse(int(x + w * 0.48), int(y + h * 0.42), int(w * 0.4), int(h * 0.4))
    elif name == "menu":
        p.drawLine(x, int(y + h * 0.25), x + w, int(y + h * 0.25))
        p.drawLine(x, int(y + h * 0.5), x + w, int(y + h * 0.5))
        p.drawLine(x, int(y + h * 0.75), x + w, int(y + h * 0.75))
    elif name == "refresh":
        p.drawArc(r.adjusted(1, 1, -1, -1), 40 * 16, 260 * 16)
        p.drawLine(int(x + w * 0.72), y, int(x + w * 0.92), int(y + h * 0.08))
        p.drawLine(int(x + w * 0.72), y, int(x + w * 0.78), int(y + h * 0.28))
    elif name == "search":
        p.drawEllipse(x, y, int(w * 0.62), int(h * 0.62))
        p.drawLine(int(x + w * 0.55), int(y + h * 0.55), int(x + w * 0.92), int(y + h * 0.92))
    elif name == "chip":
        p.drawRoundedRect(r.adjusted(2, 4, -2, -4), 2, 2)
        for i in range(3):
            p.drawLine(x, int(y + h * (0.3 + i * 0.2)), int(x + 2), int(y + h * (0.3 + i * 0.2)))
            p.drawLine(x + w, int(y + h * (0.3 + i * 0.2)), int(x + w - 2), int(y + h * (0.3 + i * 0.2)))
    elif name == "thermo":
        p.drawEllipse(int(x + w * 0.28), int(y + h * 0.55), int(w * 0.44), int(h * 0.42))
        p.drawRoundedRect(int(x + w * 0.4), y, int(w * 0.2), int(h * 0.7), 3, 3)
    elif name == "wave":
        path = QPainterPath()
        path.moveTo(x, y + h * 0.6)
        path.lineTo(x + w * 0.25, y + h * 0.3)
        path.lineTo(x + w * 0.5, y + h * 0.7)
        path.lineTo(x + w * 0.75, y + h * 0.25)
        path.lineTo(x + w, y + h * 0.5)
        p.drawPath(path)
    else:
        p.drawRect(r)
