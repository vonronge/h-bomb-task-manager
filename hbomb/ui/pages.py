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


# TRUNCATED_FOR_SIZE_TEST