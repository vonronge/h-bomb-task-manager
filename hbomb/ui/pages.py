from __future__ import annotations

import os
import time
import math
from collections import deque

from PySide6.QtCore import Qt, QThread, Signal, QObject, QSize, QRect
from PySide6.QtGui import QColor, QBrush, QFont, QFontMetrics, QPainter
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QLineEdit,
    QCheckBox,
    QTreeWidget,
    QTreeWidgetItem,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QSplitter,
    QListWidget,
    QListWidgetItem,
    QStackedWidget,
    QTextEdit,
    QFileDialog,
    QMessageBox,
    QSlider,
    QFormLayout,
    QGroupBox,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QScrollArea,
    QFrame,
    QSpinBox,
)

from hbomb.providers.linux.diskspace import walk, build_tree, DiskNode
from hbomb.providers.linux.extras import (
    list_system_units_readonly,
    list_user_units,
    list_autostart,
    toggle_autostart,
    list_sessions,
    list_connections,
    list_installed_apps,
    hardware_tree,
    list_mounts,
    journal_tail,
    sample_smart,
)
from hbomb.providers.linux.processes import descendants
from hbomb.snapshot.actions import end_tree
from hbomb.snapshot.flags import FeatureFlags
from hbomb.snapshot.history import HistoryBank, LogHistory
from hbomb.snapshot.types import Snapshot, ProcessRow
from hbomb.ui.diskviews import TreemapWidget, TreeSizeView
from hbomb.ui.fmt import bytes_h, bps_h, hz_h, pct_h, uptime_h
from hbomb.ui.icons import nav_icon
from hbomb.ui.theme import Theme, VisualState, CHROMES, MONO_FONT, UI_FONT, AMBIANCE_CHOICES, ambiance_index, ambiance_id
from hbomb.ui.widgets import TimeSeriesWidget, VfdMeter, CarbonBenchmarkGauge, SparklineWidget


class CpuPage(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._history: HistoryBank | None = None
        self.theme: Theme | None = None
        self.visual = VisualState()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 4, 8, 4)
        head = QVBoxLayout()
        title_row = QHBoxLayout()
        self.title = QLabel("Processor")
        self.title.setStyleSheet("font-size: 22px; font-weight: 600;")
        self.total_pct = QLabel("—")
        self.total_pct.setFont(QFont(MONO_FONT, 14, QFont.Weight.DemiBold))
        self.total_pct.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        title_row.addWidget(self.title)
        title_row.addStretch()
        title_row.addWidget(self.total_pct)
        head.addLayout(title_row)
        self.overview = TimeSeriesWidget()
        self.overview.fixed_max = 100.0
        self.overview.setMinimumHeight(72)
        head.addWidget(self.overview)
        self.sub = QLabel("0 logical processors     % Utilization by logical processor")
        self.sub.setObjectName("muted")
        head.addWidget(self.sub)
        lay.addLayout(head)
        self.grid = QGridLayout()
        self.grid.setSpacing(4)
        self._core_charts: list[TimeSeriesWidget] = []
        lay.addLayout(self.grid, 1)
        metrics = QHBoxLayout()
        self._metric: dict[str, QLabel] = {}
        for key, caption in (
            ("util", "Utilization"),
            ("speed", "Speed"),
            ("procs", "Processes"),
            ("threads", "Threads"),
        ):
            box = QVBoxLayout()
            cap = QLabel(caption)
            cap.setObjectName("muted")
            val = QLabel("—")
            val.setFont(QFont(MONO_FONT, 14, QFont.Weight.DemiBold))
            box.addWidget(cap)
            box.addWidget(val)
            metrics.addLayout(box)
            self._metric[key] = val
        lay.addLayout(metrics)
        spec = QHBoxLayout()
        self.spec_left = QLabel()
        self.spec_right = QLabel()
        self.spec_left.setObjectName("muted")
        self.spec_right.setObjectName("muted")
        self.spec_left.setWordWrap(True)
        self.spec_right.setWordWrap(True)
        self.spec_left.setTextFormat(Qt.TextFormat.RichText)
        self.spec_right.setTextFormat(Qt.TextFormat.RichText)
        spec.addWidget(self.spec_left, 1)
        spec.addWidget(self.spec_right, 1)
        lay.addLayout(spec)

    def bind_history(self, h: HistoryBank) -> None:
        self._history = h

    def apply_theme(self, theme: Theme, visual: VisualState) -> None:
        self.theme = theme
        self.visual = visual
        self.overview.theme = theme
        self.overview.visual = visual
        self.overview.grid_tint = theme.cpu
        for c in self._core_charts:
            c.theme = theme
            c.visual = visual

    def update_snapshot(self, snap: Snapshot) -> None:
        n = len(snap.cpu.cores) or 1
        cols = 6 if n >= 16 else max(1, int(math.ceil(math.sqrt(n))))
        self.sub.setText(
            f"{snap.cpu.logical_processors} logical processors     % Utilization by logical processor"
        )
        if len(self._core_charts) != n:
            while self.grid.count():
                item = self.grid.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            self._core_charts = []
            for i, core in enumerate(snap.cpu.cores):
                w = TimeSeriesWidget()
                w.compact = True
                w.fixed_max = 100.0
                w.corner_label = f"CPU {core.index}"
                w.setMinimumHeight(64)
                if self.theme:
                    w.theme = self.theme
                    w.visual = self.visual
                self._core_charts.append(w)
                self.grid.addWidget(w, i // cols, i % cols)
        hist = self._history
        t = self.theme
        pcol = t.cpu if t else QColor("#3dff8a")
        kcol = t.danger if t else QColor("#ff5a5a")
        if hist:
            self.overview.set_series(
                [("Total", hist.get("cpu_util_pct"), pcol, 100.0, "left", True)]
            )
            for i, core in enumerate(snap.cpu.cores):
                if i >= len(self._core_charts):
                    break
                series = [
                    ("Util", hist.get(f"cpu{core.index}_pct"), pcol, 100.0, "left", True),
                    ("Kernel", hist.get(f"cpu{core.index}_kernel_pct"), kcol, 100.0, "left", False),
                ]
                self._core_charts[i].corner_label = f"CPU {core.index}"
                self._core_charts[i].set_series(series)
        virt = snap.cpu.virtualization or "—"
        total_pct = snap.cpu.overall.total * 100.0
        self.total_pct.setText(f"{total_pct:.1f}%")
        self._metric["util"].setText(f"{total_pct:.1f}%")
        self._metric["speed"].setText(hz_h(snap.cpu.freq_ghz))
        self._metric["procs"].setText(str(snap.cpu.process_count))
        self._metric["threads"].setText(str(snap.cpu.thread_count))
        self.spec_left.setText(
            f"Up time  {uptime_h(snap.cpu.uptime_s)}<br>"
            f"Base speed  {hz_h(snap.cpu.base_ghz)}<br>"
            f"Physical cores  {snap.cpu.physical_cores}<br>"
            f"Virtualization  {virt}<br>"
            f"Frequency driver  {snap.cpu.freq_driver or '—'}"
        )
        self.spec_right.setText(
            f"Sockets  {snap.cpu.sockets}<br>"
            f"Logical processors  {snap.cpu.logical_processors}<br>"
            f"Virtual machine  No<br>"
            f"Governor  {snap.cpu.governor or '—'}"
        )


class MemoryPage(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._history: HistoryBank | None = None
        self.theme: Theme | None = None
        self.visual = VisualState()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.title = QLabel("Memory")
        self.title.setStyleSheet("font-size: 22px; font-weight: 600;")
        lay.addWidget(self.title)
        self.chart = TimeSeriesWidget()
        lay.addWidget(self.chart, 1)
        self.body = QLabel()
        self.body.setWordWrap(True)
        lay.addWidget(self.body)

    def bind_history(self, h: HistoryBank) -> None:
        self._history = h

    def apply_theme(self, theme: Theme, visual: VisualState) -> None:
        self.theme = theme
        self.visual = visual
        self.chart.theme = theme
        self.chart.visual = visual

    def update_snapshot(self, snap: Snapshot) -> None:
        m = snap.memory
        if self._history and self.theme:
            self.chart.set_series([("Occupied %", self._history.get("mem_used_pct"), self.theme.mem)])
        self.body.setText(
            f"Occupied {bytes_h(m.occupied_bytes)}   Expensive {bytes_h(m.expensive_bytes)}\n"
            f"Application {bytes_h(m.application_bytes)}   Wired {bytes_h(m.wired_bytes)}   "
            f"Compressed {bytes_h(m.compressed_bytes)}   Cached {bytes_h(m.cached_bytes)}\n"
            f"Committed {bytes_h(m.committed_bytes)}   Available {bytes_h(m.available_bytes)}   "
            f"Swap {bytes_h(m.swap_used_bytes)} / {bytes_h(m.swap_total_bytes)}\n"
            f"Pressure PSI some avg10={m.psi_avg10:.2f} avg60={m.psi_avg60:.2f} avg300={m.psi_avg300:.2f}\n"
            f"{bytes_h(m.occupied_bytes)} / {bytes_h(m.total_bytes)}"
        )


class PerformanceRailTile(QWidget):
    def __init__(self, title: str, accent: QColor, parent=None) -> None:
        super().__init__(parent)
        self.accent = accent
        self._selected = False
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 10, 6, 8)
        lay.setSpacing(6)
        text = QVBoxLayout()
        text.setSpacing(0)
        self.title_lbl = QLabel(title)
        self.title_lbl.setStyleSheet("font-weight: 600; font-size: 11px; background: transparent;")
        self.headline = QLabel()
        self.headline.setStyleSheet("font-size: 14px; background: transparent;")
        self.detail = QLabel()
        self.detail.setStyleSheet("font-size: 11px; color: #8b919a; background: transparent;")
        text.addWidget(self.title_lbl)
        text.addWidget(self.headline)
        text.addWidget(self.detail)
        lay.addLayout(text, 1)
        self.spark = SparklineWidget(accent)
        lay.addWidget(self.spark, 0, Qt.AlignmentFlag.AlignVCenter)

    def set_selected(self, on: bool) -> None:
        self._selected = on
        accent = self.accent.name()
        if on:
            c = self.accent
            self.setStyleSheet(
                f"PerformanceRailTile {{ background: rgba({c.red()}, {c.green()}, {c.blue()}, 0.18); "
                f"border-left: 4px solid {accent}; border-radius: 8px; }}"
            )
        else:
            self.setStyleSheet("PerformanceRailTile { background: transparent; border-left: 4px solid transparent; }")

    def set_data(self, headline: str, detail: str, hist: LogHistory | None) -> None:
        self.headline.setText(headline)
        self.detail.setText(detail)
        self.spark.set_history(hist)

    def apply_theme(self, theme: Theme, visual: VisualState) -> None:
        self.spark.theme = theme
        self.spark.visual = visual
        self.detail.setStyleSheet(f"font-size: 11px; color: {theme.muted.name()}; background: transparent;")
        self.set_selected(self._selected)


_PERF_TABS = (
    ("cpu", "Processor"),
    ("memory", "RAM"),
    ("energy", "Power Draw"),
    ("thermals", "Temperature"),
    ("disk", "Disk I/O"),
    ("network", "Network"),
    ("gpu", "Graphics"),
)

_BENCH_KINDS = (
    "Processor",
    "Graphics",
    "Storage",
    "Network",
    "Overall Score",
)


class PerformancePage(QWidget):
    """Task-Manager-style performance hub with internal resource rail."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._history: HistoryBank | None = None
        self.theme: Theme | None = None
        self.visual = VisualState()
        self._snap: Snapshot | None = None
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        split = QSplitter(Qt.Orientation.Horizontal)
        lay.addWidget(split)
        self.rail = QListWidget()
        self.rail.setObjectName("perfRail")
        rail_font = QFont(self.font().family(), 10, QFont.Weight.Medium)
        fm = QFontMetrics(rail_font)
        rail_w = max(fm.horizontalAdvance(label) for _k, label in _PERF_TABS) + 200
        self.rail.setFixedWidth(max(248, rail_w))
        self.rail.setSpacing(2)
        self.rail.setFrameShape(QListWidget.Shape.NoFrame)
        self._tiles: dict[str, PerformanceRailTile] = {}
        self.stack = QStackedWidget()
        self.cpu = CpuPage()
        self.memory = MemoryPage()
        self.energy = TelemetryPage("energy", title="Power Draw")
        self.thermals = TelemetryPage("thermals", title="Temperature")
        self.disk = TelemetryPage("storage", title="Disk I/O")
        self.network = TelemetryPage("network", title="Network")
        self.gpu = TelemetryPage("gpu", title="Graphics")
        self._detail_pages: dict[str, QWidget] = {
            "cpu": self.cpu,
            "memory": self.memory,
            "energy": self.energy,
            "thermals": self.thermals,
            "disk": self.disk,
            "network": self.network,
            "gpu": self.gpu,
        }
        for key, label in _PERF_TABS:
            item = QListWidgetItem()
            item.setSizeHint(QSize(max(240, fm.horizontalAdvance(label) + 180), 88))
            tile = PerformanceRailTile(label, QColor("#3dff8a"))
            self.rail.addItem(item)
            self.rail.setItemWidget(item, tile)
            self._tiles[key] = tile
            self.stack.addWidget(self._detail_pages[key])
        split.addWidget(self.rail)
        split.addWidget(self.stack)
        split.setStretchFactor(1, 1)
        self.rail.currentRowChanged.connect(self._on_rail)
        self.rail.setCurrentRow(0)
        self._on_rail(0)

    def bind_history(self, h: HistoryBank) -> None:
        self._history = h
        for p in self._detail_pages.values():
            if hasattr(p, "bind_history"):
                p.bind_history(h)

    def apply_theme(self, theme: Theme, visual: VisualState) -> None:
        self.theme = theme
        self.visual = visual
        colors = {
            "cpu": theme.gpu,
            "memory": theme.mem,
            "energy": theme.temp,
            "thermals": theme.temp,
            "disk": theme.disk,
            "network": theme.net,
            "gpu": theme.gpu,
        }
        for key, tile in self._tiles.items():
            tile.accent = colors.get(key, theme.accent)
            tile.spark.color = tile.accent
            tile.apply_theme(theme, visual)
        for p in self._detail_pages.values():
            if hasattr(p, "apply_theme"):
                p.apply_theme(theme, visual)

    def _on_rail(self, row: int) -> None:
        for i, (key, _label) in enumerate(_PERF_TABS):
            self._tiles[key].set_selected(i == row)
        self.stack.setCurrentIndex(row)
        if self._snap is not None:
            w = self.stack.currentWidget()
            if w is not None and hasattr(w, "update_snapshot"):
                w.update_snapshot(self._snap)

    def _rail_hist(self, key: str) -> LogHistory | None:
        if self._history is None:
            return None
        mapping = {
            "cpu": "cpu_util_pct",
            "memory": "mem_used_pct",
            "energy": "power_w",
            "thermals": "temp_c",
            "disk": "disk_busy_pct",
            "network": "net_r_bps",
            "gpu": "gpu_util_pct",
        }
        return self._history.get(mapping[key])

    def _update_rail(self, snap: Snapshot) -> None:
        h = self._history
        cpu = snap.cpu
        mem = snap.memory
        w = snap.energy.watts
        self._tiles["cpu"].set_data(
            f"{cpu.overall.total * 100:.1f}%",
            f"{cpu.logical_processors} logical processors",
            self._rail_hist("cpu"),
        )
        self._tiles["memory"].set_data(
            f"{bytes_h(mem.occupied_bytes)} / {bytes_h(mem.total_bytes)}",
            f"{mem.used_ratio * 100:.1f}%",
            self._rail_hist("memory"),
        )
        self._tiles["energy"].set_data(
            "Whole machine",
            "Power unavailable" if w is None else f"{w:.1f} W",
            self._rail_hist("energy"),
        )
        self._tiles["thermals"].set_data(
            "Whole machine",
            f"{snap.thermals.hotspot_c:.0f} C",
            self._rail_hist("thermals"),
        )
        self._tiles["disk"].set_data(
            "Physical disk",
            f"{snap.disk.busy * 100:.1f}%",
            self._rail_hist("disk"),
        )
        self._tiles["network"].set_data(
            "Network adapter",
            f"S: {bps_h(snap.net.tx_bps)}  R: {bps_h(snap.net.rx_bps)}",
            self._rail_hist("network"),
        )
        gpu_name = snap.gpu.name or "Graphics"
        if len(gpu_name) > 28:
            gpu_name = gpu_name[:25] + "…"
        self._tiles["gpu"].title_lbl.setText(gpu_name)
        vram_pct = (snap.gpu.vram_used / snap.gpu.vram_total * 100.0) if snap.gpu.vram_total else 0.0
        self._tiles["gpu"].set_data(
            "Graphics card",
            f"{snap.gpu.util * 100:.1f}%  ·  VRAM {vram_pct:.0f}%",
            self._rail_hist("gpu"),
        )

    def update_snapshot(self, snap: Snapshot) -> None:
        self._snap = snap
        self._update_rail(snap)
        w = self.stack.currentWidget()
        if w is not None and hasattr(w, "update_snapshot"):
            w.update_snapshot(snap)

    def select_tab(self, key: str) -> None:
        alias = {"storage": "disk"}
        key = alias.get(key, key)
        for i, (k, _label) in enumerate(_PERF_TABS):
            if k == key:
                self.rail.setCurrentRow(i)
                return

    def tick(self, dt: float = 1 / 60) -> None:
        w = self.stack.currentWidget()
        if w is not None and hasattr(w, "tick"):
            w.tick(dt)


class CpuBarDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        r = option.rect.adjusted(1, 1, -1, -1)
        painter.fillRect(r, QColor(24, 72, 42))
        cpu = index.data(Qt.ItemDataRole.UserRole)
        if isinstance(cpu, (int, float)) and cpu > 0:
            frac = min(1.0, float(cpu) / 0.25)
            bar_w = int(r.width() * frac)
            painter.fillRect(QRect(r.x(), r.y(), max(2, bar_w), r.height()), QColor(61, 255, 138, 120))
        super().paint(painter, option, index)


class ProcessPage(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._rows: list[ProcessRow] = []
        self._follow_pid: int | None = None
        self._last_cpu: dict[int, float] = {}
        self._flash: dict[int, float] = {}
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 4, 8, 4)
        head = QHBoxLayout()
        self.view_mode = QComboBox()
        self.view_mode.addItems(["Tree", "Flat"])
        self.view_mode.setMinimumWidth(88)
        view_btn = QPushButton("Process view")
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("Filter by name, user, or PID")
        head.addWidget(view_btn)
        head.addWidget(self.view_mode)
        head.addWidget(self.filter, 1)
        lay.addLayout(head)
        self.follow = QCheckBox("Follow")
        self.end_btn = QPushButton("End task")
        self.kill_btn = QPushButton("Kill tree")
        self.inspect_btn = QPushButton("Inspect files")
        for w in (self.follow, self.end_btn, self.kill_btn, self.inspect_btn):
            w.hide()
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(
            ["Name", "PID", "Status", "User name", "CPU", "Memory", "Disk read", "Disk write", "Threads", "Virtual", "FDs", "Nice", "Command"]
        )
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.setRootIsDecorated(True)
        self.tree.setIndentation(16)
        self.tree.setUniformRowHeights(True)
        self.tree.setAlternatingRowColors(True)
        self.tree.setItemDelegateForColumn(4, CpuBarDelegate(self.tree))
        self.tree.itemSelectionChanged.connect(self._sel)
        lay.addWidget(self.tree, 1)
        self.detail = QLabel("Select a single entry for detail information.")
        self.detail.setObjectName("muted")
        self.detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detail.setMinimumHeight(48)
        self.detail.setWordWrap(True)
        lay.addWidget(self.detail)
        self.end_btn.clicked.connect(lambda: self._act(False))
        self.kill_btn.clicked.connect(lambda: self._act(True))
        self.inspect_btn.clicked.connect(self._inspect)
        self.filter.textChanged.connect(lambda _: self._rebuild())
        self.view_mode.currentIndexChanged.connect(lambda _: self._rebuild())

    def _sel(self) -> None:
        items = self.tree.selectedItems()
        if len(items) != 1:
            self.detail.setText("Select a single entry for detail information.")
            return
        pid = int(items[0].text(1))
        self._follow_pid = pid if self.follow.isChecked() else self._follow_pid
        row = next((r for r in self._rows if r.pid == pid), None)
        if not row:
            return
        kids = descendants(self._rows, pid)
        self.detail.setText(
            f"{row.name}  pid {row.pid}  ppid {row.ppid}  {row.command}\n"
            f"CPU {row.cpu * 100:.1f}%  RSS {bytes_h(row.mem_bytes)}  threads {row.threads}  "
            f"fds {row.fds}  descendants {len(kids)}"
        )

    def _act(self, kill: bool) -> None:
        items = self.tree.selectedItems()
        if not items:
            return
        pid = int(items[0].text(1))
        kids = descendants(self._rows, pid)
        pids = [pid] + kids
        msg = f"{'Kill' if kill else 'End'} {len(pids)} processes?\n" + ", ".join(str(p) for p in pids[:24])
        if QMessageBox.question(self, "Confirm", msg) != QMessageBox.StandardButton.Yes:
            return
        r = end_tree(pids, kill=kill)
        if not r.ok:
            QMessageBox.warning(self, "Failed", r.message)

    def _inspect(self) -> None:
        items = self.tree.selectedItems()
        if not items:
            return
        pid = int(items[0].text(1))
        lines = []
        fd_dir = f"/proc/{pid}/fd"
        try:
            for name in sorted(os.listdir(fd_dir), key=lambda x: int(x) if x.isdigit() else 0)[:80]:
                try:
                    target = os.readlink(os.path.join(fd_dir, name))
                except OSError:
                    continue
                lines.append(f"{name} -> {target}")
        except OSError as exc:
            lines.append(str(exc))
        QMessageBox.information(self, f"Open files {pid}", "\n".join(lines) or "(none)")

    def update_snapshot(self, snap: Snapshot, include_self: bool) -> None:
        self._rows = snap.visible_processes(include_self)
        now = time.time()
        for r in self._rows:
            prev = self._last_cpu.get(r.pid)
            if prev is not None and abs(prev - r.cpu) > 0.02:
                self._flash[r.pid] = now
            self._last_cpu[r.pid] = r.cpu
        self._rebuild()

    def _rebuild(self) -> None:
        q = self.filter.text().lower().strip()
        follow = self._follow_pid if self.follow.isChecked() else None
        expanded = {self.tree.indexOfTopLevelItem(self.tree.topLevelItem(i)) for i in range(self.tree.topLevelItemCount())}
        self.tree.clear()
        rows = self._rows
        if q:
            rows = [r for r in rows if q in r.name.lower() or q in r.user.lower() or q == str(r.pid)]
        by_pid = {r.pid: r for r in self._rows}
        tree_mode = self.view_mode.currentIndex() == 0 and not q
        now = time.time()

        def add(parent: QTreeWidgetItem | None, r: ProcessRow) -> QTreeWidgetItem:
            it = QTreeWidgetItem(
                [
                    r.name,
                    str(r.pid),
                    r.status,
                    r.user,
                    f"{r.cpu * 100:.1f}%",
                    bytes_h(r.mem_bytes),
                    bps_h(r.disk_read_bps),
                    bps_h(r.disk_write_bps),
                    str(r.threads),
                    bytes_h(r.virt_bytes),
                    str(r.fds),
                    str(r.nice),
                    r.command,
                ]
            )
            it.setData(4, Qt.ItemDataRole.UserRole, r.cpu)
            flash_t = self._flash.get(r.pid)
            if flash_t and now - flash_t < 0.6:
                a = int(80 * (1 - (now - flash_t) / 0.6))
                it.setBackground(0, QBrush(QColor(61, 255, 138, a)))
            if parent is None:
                self.tree.addTopLevelItem(it)
            else:
                parent.addChild(it)
            if r.cpu > 0.05:
                it.setBackground(4, QBrush(QColor(61, 255, 138, 50)))
            return it

        if tree_mode:
            items: dict[int, QTreeWidgetItem] = {}
            pending = list(rows)
            guard = 0
            while pending and guard < 20:
                guard += 1
                nxt = []
                for r in pending:
                    if r.ppid in items:
                        items[r.pid] = add(items[r.ppid], r)
                    elif r.ppid not in by_pid or r.ppid == r.pid:
                        items[r.pid] = add(None, r)
                    else:
                        nxt.append(r)
                if len(nxt) == len(pending):
                    for r in nxt:
                        items[r.pid] = add(None, r)
                    break
                pending = nxt
            for i in range(min(8, self.tree.topLevelItemCount())):
                self.tree.topLevelItem(i).setExpanded(True)
        else:
            for r in sorted(rows, key=lambda x: x.cpu, reverse=True):
                add(None, r)
        if follow:
            found = self.tree.findItems(str(follow), Qt.MatchFlag.MatchExactly, 1)
            if found:
                self.tree.setCurrentItem(found[0])
                self.tree.scrollToItem(found[0])


class TelemetryPage(QWidget):
    def __init__(self, kind: str, title: str | None = None, parent=None) -> None:
        super().__init__(parent)
        self.kind = kind
        self._history: HistoryBank | None = None
        self.theme: Theme | None = None
        self.visual = VisualState()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.title = QLabel(title or kind.title())
        self.title.setStyleSheet("font-size: 22px; font-weight: 600;")
        lay.addWidget(self.title)
        self.chart = TimeSeriesWidget()
        lay.addWidget(self.chart, 1)
        self.body = QLabel()
        self.body.setWordWrap(True)
        lay.addWidget(self.body)
        self.table = QTableWidget(0, 4)
        lay.addWidget(self.table, 1)

    def bind_history(self, h: HistoryBank) -> None:
        self._history = h

    def apply_theme(self, theme: Theme, visual: VisualState) -> None:
        self.theme = theme
        self.visual = visual
        self.chart.theme = theme
        self.chart.visual = visual

    def update_snapshot(self, snap: Snapshot) -> None:
        t = self.theme
        h = self._history
        if self.kind == "storage":
            if h and t:
                self.chart.set_series(
                    [("Read", h.get("disk_r_bps"), t.disk), ("Write", h.get("disk_w_bps"), t.temp)]
                )
            self.body.setText(f"Combined  R {bps_h(snap.disk.read_bps)}  W {bps_h(snap.disk.write_bps)}")
            self.table.setColumnCount(6)
            self.table.setHorizontalHeaderLabels(["Device", "Read", "Write", "Busy", "Size", "Mount"])
            self.table.setRowCount(len(snap.disk.devices))
            for i, d in enumerate(snap.disk.devices):
                for c, v in enumerate(
                    [d.name, bps_h(d.read_bps), bps_h(d.write_bps), f"{d.busy * 100:.1f}%", bytes_h(d.size_bytes), d.mount]
                ):
                    self.table.setItem(i, c, QTableWidgetItem(v))
        elif self.kind == "network":
            cap = max(snap.net.link_speed_mbps * 125_000, 1.0)
            if h and t:
                self.chart.set_series(
                    [("Rx", h.get("net_r_bps"), t.net), ("Tx", h.get("net_w_bps"), t.accent)]
                )
            self.body.setText(
                f"R {bps_h(snap.net.rx_bps)}  W {bps_h(snap.net.tx_bps)}  "
                f"session {bytes_h(snap.net.session_rx)} / {bytes_h(snap.net.session_tx)}  "
                f"link {snap.net.link_speed_mbps:.0f} Mb/s  ceiling {bps_h(cap)}"
            )
            real = [i for i in snap.net.ifaces if not i.is_virtual]
            use = real or snap.net.ifaces
            self.table.setColumnCount(6)
            self.table.setHorizontalHeaderLabels(["Iface", "Rx", "Tx", "State", "Speed", "Kind"])
            self.table.setRowCount(len(use))
            for i, n in enumerate(use):
                for c, v in enumerate(
                    [n.name, bps_h(n.rx_bps), bps_h(n.tx_bps), n.operstate, f"{n.speed_mbps:.0f}", "virtual" if n.is_virtual else "physical"]
                ):
                    self.table.setItem(i, c, QTableWidgetItem(v))
        elif self.kind == "energy":
            if h and t:
                self.chart.set_series([("Watts", h.get("power_w"), t.temp)])
            w = snap.energy.watts
            batt = "" if snap.energy.battery_pct is None else f"  battery {snap.energy.battery_pct:.0f}%"
            self.body.setText(
                f"{'Power unavailable' if w is None else f'{w:.1f} W'}  "
                f"governor {snap.