from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QFrame,
)

from hbomb.snapshot.history import HistoryBank
from hbomb.snapshot.types import Snapshot
from hbomb.ui.fmt import bytes_h, bps_h
from hbomb.ui.theme import Theme, VisualState, MONO_FONT
from hbomb.ui.widgets import VfdMeter, TimeSeriesWidget


class _Tile(QFrame):
    clicked = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self.setFrameShape(QFrame.Shape.NoFrame)

    def mousePressEvent(self, ev) -> None:
        self.clicked.emit()
        super().mousePressEvent(ev)


def _chart_tile(title: str, chart: TimeSeriesWidget, nav: str, parent: QWidget) -> _Tile:
    box = _Tile(parent)
    lay = QVBoxLayout(box)
    lay.setContentsMargins(8, 6, 8, 6)
    head = QHBoxLayout()
    lbl = QLabel(title)
    lbl.setObjectName("muted")
    head.addWidget(lbl)
    head.addStretch()
    val = QLabel("")
    val.setFont(QFont(MONO_FONT, 10))
    val.setObjectName("chartValue")
    head.addWidget(val)
    lay.addLayout(head)
    lay.addWidget(chart, 1)
    box.clicked.connect(lambda: parent.navigate.emit(nav))  # type: ignore[attr-defined]
    box._value_lbl = val  # type: ignore[attr-defined]
    return box


class HomePage(QWidget):
    navigate = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.theme: Theme | None = None
        self.visual = VisualState()
        self._history: HistoryBank | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 8, 12, 8)
        root.setSpacing(10)

        charts_row = QHBoxLayout()
        charts_row.setSpacing(10)

        self.cpu_chart = TimeSeriesWidget()
        self.cpu_chart.fixed_max = 100.0
        self.cpu_chart.setMinimumHeight(150)
        self.cpu_tile = _chart_tile("CPU", self.cpu_chart, "performance", self)

        self.gpu_chart = TimeSeriesWidget()
        self.gpu_chart.fixed_max = 100.0
        self.gpu_chart.setMinimumHeight(150)
        self.gpu_tile = _chart_tile("GPU", self.gpu_chart, "gpu", self)

        charts_row.addWidget(self.cpu_tile, 1)
        charts_row.addWidget(self.gpu_tile, 1)
        root.addLayout(charts_row, 2)

        heat_mem = QHBoxLayout()
        heat_mem.setSpacing(10)

        self.temp_chart = TimeSeriesWidget()
        self.temp_chart.fixed_max = 110.0
        self.temp_chart.setMinimumHeight(110)
        self.temp_tile = _chart_tile("Temperature", self.temp_chart, "thermals", self)

        mem_tile = _Tile()
        mem_outer = QHBoxLayout(mem_tile)
        mem_outer.setContentsMargins(8, 6, 8, 6)
        self.m_mem = VfdMeter("Memory", QColor("#b07cff"), vertical=True)
        self.m_mem.setMaximumWidth(56)
        mem_outer.addWidget(self.m_mem)
        mem_l = QVBoxLayout()
        mem_head = QHBoxLayout()
        self.mem_legend = QLabel("Physical memory in use")
        self.mem_legend.setStyleSheet("color: #b07cff;")
        self.mem_avail = QLabel("Available")
        self.mem_avail.setObjectName("muted")
        self.mem_nums = QLabel("")
        self.mem_nums.setFont(QFont(MONO_FONT, 10))
        mem_head.addWidget(self.mem_legend)
        mem_head.addSpacing(16)
        mem_head.addWidget(self.mem_avail)
        mem_head.addStretch()
        mem_head.addWidget(self.mem_nums)
        mem_l.addLayout(mem_head)
        self.mem_chart = TimeSeriesWidget()
        self.mem_chart.setMinimumHeight(56)
        mem_l.addWidget(self.mem_chart)
        self.mem_foot = QLabel("")
        self.mem_foot.setObjectName("muted")
        mem_l.addWidget(self.mem_foot)
        mem_outer.addLayout(mem_l, 1)
        mem_tile.clicked.connect(lambda: self.navigate.emit("memory"))

        heat_mem.addWidget(self.temp_tile, 1)
        heat_mem.addWidget(mem_tile, 1)
        root.addLayout(heat_mem, 2)

        bottom = QHBoxLayout()
        bottom.setSpacing(8)

        self.disk_chart = TimeSeriesWidget()
        self.disk_chart.compact = True
        self.disk_chart.fixed_max = 100.0
        self.disk_chart.setMinimumHeight(52)
        self.disk_tile = _chart_tile("Disk", self.disk_chart, "disk", self)
        self.disk_tile.setMinimumHeight(72)

        self.net_chart = TimeSeriesWidget()
        self.net_chart.compact = True
        self.net_chart.setMinimumHeight(52)
        self.net_tile = _chart_tile("Network", self.net_chart, "network", self)
        self.net_tile.setMinimumHeight(72)

        bottom.addWidget(self.disk_tile, 1)
        bottom.addWidget(self.net_tile, 1)
        root.addLayout(bottom)

        for w in self.findChildren(TimeSeriesWidget):
            w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.m_mem.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

    def bind_history(self, history: HistoryBank) -> None:
        self._history = history

    def apply_theme(self, theme: Theme, visual: VisualState) -> None:
        self.theme = theme
        self.visual = visual
        self.m_mem.color = theme.mem
        self.m_mem.theme = theme
        self.m_mem.visual = visual
        charts = (
            self.cpu_chart,
            self.gpu_chart,
            self.temp_chart,
            self.mem_chart,
            self.disk_chart,
            self.net_chart,
        )
        for chart in charts:
            chart.theme = theme
            chart.visual = visual
        self.mem_chart.grid_tint = theme.mem
        self.disk_chart.grid_tint = theme.disk
        self.temp_chart.grid_tint = theme.temp
        self.mem_legend.setStyleSheet(f"color: {theme.mem.name()}; background: transparent;")

    def tick(self, dt: float = 1 / 60) -> None:
        self.m_mem.tick(dt)

    def update_snapshot(self, snap: Snapshot, include_self: bool) -> None:
        cpu = snap.cpu.overall.total
        hist = self._history
        t = self.theme
        if hist:
            self.cpu_chart.set_series(
                [("Utilization", hist.get("cpu_util_pct"), t.cpu if t else QColor("#3dff8a"), 100.0, "left", True)]
            )
            self.gpu_chart.set_series(
                [
                    ("Utilization", hist.get("gpu_util_pct"), t.gpu if t else QColor("#4da3ff"), 100.0, "left", True),
                    ("VRAM", hist.get("gpu_vram_pct"), t.danger if t else QColor("#ff5a5a"), 100.0, "left", False),
                ]
            )
            self.temp_chart.set_series(
                [("Temperature", hist.get("temp_c"), t.temp if t else QColor("#ffb347"), 110.0, "left", True)]
            )
            self.mem_chart.set_series(
                [("Memory", hist.get("mem_used_pct"), t.mem if t else QColor("#b07cff"), 100.0, "left", True)]
            )
            self.disk_chart.set_series(
                [("Busy", hist.get("disk_busy_pct"), t.disk if t else QColor("#5dff9a"), 100.0, "left", True)]
            )
            net_cap = max(snap.net.link_speed_mbps * 125_000, 1.0)
            self.net_chart.fixed_max = net_cap
            self.net_chart.set_series(
                [
                    ("Receive", hist.get("net_r_bps"), t.net if t else QColor("#5ad0ff"), net_cap, "left", True),
                    ("Send", hist.get("net_w_bps"), t.accent if t else QColor("#d4a84b"), net_cap, "left", False),
                ]
            )
        self.cpu_tile._value_lbl.setText(f"{cpu * 100:.1f}%")  # type: ignore[attr-defined]
        vram_pct = (snap.gpu.vram_used / snap.gpu.vram_total * 100.0) if snap.gpu.vram_total else 0.0
        self.gpu_tile._value_lbl.setText(  # type: ignore[attr-defined]
            f"{snap.gpu.util * 100:.1f}%  ·  VRAM {vram_pct:.0f}%"
        )
        self.temp_tile._value_lbl.setText(f"{snap.thermals.hotspot_c:.0f} °C")  # type: ignore[attr-defined]
        self.disk_tile._value_lbl.setText(f"{snap.disk.busy * 100:.1f}%")  # type: ignore[attr-defined]
        self.net_tile._value_lbl.setText(  # type: ignore[attr-defined]
            f"R: {bps_h(snap.net.rx_bps)}  W: {bps_h(snap.net.tx_bps)}"
        )
        occ = snap.memory.occupied_bytes
        tot = snap.memory.total_bytes
        self.mem_nums.setText(f"{bytes_h(occ)} / {bytes_h(tot)}")
        self.m_mem.set_value(snap.memory.used_ratio, f"{snap.memory.used_ratio * 100:.0f}%")
        self.mem_avail.setText(f"Available {bytes_h(snap.memory.available_bytes)}")
        self.mem_foot.setText(
            f"Cached {bytes_h(snap.memory.cached_bytes)}      Swap {bytes_h(snap.memory.swap_used_bytes)}"
        )
