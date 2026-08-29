from __future__ import annotations

import math
import random
from PySide6.QtCore import Qt, QRectF, QTimer
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont
from PySide6.QtWidgets import QWidget, QTreeWidget, QTreeWidgetItem, QHeaderView

from hbomb.providers.linux.diskspace import DiskNode, squarify
from hbomb.ui.fmt import bytes_h, compact_bytes
from hbomb.ui.theme import Theme


_EXT_COLORS = {
    ".py": QColor("#3dff8a"),
    ".so": QColor("#4da3ff"),
    ".bin": QColor("#4da3ff"),
    ".png": QColor("#ffb347"),
    ".jpg": QColor("#ffb347"),
    ".mp4": QColor("#ff6b4a"),
    ".mkv": QColor("#ff6b4a"),
    ".pdf": QColor("#b07cff"),
    ".zip": QColor("#d4a017"),
    ".deb": QColor("#5ad0ff"),
}


def _color_for(node: DiskNode, theme: Theme | None) -> QColor:
    if node.ext in _EXT_COLORS:
        return _EXT_COLORS[node.ext]
    h = hash(node.ext or node.name) % 360
    c = QColor()
    c.setHsv(h, 160, 220)
    return c


class TreemapWidget(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.root: DiskNode | None = None
        self.current: DiskNode | None = None
        self.theme: Theme | None = None
        self._rects: list[tuple[DiskNode, float, float, float, float]] = []
        self._hover: DiskNode | None = None
        self.setMouseTracking(True)

    def set_tree(self, root: DiskNode) -> None:
        self.root = root
        self.current = root
        self.update()

    def zoom_out(self) -> None:
        if self.current is None or self.root is None:
            return
        parent_path = self.current.path.rsplit("/", 1)[0] or "/"
        self.current = self._find(self.root, parent_path) or self.root
        self.update()

    def _find(self, node: DiskNode, path: str) -> DiskNode | None:
        if node.path == path:
            return node
        for ch in node.children:
            hit = self._find(ch, path)
            if hit:
                return hit
        return None

    def mousePressEvent(self, ev) -> None:
        pos = ev.position()
        for node, x, y, w, h in self._rects:
            if x <= pos.x() <= x + w and y <= pos.y() <= y + h:
                if node.is_dir and node.children:
                    self.current = node
                    self.update()
                break

    def mouseMoveEvent(self, ev) -> None:
        pos = ev.position()
        hit = None
        for node, x, y, w, h in self._rects:
            if x <= pos.x() <= x + w and y <= pos.y() <= y + h:
                hit = node
                break
        if hit is not self._hover:
            self._hover = hit
            if hit:
                self.setToolTip(f"{hit.path}\n{bytes_h(hit.size)}")
            else:
                self.setToolTip("")
            self.update()

    def leaveEvent(self, _ev) -> None:
        self._hover = None
        self.setToolTip("")
        self.update()

    def _draw_tile_label(self, p: QPainter, child: DiskNode, x: float, y: float, w: float, h: float) -> None:
        if w < 22 or h < 14:
            return
        rect = QRectF(x + 2, y + 2, w - 4, h - 4)
        name = child.name
        if len(name) * 6 > rect.width():
            name = name[: max(1, int(rect.width() / 6) - 1)] + "…"
        size = compact_bytes(child.size)
        font = QFont("Inter", 8 if h < 28 else 9)
        p.setFont(font)
        lines = [name]
        if h >= 20 and rect.width() >= 28:
            lines.append(size)
        yoff = rect.top()
        for line in lines:
            p.setPen(QColor(0, 0, 0, 200))
            p.drawText(QRectF(rect.x() + 1, yoff + 1, rect.width(), 14), Qt.AlignmentFlag.AlignLeft, line)
            p.setPen(QColor(255, 255, 255))
            p.drawText(QRectF(rect.x(), yoff, rect.width(), 14), Qt.AlignmentFlag.AlignLeft, line)
            yoff += 13

    def paintEvent(self, _ev) -> None:
        p = QPainter(self)
        p.fillRect(self.rect(), self.theme.panel if self.theme else QColor("#101216"))
        node = self.current or self.root
        if not node:
            p.setPen(QColor("#888"))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Scan a folder to build the map.")
            return
        r = QRectF(self.rect()).adjusted(4, 4, -4, -4)
        self._rects = squarify(node, r.x(), r.y(), r.width(), r.height())
        for child, x, y, w, h in self._rects:
            if w < 1 or h < 1:
                continue
            col = _color_for(child, self.theme)
            if self._hover is child:
                col = col.lighter(125)
            p.fillRect(QRectF(x, y, w, h), col)
            p.setPen(QPen(QColor(0, 0, 0, 120), 1))
            p.drawRect(QRectF(x, y, w, h))
            self._draw_tile_label(p, child, x, y, w, h)


class TreeSizeView(QTreeWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setHeaderLabels(["Name", "Size", "Files", "Folders", "% of parent"])
        self.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.setAlternatingRowColors(True)

    def set_tree(self, root: DiskNode) -> None:
        self.clear()
        item = self._item(root, root.size)
        self.addTopLevelItem(item)
        item.setExpanded(True)

    def _item(self, node: DiskNode, parent_size: int) -> QTreeWidgetItem:
        pct = f"{node.percent_of(parent_size) * 100:.1f}%" if parent_size else ""
        bar = "█" * int(node.percent_of(parent_size) * 12)
        it = QTreeWidgetItem(
            [node.name, bytes_h(node.size), str(node.file_count), str(node.dir_count), f"{pct}  {bar}"]
        )
        for ch in node.children[:400]:
            it.addChild(self._item(ch, node.size))
        return it


class BlockMapWidget(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.used_ratio = 0.0
        self.theme: Theme | None = None

    def set_used(self, ratio: float) -> None:
        self.used_ratio = max(0.0, min(1.0, ratio))
        self.update()

    def paintEvent(self, _ev) -> None:
        p = QPainter(self)
        cols, rows = 64, 24
        w = self.width() / cols
        h = self.height() / rows
        n = cols * rows
        used = int(self.used_ratio * n)
        rng = random.Random(42)
        occupied = set(rng.sample(range(n), used)) if used else set()
        col = self.theme.disk if self.theme else QColor("#5dff9a")
        empty = QColor("#22262c")
        for i in range(n):
            x, y = (i % cols) * w, (i // cols) * h
            p.fillRect(QRectF(x + 1, y + 1, w - 2, h - 2), col if i in occupied else empty)


class BallsWidget(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.nodes: list[DiskNode] = []
        self._balls: list[list[float]] = []
        self.theme: Theme | None = None
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)

    def set_tree(self, root: DiskNode | None) -> None:
        self.nodes = [c for c in root.children if c.size > 0][:40] if root else []
        self._balls = []
        if self.nodes:
            self._timer.start()
        else:
            self._timer.stop()
        self.update()

    def _tick(self) -> None:
        if not self.nodes:
            return
        w, h = max(1, self.width()), max(1, self.height())
        total = sum(n.size for n in self.nodes) or 1
        area = w * h * 0.55
        if not self._balls:
            rng = random.Random(1)
            for i, n in enumerate(self.nodes):
                r = max(8.0, math.sqrt(n.size / total * area / math.pi))
                self._balls.append(
                    [rng.uniform(r, w - r), rng.uniform(r, h - r), r, rng.uniform(-0.4, 0.4), rng.uniform(-0.4, 0.4), i]
                )
        for b in self._balls:
            b[0] += b[3]
            b[1] += b[4]
            if b[0] < b[2] or b[0] > w - b[2]:
                b[3] *= -1
                b[0] = max(b[2], min(w - b[2], b[0]))
            if b[1] < b[2] or b[1] > h - b[2]:
                b[4] *= -1
                b[1] = max(b[2], min(h - b[2], b[1]))
        for i in range(len(self._balls)):
            for j in range(i + 1, len(self._balls)):
                a, c = self._balls[i], self._balls[j]
                dx, dy = c[0] - a[0], c[1] - a[1]
                dist = math.hypot(dx, dy) or 0.001
                min_d = a[2] + c[2]
                if dist < min_d:
                    push = (min_d - dist) / 2
                    nx, ny = dx / dist, dy / dist
                    a[0] -= nx * push
                    a[1] -= ny * push
                    c[0] += nx * push
                    c[1] += ny * push
        self.update()

    def paintEvent(self, _ev) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), self.theme.panel if self.theme else QColor("#1a1d24"))
        if not self._balls:
            p.setPen(QColor("#888"))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Scan a folder to pack balls.")
            return
        for x, y, r, _vx, _vy, idx in self._balls:
            node = self.nodes[int(idx)]
            col = _color_for(node, self.theme)
            p.setBrush(QBrush(col))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QRectF(x - r, y - r, r * 2, r * 2))
            if r > 18:
                p.setPen(QColor("#101216"))
                p.drawText(QRectF(x - r, y - 8, r * 2, 16), Qt.AlignmentFlag.AlignCenter, node.name[:12])
