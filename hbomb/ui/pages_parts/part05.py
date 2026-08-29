            batt = "" if snap.energy.battery_pct is None else f"  battery {snap.energy.battery_pct:.0f}%"
            self.body.setText(
                f"{'Power unavailable' if w is None else f'{w:.1f} W'}  "
                f"governor {snap.energy.governor}  state {snap.energy.power_state}{batt}\n"
                "Per-process energy is n/a on this kernel unless a future helper fills it."
            )
            self.table.setRowCount(0)
        elif self.kind == "thermals":
            if h and t:
                self.chart.set_series([("Hotspot", h.get("temp_c"), t.temp)])
            lines = [f"Hotspot {snap.thermals.hotspot_c:.1f} °C  (orange signal path)"]
            self.table.setColumnCount(3)
            self.table.setHorizontalHeaderLabels(["Sensor", "°C", "Kind"])
            self.table.setRowCount(len(snap.thermals.sensors))
            for i, s in enumerate(snap.thermals.sensors):
                for c, v in enumerate([s.name, f"{s.temp_c:.1f}", s.kind]):
                    self.table.setItem(i, c, QTableWidgetItem(v))
            self.body.setText("\n".join(lines))
        elif self.kind == "gpu":
            self.chart.fixed_max = 100.0
            if h and t:
                vram_col = t.danger
                self.chart.set_series(
                    [
                        ("GPU %", h.get("gpu_util_pct"), t.gpu, 100.0, "left", True),
                        ("VRAM %", h.get("gpu_vram_pct"), vram_col, 100.0, "left", False),
                    ]
                )
            g = snap.gpu
            npu = snap.npu
            npu_txt = f"{npu.util * 100:.0f}%" if npu.available else "not published"
            self.body.setText(
                f"{g.name or 'GPU unavailable'}  {g.util * 100:.1f}%  "
                f"VRAM {bytes_h(g.vram_used)} / {bytes_h(g.vram_total)}  "
                f"{g.temp_c:.0f}°C  {g.clock_mhz:.0f} MHz\nNPU: {npu_txt}"
            )
            self.table.setRowCount(0)


class PowerFreqPage(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.theme: Theme | None = None
        self.visual = VisualState()
        self._mins: dict[str, float] = {}
        self._maxs: dict[str, float] = {}
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 4, 8, 8)
        self.chart_slot = QFrame()
        self.chart_slot.setObjectName("card")
        self.chart_slot.setMinimumHeight(72)
        self.chart_slot.setMaximumHeight(72)
        lay.addWidget(self.chart_slot)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Sensor", "Value", "Min", "Max"])
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.header().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.setRootIsDecorated(True)
        self.tree.setAlternatingRowColors(True)
        self.tree.setUniformRowHeights(True)
        lay.addWidget(self.tree, 1)

    def _track(self, key: str, value: float) -> tuple[float, float, float]:
        if key not in self._mins:
            self._mins[key] = value
            self._maxs[key] = value
        else:
            self._mins[key] = min(self._mins[key], value)
            self._maxs[key] = max(self._maxs[key], value)
        return value, self._mins[key], self._maxs[key]

    def _row(self, parent: QTreeWidgetItem | QTreeWidget, name: str, value: str, vmin: str = "", vmax: str = "") -> QTreeWidgetItem:
        item = QTreeWidgetItem([name, value, vmin, vmax])
        if isinstance(parent, QTreeWidget):
            parent.addTopLevelItem(item)
        else:
            parent.addChild(item)
        return item

    def update_snapshot(self, snap: Snapshot) -> None:
        self.tree.clear()
        root = self._row(self.tree, "This PC", "", "", "")
        cpu_name = snap.cpu.model_name or f"{snap.cpu.physical_cores or len(snap.cpu.cores)}-Core Processor"
        proc = self._row(root, cpu_name, "", "", "")
        proc.setExpanded(True)
        clocks = self._row(proc, "Clocks", "", "", "")
        clocks.setExpanded(True)
        avg = snap.cpu.freq_ghz
        _v, mn, mx = self._track("cpu.avg_ghz", avg)
        self._row(clocks, "Average effective", f"{avg:.2f} GHz", f"{mn:.2f} GHz", f"{mx:.2f} GHz")
        for core in snap.cpu.cores[: min(8, len(snap.cpu.cores))]:
            key = f"cpu.core{core.index}"
            _v, mn, mx = self._track(key, core.freq_ghz)
            self._row(clocks, f"Core {core.index}", f"{core.freq_ghz:.2f} GHz", f"{mn:.2f} GHz", f"{mx:.2f} GHz")
        temps = self._row(proc, "Temperatures", "", "", "")
        hot = snap.thermals.hotspot_c
        _v, mn, mx = self._track("cpu.temp", hot)
        self._row(temps, "Package", f"{hot:.0f} °C", f"{mn:.0f} °C", f"{mx:.0f} °C")
        for sensor in snap.thermals.sensors[:4]:
            key = f"temp.{sensor.name}"
            _v, mn, mx = self._track(key, sensor.temp_c)
            self._row(temps, sensor.name, f"{sensor.temp_c:.0f} °C", f"{mn:.0f} °C", f"{mx:.0f} °C")
        powers = self._row(proc, "Powers", "", "", "")
        w = snap.energy.watts
        if w is not None:
            _v, mn, mx = self._track("cpu.power", w)
            self._row(powers, "Package", f"{w:.1f} W", f"{mn:.1f} W", f"{mx:.1f} W")
        else:
            self._row(powers, "Package", "—", "—", "—")
        if snap.gpu.available and snap.gpu.name:
            gpu = self._row(root, "Discrete GPU", "", "", "")
            ghz = snap.gpu.clock_mhz / 1000.0 if snap.gpu.clock_mhz else 0.0
            _v, mn, mx = self._track("gpu.clock", ghz)
            self._row(gpu, snap.gpu.name, f"{ghz:.2f} GHz", f"{mn:.2f} GHz", f"{mx:.2f} GHz")
        mem = self._row(root, "System Memory", "", "", "")
        used_gib = snap.memory.occupied_bytes / (1024**3)
