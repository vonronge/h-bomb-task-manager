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

