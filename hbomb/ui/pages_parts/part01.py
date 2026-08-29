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
