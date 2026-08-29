from __future__ import annotations

import math
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPainter, QPen, QColor, QLinearGradient, QPainterPath, QFont, QBrush
from PySide6.QtWidgets import QWidget, QSizePolicy

from hbomb.snapshot.history import LogHistory, ease, log_time_fraction, age_from_fraction, log_grid_ages, Sample
from hbomb.ui.theme import Theme, VisualState, apply_saturation, UI_FONT, MONO_FONT


def _tick(shown: float, target: float, dt: float = 1 / 60, tau: float = 0.14) -> float:
    return ease(shown, target, dt, tau)


def _seg_heat(t: float, ramp: str, base: QColor) -> QColor:
    t = max(0.0, min(1.0, t))
    if ramp == "cpu":
        if t < 0.5:
            u = t * 2
            return QColor(int(40 + 180 * u), int(220 - 20 * u), int(80 - 40 * u))
        u = (t - 0.5) * 2
        return QColor(int(220 + 35 * u), int(200 - 160 * u), int(40 - 20 * u))
    if ramp == "temp":
        return QColor(int(255), int(200 - 140 * t), int(40 - 20 * t))
    if ramp == "clock":
        return QColor(int(255), int(140 - 40 * t), int(50 - 20 * t))
    if ramp == "gpu":
        return QColor(int(40 + 40 * t), int(140 + 80 * t), 255)
    return base


class VfdMeter(QWidget):
    """Segmented bar with ballistics. Paints at display cadence."""

    def __init__(self, label: str, color: QColor, vertical: bool = True, parent=None) -> None:
        super().__init__(parent)
        self.label = label
        self.color = color
        self.vertical = vertical
        self.ramp = ""  # cpu / temp / clock / gpu / ""
        self._target = 0.0
        self._shown = 0.0
        self._caption = ""
        self.theme: Theme | None = None
        self.visual = VisualState()
        if vertical:
            self.setMinimumSize(36, 80)
        else:
            self.setMinimumHeight(22)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_value(self, ratio: float, caption: str = "") -> None:
        self._target = max(0.0, min(1.0, ratio))
        self._caption = caption
        self.update()

    def tick(self, dt: float = 1 / 60) -> None:
        nxt = _tick(self._shown, self._target, dt, 0.14)
        if abs(nxt - self._shown) > 5e-4:
            self._shown = nxt
            self.update()

    def paintEvent(self, _ev) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        theme = self.theme
        text = theme.text if theme else QColor("#eee")
        muted = theme.muted if theme else QColor("#888")
        col = apply_saturation(self.color, self.visual.saturation, self.visual.color_mode == "mono")
        r = self.rect().adjusted(4, 4, -4, -4)
        p.setPen(QPen(muted))
        p.setFont(QFont(UI_FONT, 8))
        p.drawText(r, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, self.label)
        body = r.adjusted(2, 16, -2, -16)
        segs = 16 if self.vertical else 24
        filled = int(round(self._shown * segs))
        if self.vertical:
            h = body.height() / segs
            for i in range(segs):
                y = body.bottom() - (i + 1) * h
                sr = QRectF(body.x(), y + 1, body.width(), h - 2)
                c = _seg_heat(i / max(1, segs - 1), self.ramp, col)
                if i < filled:
                    p.fillRect(sr, c)
                else:
                    dim = QColor(c)
                    dim.setAlpha(28)
                    p.fillRect(sr, dim)
        else:
            w = body.width() / segs
            for i in range(segs):
                sr = QRectF(body.x() + i * w + 1, body.y(), w - 2, body.height())
                c = _seg_heat(i / max(1, segs - 1), self.ramp, col)
                if i < filled:
                    p.fillRect(sr, c)
                else:
                    dim = QColor(c)
                    dim.setAlpha(28)
                    p.fillRect(sr, dim)
        p.setFont(QFont(MONO_FONT, 8))
        p.setPen(QPen(text))
        p.drawText(r, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom, self._caption)


class UtilizationBar(QWidget):
    """Horizontal segmented utilization bar with green→yellow→red gradient."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._target = 0.0
        self._shown = 0.0
        self.theme: Theme | None = None
        self.visual = VisualState()
        self.setMinimumHeight(28)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_value(self, ratio: float) -> None:
        self._target = max(0.0, min(1.0, ratio))
        self.update()

    def tick(self, dt: float = 1 / 60) -> None:
        nxt = _tick(self._shown, self._target, dt, 0.14)
        if abs(nxt - self._shown) > 5e-4:
            self._shown = nxt
            self.update()

    def paintEvent(self, _ev) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        theme = self.theme
        accent = theme.gpu if theme else QColor("#4da3ff")
        r = QRectF(self.rect()).adjusted(0, 4, -56, -4)
        segs = 60
        filled = int(round(self._shown * segs))
        w = r.width() / segs
        for i in range(segs):
            t = i / max(1, segs - 1)
            col = _seg_heat(t, "cpu", QColor("#3dff8a"))
            sr = QRectF(r.x() + i * w + 0.5, r.y(), max(1.0, w - 1), r.height())
            if i < filled:
                p.fillRect(sr, col)
            else:
                dim = QColor(col)
                dim.setAlpha(42)
                p.fillRect(sr, dim)
        p.setFont(QFont(MONO_FONT, 11, QFont.Weight.DemiBold))
        p.setPen(QPen(accent))
        p.drawText(
            QRectF(r.right() + 6, self.rect().top(), 50, self.rect().height()),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
            f"{self._shown * 100:.1f}%",
        )


class SparklineWidget(QWidget):
    """Compact log-time sparkline for the performance rail."""

    def __init__(self, color: QColor, parent=None) -> None:
        super().__init__(parent)
        self.color = color
        self._hist: LogHistory | None = None
        self.theme: Theme | None = None
        self.visual = VisualState()
        self.setFixedSize(96, 52)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def set_history(self, hist: LogHistory | None) -> None:
        self._hist = hist
        self.update()

    def paintEvent(self, _ev) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect())
        pts = self._hist.series() if self._hist else []
        if len(pts) < 2:
            return
        t_min, t_max = pts[0].t, pts[-1].t
        if t_max <= t_min:
            t_max = t_min + 1.0
        mx = max(max(s.value for s in pts), 1.0)
        col = apply_saturation(self.color, self.visual.saturation, self.visual.color_mode == "mono")
        path = QPainterPath()
        fill = QPainterPath()
        for i, s in enumerate(pts):
            frac = log_time_fraction(s.t, t_min, t_max)
            x = r.left() + frac * r.width()
            y = r.bottom() - (s.value / mx) * r.height() * 0.88
            if i == 0:
                path.moveTo(x, y)
                fill.moveTo(x, r.bottom())
                fill.lineTo(x, y)
            else:
                path.lineTo(x, y)
                fill.lineTo(x, y)
        fill.lineTo(r.right(), r.bottom())
        fill.closeSubpath()
        fc = QColor(col)
        fc.setAlpha(50)
        p.fillPath(fill, fc)
        if self.visual.bloom:
            glow = QColor(col)
            glow.setAlpha(50)
            p.setPen(QPen(glow, 4))
            p.drawPath(path)
        p.setPen(QPen(col, 1.5))
        p.drawPath(path)


class TimeSeriesWidget(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.series: list[tuple] = []
        self.theme: Theme | None = None
        self.visual = VisualState()
        self.compact = False
        self.overview = False
        self.fixed_max: float | None = None
        self.corner_label = ""
        self.chart_title = ""
        self.headline = ""
        self.footer_left = ""
        self.footer_sub = ""
        self.footer_right = ""
        self.grid_tint: QColor | None = None
        self._hover_x: float | None = None
        self._decay: list[tuple[float, float]] = []
        self.setMinimumHeight(80)
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_series(self, series: list[tuple]) -> None:
        self.series = series
        self.update()

    def mouseMoveEvent(self, ev) -> None:
        if self.compact:
            return
        self._hover_x = ev.position().x()
        self.update()

    def leaveEvent(self, _ev) -> None:
        self._hover_x = None
        self.update()

    def _unpack(self, item: tuple) -> tuple[str, LogHistory, QColor, float | None, str, bool]:
        name, hist, color = item[0], item[1], item[2]
        y_max = item[3] if len(item) > 3 else None
        axis = item[4] if len(item) > 4 else "left"
        fill = item[5] if len(item) > 5 else True
        return name, hist, color, y_max, axis, fill

    def paintEvent(self, _ev) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        theme = self.theme or Theme(
            "x", QColor("#111"), QColor("#222"), QColor("#eee"), QColor("#888"),
            QColor("#48f"), QColor("#3f8"), QColor("#a8f"), QColor("#4af"),
            QColor("#fa3"), QColor("#5f8"), QColor("#5df"), QColor("#f55"), QColor("#333"),
        )
        if self.overview:
            self._paint_overview(p, theme)
            return
        r = QRectF(self.rect()).adjusted(2, 2, -2, -2)
        p.fillRect(r, theme.panel if not self.compact else theme.bg)
        t_min, t_max = self._time_bounds()
        span = max(0.0, t_max - t_min)
        grid = apply_saturation(self.grid_tint or theme.grid, self.visual.saturation, False)
        if self.compact:
            g = QColor(theme.gpu)
            g.setAlpha(45)
            p.setPen(QPen(g, 1))
            for i in range(1, 4):
                y = r.top() + r.height() * i / 4
                p.drawLine(QPointF(r.left(), y), QPointF(r.right(), y))
            for i in range(1, 6):
                x = r.left() + r.width() * i / 6
                p.drawLine(QPointF(x, r.top()), QPointF(x, r.bottom()))
        else:
            p.setPen(QPen(grid, 1))
            for i in range(1, 4):
                y = r.top() + r.height() * i / 4
                p.drawLine(QPointF(r.left(), y), QPointF(r.right(), y))
            if self.grid_tint is not None:
                for i in range(1, 8):
                    x = r.left() + r.width() * i / 8
                    p.drawLine(QPointF(x, r.top()), QPointF(x, r.bottom()))
        if span > 0:
            p.setPen(QPen(grid, 1))
            for age in log_grid_ages(span):
                t_mark = t_max - age
                frac = log_time_fraction(t_mark, t_min, t_max)
                x = r.left() + frac * r.width()
                p.drawLine(QPointF(x, r.top()), QPointF(x, r.bottom()))
        if self.corner_label:
            p.setFont(QFont(UI_FONT, 8))
            p.setPen(QPen(theme.muted))
            p.drawText(QPointF(r.left() + 4, r.top() + 12), self.corner_label)
        legend_y = r.top() + 12
        for i, item in enumerate(self.series):
            name, hist, color, y_max, _axis, fill = self._unpack(item)
            pts = hist.series()
            if len(pts) < 2:
                continue
            col = apply_saturation(color, self.visual.saturation, self.visual.color_mode == "mono")
            do_fill = fill if not self.compact else i == 0
            if theme.phosphor:
                self._paint_phosphor(p, r, pts, t_min, t_max, col, y_max)
            else:
                self._paint_line(p, r, pts, t_min, t_max, col, bloom=self.visual.bloom, y_max=y_max, fill=do_fill)
            if not self.compact:
                p.setPen(QPen(col))
                p.drawText(QPointF(r.left() + 8, legend_y), name)
                legend_y += 14
        if self.visual.sickbay:
            p.setPen(QPen(QColor("#ffffff"), 1, Qt.PenStyle.DotLine))
            mid = r.center().y()
            p.drawLine(QPointF(r.left(), mid), QPointF(r.right(), mid))
        if self._hover_x is not None and span > 0 and not self.compact:
            p.setPen(QPen(theme.text, 1, Qt.PenStyle.DashLine))
            p.drawLine(QPointF(self._hover_x, r.top()), QPointF(self._hover_x, r.bottom()))
            frac = max(0.0, min(1.0, (self._hover_x - r.left()) / max(1.0, r.width())))
            target_t = t_max - age_from_fraction(frac, span)
            for item in self.series:
                name, hist, color, *_rest = self._unpack(item)
                pts = hist.series()
                if not pts:
                    continue
                nearest = min(pts, key=lambda s: abs(s.t - target_t))
                p.setPen(QPen(color))
                p.drawText(QPointF(self._hover_x + 4, r.bottom() - 8), f"{name}: {nearest.value:.1f}")

    def _paint_overview(self, p: QPainter, theme: Theme) -> None:
        full = QRectF(self.rect())
        p.fillRect(full, theme.panel)
        left_c = theme.cpu
        right_c = theme.temp
        p.setFont(QFont(UI_FONT, 11, QFont.Weight.DemiBold))
        p.setPen(QPen(theme.text))
        p.drawText(QRectF(28, 6, 220, 20), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.chart_title or "CPU Overview")
        # chip
        p.setPen(QPen(theme.muted, 1.2))
        p.drawRoundedRect(QRectF(8, 8, 14, 14), 2, 2)
        p.setFont(QFont(MONO_FONT, 14, QFont.Weight.DemiBold))
        p.setPen(QPen(left_c))
        p.drawText(QRectF(full.width() - 80, 4, 72, 24), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, self.headline)
        # legend
        x = 28
        for item in self.series:
            name, _h, color, *_r = self._unpack(item)
            p.setPen(QPen(color, 1.6))
            p.drawLine(QPointF(x, 38), QPointF(x + 14, 32))
            p.drawLine(QPointF(x + 14, 32), QPointF(x + 22, 40))
            p.setFont(QFont(UI_FONT, 8))
            p.drawText(QRectF(x + 26, 26, 90, 18), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, name)
            x += 118
        plot = QRectF(40, 52, full.width() - 80, full.height() - 92)
        grid = QColor(theme.cpu)
        grid.setAlpha(52)
        p.setPen(QPen(grid, 1))
        for i in range(11):
            y = plot.top() + plot.height() * i / 10
            p.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
        for i in range(13):
            x = plot.left() + plot.width() * i / 12
            p.drawLine(QPointF(x, plot.top()), QPointF(x, plot.bottom()))
        t_min, t_max = self._time_bounds()
        span = max(0.0, t_max - t_min)
        if span > 0:
            for age in log_grid_ages(span):
                frac = log_time_fraction(t_max - age, t_min, t_max)
                x = plot.left() + frac * plot.width()
                p.drawLine(QPointF(x, plot.top()), QPointF(x, plot.bottom()))
        p.setFont(QFont(MONO_FONT, 8))
        for frac, lab in ((1.0, "0%"), (0.5, "50%"), (0.0, "100%")):
            y = plot.top() + plot.height() * frac
            p.setPen(QPen(left_c))
            p.drawText(QRectF(2, y - 8, 36, 16), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, lab)
        for frac, lab in ((1.0, "0°"), (0.5, "55°"), (0.0, "110°")):
            y = plot.top() + plot.height() * frac
            p.setPen(QPen(right_c))
            p.drawText(QRectF(plot.right() + 4, y - 8, 36, 16), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, lab)
        for i, item in enumerate(self.series):
            name, hist, color, y_max, axis, fill = self._unpack(item)
            pts = hist.series()
            if len(pts) < 2:
                continue
            col = apply_saturation(color, self.visual.saturation, self.visual.color_mode == "mono")
            mx = 110.0 if axis == "right" else (y_max or 100.0)
            self._paint_line(p, plot, pts, t_min, t_max, col, bloom=self.visual.bloom, y_max=mx, fill=(axis != "right"))
        p.setFont(QFont(UI_FONT, 9))
        p.setPen(QPen(theme.muted))
        p.drawText(QRectF(12, full.height() - 36, 220, 16), Qt.AlignmentFlag.AlignLeft, self.footer_left)
        p.setFont(QFont(UI_FONT, 8))
        p.drawText(QRectF(12, full.height() - 20, 220, 14), Qt.AlignmentFlag.AlignLeft, self.footer_sub)
        p.setFont(QFont(UI_FONT, 9))
        p.drawText(QRectF(full.width() - 200, full.height() - 28, 188, 18), Qt.AlignmentFlag.AlignRight, self.footer_right)
        if self._hover_x is not None and span > 0:
            hx = max(plot.left(), min(plot.right(), self._hover_x))
            p.setPen(QPen(theme.text, 1, Qt.PenStyle.DashLine))
            p.drawLine(QPointF(hx, plot.top()), QPointF(hx, plot.bottom()))

    def _time_bounds(self) -> tuple[float, float]:
        t_min = float("inf")
        t_max = float("-inf")
        for item in self.series:
            _name, hist, _c, *_r = self._unpack(item)
            pts = hist.series()
            if not pts:
                continue
            t_min = min(t_min, pts[0].t)
            t_max = max(t_max, pts[-1].t)
        if t_min == float("inf"):
            return 0.0, 1.0
        if t_max <= t_min:
            t_max = t_min + 1.0
        return t_min, t_max

    def _x_for(self, r: QRectF, t: float, t_min: float, t_max: float) -> float:
        frac = log_time_fraction(t, t_min, t_max)
        return r.left() + frac * r.width()

    def _paint_line(
        self,
        p: QPainter,
        r: QRectF,
        pts: list[Sample],
        t_min: float,
        t_max: float,
        col: QColor,
        bloom: bool,
        y_max: float | None = None,
        fill: bool = True,
    ) -> None:
        mx = y_max if y_max is not None else (self.fixed_max if self.fixed_max is not None else max(max(s.value for s in pts), 1.0))
        mx = max(mx, 1e-6)
        path = QPainterPath()
        fill_path = QPainterPath()
        first_x = None
        for i, s in enumerate(pts):
            x = self._x_for(r, s.t, t_min, t_max)
            y = r.bottom() - (s.value / mx) * r.height() * 0.92
            y = max(r.top(), min(r.bottom(), y))
            if i == 0:
                path.moveTo(x, y)
                if fill:
                    fill_path.moveTo(x, r.bottom())
                    fill_path.lineTo(x, y)
                first_x = x
            else:
                path.lineTo(x, y)
                if fill:
                    fill_path.lineTo(x, y)
        if first_x is not None and fill:
            fill_path.lineTo(self._x_for(r, pts[-1].t, t_min, t_max), r.bottom())
            fill_path.closeSubpath()
            fill_col = QColor(col)
            fill_col.setAlpha(72 if self.compact else 45)
            p.fillPath(fill_path, fill_col)
        width = 1.4 if self.compact else 2.0
        if bloom and not self.compact:
            glow = QColor(col)
            glow.setAlpha(60)
            p.setPen(QPen(glow, 6))
            p.drawPath(path)
        p.setPen(QPen(col, width))
        p.drawPath(path)

    def _paint_phosphor(
        self,
        p: QPainter,
        r: QRectF,
        pts: list[Sample],
        t_min: float,
        t_max: float,
        col: QColor,
        y_max: float | None = None,
    ) -> None:
        mx = y_max if y_max is not None else (self.fixed_max if self.fixed_max is not None else max(max(s.value for s in pts), 1.0))
        n = len(pts)
        for i in range(1, n):
            age = (n - 1 - i) / max(1, n)
            a = int(255 * math.exp(-age * 4))
            c = QColor(col)
            c.setAlpha(max(30, a))
            x0 = self._x_for(r, pts[i - 1].t, t_min, t_max)
            y0 = r.bottom() - (pts[i - 1].value / mx) * r.height() * 0.92
            x = self._x_for(r, pts[i].t, t_min, t_max)
            y = r.bottom() - (pts[i].value / mx) * r.height() * 0.92
            p.setPen(QPen(c, 2))
            p.drawLine(QPointF(x0, y0), QPointF(x, y))


class AnalogGauge(QWidget):
    def __init__(self, title: str, unit: str, max_value: float, parent=None) -> None:
        super().__init__(parent)
        self.title = title
        self.unit = unit
        self.max_value = max_value
        self._target = 0.0
        self._shown = 0.0
        self.theme: Theme | None = None
        self.setMinimumSize(180, 160)

    def set_value(self, v: float) -> None:
        self._target = v
        self.update()

    def tick(self, dt: float = 1 / 60) -> None:
        nxt = _tick(self._shown, self._target, dt, 0.18)
        if abs(nxt - self._shown) > 1e-3:
            self._shown = nxt
            self.update()

    def paintEvent(self, _ev) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        theme = self.theme
        text = theme.text if theme else QColor("white")
        accent = theme.accent if theme else QColor("#3d8bfd")
        danger = theme.danger if theme else QColor("#ff3a3a")
        r = QRectF(self.rect()).adjusted(12, 20, -12, -28)
        p.setPen(QPen(text, 3))
        p.drawArc(r, 30 * 16, 120 * 16)
        span = 120
        frac = 0 if self.max_value <= 0 else min(1.0, self._shown / self.max_value)
        angle = 30 + span * (1 - frac)
        cx, cy = r.center().x(), r.center().y() + r.height() * 0.15
        rad = math.radians(180 - angle)
        length = min(r.width(), r.height()) * 0.42
        p.setPen(QPen(danger, 3))
        p.drawLine(QPointF(cx, cy), QPointF(cx + math.cos(rad) * length, cy - math.sin(rad) * length))
        p.setPen(QPen(accent))
        font = QFont(MONO_FONT, 16)
        p.setFont(font)
        p.drawText(self.rect().adjusted(0, 40, 0, 0), Qt.AlignmentFlag.AlignHCenter, f"{self._shown:.1f}")
        p.setFont(QFont(UI_FONT, 9))
        p.setPen(QPen(text))
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, self.title)
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom, self.unit)


_SEG = {
    "0": "abcdef",
    "1": "bc",
    "2": "abged",
    "3": "abcdg",
    "4": "fgbc",
    "5": "afgcd",
    "6": "afedcg",
    "7": "abc",
    "8": "abcdefg",
    "9": "abcdfg",
    "-": "g",
    " ": "",
}


def _draw_led_digit(p: QPainter, box: QRectF, ch: str, on: QColor) -> None:
    if ch == ".":
        p.setBrush(on)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(box.right() - 2, box.bottom() - 2), 2.2, 2.2)
        return
    segs = _SEG.get(ch, "")
    x, y, w, h = box.x(), box.y(), box.width(), box.height()
    t = max(2.0, w * 0.16)
    thick = t
    parts = {
        "a": QRectF(x + t, y, w - 2 * t, thick),
        "b": QRectF(x + w - thick, y + t * 0.6, thick, h * 0.42),
        "c": QRectF(x + w - thick, y + h * 0.52, thick, h * 0.42),
        "d": QRectF(x + t, y + h - thick, w - 2 * t, thick),
        "e": QRectF(x, y + h * 0.52, thick, h * 0.42),
        "f": QRectF(x, y + t * 0.6, thick, h * 0.42),
        "g": QRectF(x + t, y + h * 0.46, w - 2 * t, thick),
    }
    off = QColor(on)
    off.setAlpha(28)
    for key, rect in parts.items():
        p.fillRect(rect, on if key in segs else off)


def _draw_led_text(p: QPainter, rect: QRectF, text: str, color: QColor) -> None:
    chars = list(text)
    n = max(len(chars), 1)
    slot = rect.width() / n
    for i, ch in enumerate(chars):
        box = QRectF(rect.x() + i * slot + 2, rect.y(), slot - 4, rect.height())
        _draw_led_digit(p, box, ch, color)


class CarbonBenchmarkGauge(QWidget):
    """Analog benchmark gauge (carbon face, red needle, digital readout)."""

    def __init__(self, title: str, unit: str, max_value: float, parent=None) -> None:
        super().__init__(parent)
        self.title = title
        self.unit = unit
        self.max_value = max_value
        self._target = 0.0
        self._shown = 0.0
        self.setMinimumSize(280, 300)

    def set_value(self, v: float) -> None:
        self._target = v
        self.update()

    def set_instant(self, v: float) -> None:
        self._target = v
        self._shown = v
        self.update()

    def tick(self, dt: float = 1 / 60) -> None:
        nxt = _tick(self._shown, self._target, dt, 0.22)
        if abs(nxt - self._shown) > 1e-3:
            self._shown = nxt
            self.update()

    def _carbon(self, p: QPainter, rect: QRectF) -> None:
        path = QPainterPath()
        path.addEllipse(rect)
        p.save()
        p.setClipPath(path)
        p.fillPath(path, QColor("#16351c"))
        p.setPen(QPen(QColor(0, 0, 0, 80), 1))
        step = 5
        left, top, right, bottom = int(rect.left()), int(rect.top()), int(rect.right()), int(rect.bottom())
        for i in range(left - 40, right + 40, step):
            p.drawLine(i, top, i + int(rect.height() * 0.55), bottom)
        p.setPen(QPen(QColor(255, 255, 255, 18), 1))
        for i in range(left - 40, right + 40, step):
            p.drawLine(i + 2, top, i + 2 + int(rect.height() * 0.55), bottom)
        p.restore()

    def paintEvent(self, _ev) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h * 0.52
        radius = min(w, h) * 0.42
        face = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)
        # outer chrome
        outer = face.adjusted(-8, -4, 8, 8)
        chrome = QLinearGradient(outer.topLeft(), outer.bottomRight())
        chrome.setColorAt(0.0, QColor("#f4f6f8"))
        chrome.setColorAt(0.35, QColor("#8a929c"))
        chrome.setColorAt(0.55, QColor("#d8dde4"))
        chrome.setColorAt(1.0, QColor("#6e757e"))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(chrome))
        p.drawEllipse(outer)
        inner_ring = QColor("#0a0c0e")
        p.setBrush(inner_ring)
        p.drawEllipse(face.adjusted(-2, -2, 2, 2))
        self._carbon(p, face.adjusted(6, 6, -6, -6))
        # ticks
        ticks = 8 if self.max_value <= 10 else 4
        p.setPen(QPen(QColor("#f0f0f0"), 2))
        p.setFont(QFont(UI_FONT, 8))
        inner_r = radius - 10
        for i in range(ticks + 1):
            t = i / ticks
            ang = math.radians(225 - t * 270)
            x0 = cx + math.cos(ang) * (inner_r - 16)
            y0 = cy - math.sin(ang) * (inner_r - 16)
            x1 = cx + math.cos(ang) * (inner_r - 4)
            y1 = cy - math.sin(ang) * (inner_r - 4)
            p.drawLine(QPointF(x0, y0), QPointF(x1, y1))
            val = self.max_value * t
            label = f"{val:.0f}" if self.max_value > 10 else f"{val:.0f}" if val == int(val) else f"{val:.0f}"
            if self.max_value <= 10:
                label = f"{val:.0f}"
            lx = cx + math.cos(ang) * (inner_r - 30)
            ly = cy - math.sin(ang) * (inner_r - 30)
            p.drawText(QRectF(lx - 16, ly - 8, 32, 16), Qt.AlignmentFlag.AlignCenter, label)
        # title inside face
        p.setPen(QColor("#e8eaed"))
        p.setFont(QFont(UI_FONT, 10, QFont.Weight.DemiBold))
        p.drawText(QRectF(0, cy - radius * 0.42, w, 20), Qt.AlignmentFlag.AlignHCenter, self.title)
        # needle
        frac = 0.0 if self.max_value <= 0 else min(1.0, self._shown / self.max_value)
        ang = math.radians(225 - frac * 270)
        nx = cx + math.cos(ang) * (inner_r - 28)
        ny = cy - math.sin(ang) * (inner_r - 28)
        tx = cx - math.cos(ang) * 18
        ty = cy + math.sin(ang) * 18
        needle = QPainterPath()
        perp = ang + math.pi / 2
        needle.moveTo(nx, ny)
        needle.lineTo(cx + math.cos(perp) * 3.5, cy - math.sin(perp) * 3.5)
        needle.lineTo(tx, ty)
        needle.lineTo(cx - math.cos(perp) * 3.5, cy + math.sin(perp) * 3.5)
        needle.closeSubpath()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#ff2a2a"))
        p.drawPath(needle)
        # silver hub
        hub = QLinearGradient(cx - 10, cy - 10, cx + 10, cy + 10)
        hub.setColorAt(0, QColor("#f2f4f6"))
        hub.setColorAt(1, QColor("#7a828c"))
        p.setBrush(QBrush(hub))
        p.drawEllipse(QPointF(cx, cy), 9, 9)
        p.setBrush(QColor("#1a1d22"))
        p.drawEllipse(QPointF(cx, cy), 3.5, 3.5)
        # digital readout
        if self.max_value <= 10 and self._shown < 0.05:
            digits = "0"
        elif self.max_value <= 10:
            digits = f"{self._shown:.1f}"
        else:
            digits = f"{self._shown:.0f}"
        led_rect = QRectF(cx - 60, cy + inner_r * 0.18, 120, 30)
        led_col = QColor("#4fc3ff")
        _draw_led_text(p, led_rect, digits, led_col)
        p.setFont(QFont(UI_FONT, 10, QFont.Weight.DemiBold))
        p.setPen(QColor("#5ad0ff"))
        p.drawText(QRectF(0, cy + inner_r * 0.18 + 32, w, 18), Qt.AlignmentFlag.AlignHCenter, self.unit)


class BrandLogo(QWidget):
    """Sidebar brand mark with pulse line."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedHeight(56)
        self.setMinimumWidth(120)
        self._accent = QColor("#d4a84b")
        self._glow = QColor("#2a231a")

    def set_palette(self, accent: QColor, panel: QColor) -> None:
        self._accent = accent
        self._glow = panel
        self.update()

    def paintEvent(self, _ev) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(8, 4, -8, -4)
        glow = QColor(self._glow)
        glow.setAlpha(200)
        p.setPen(QPen(self._accent, 1.2))
        p.setBrush(glow)
        p.drawRoundedRect(r, 8, 8)
        mid = r.center().y()
        path = QPainterPath()
        path.moveTo(r.left() + 10, mid)
        path.lineTo(r.left() + 24, mid - 7)
        path.lineTo(r.left() + 36, mid + 5)
        path.lineTo(r.left() + 48, mid - 3)
        path.lineTo(r.left() + 60, mid + 2)
        p.setPen(QPen(self._accent, 2))
        p.drawPath(path)
        p.setFont(QFont(UI_FONT, 12, QFont.Weight.Bold))
        p.setPen(self._accent)
        p.drawText(QRectF(r.left() + 66, r.top(), r.width() - 72, r.height()), Qt.AlignmentFlag.AlignVCenter, "H-Bomb")


class StatusLed(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._color = QColor("#3dff8a")
        self.setFixedSize(12, 12)

    def set_color(self, c: QColor) -> None:
        self._color = c
        self.update()

    def paintEvent(self, _ev) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self._color)
        p.drawEllipse(1, 1, 10, 10)


class BlinkenDisk(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._r = 0.0
        self._w = 0.0
        self._sr = 0.0
        self._sw = 0.0
        self.setFixedSize(16, 16)

    def set_activity(self, read_ratio: float, write_ratio: float) -> None:
        self._r = read_ratio
        self._w = write_ratio
        self.update()

    def tick(self, dt: float = 1 / 60) -> None:
        self._sr = _tick(self._sr, self._r, dt, 0.08)
        self._sw = _tick(self._sw, self._w, dt, 0.08)
        self.update()

    def paintEvent(self, _ev) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        val = min(1.0, max(self._sr, self._sw) * 8)
        c = QColor("#ff3a3a")
        c.setAlpha(int(50 + 205 * val))
        p.setBrush(c)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(2, 2, 12, 12)
