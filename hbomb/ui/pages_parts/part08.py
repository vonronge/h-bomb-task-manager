ResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setMinimumHeight(80)
        body.addWidget(self.table, 2)
        self._empty = QLabel("Benchmark runs will appear here as they complete.")
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty.setStyleSheet("color: #666; padding: 24px; font-style: italic;")
        body.addWidget(self._empty)

        self.sidebar.currentRowChanged.connect(self._switch_kind)
        self.start.clicked.connect(self._run)
        self.clear.clicked.connect(self._clear_history)
        self._switch_kind(0)
        self._refresh_table()
        self._restore_gauges()

    def _restore_gauges(self) -> None:
        if not self._history:
            return
        _date, single, multi, _note = self._history[-1]
        self.g1.set_instant(single)
        self.g2.set_instant(multi)

    def _switch_kind(self, row: int) -> None:
        kind = _BENCH_KINDS[row] if 0 <= row < len(_BENCH_KINDS) else _BENCH_KINDS[0]
        self.title.setText(f"{kind} Benchmark" if kind != "Overall Score" else "Overall Score")
        if kind == "Processor":
            self.g1.title = "SINGLE CORE"
            self.g1.unit = "Mops/sec"
            self.g1.max_value = 800
            self.g2.setVisible(True)
            self.g2.title = "MULTI CORE"
            self.g2.unit = "Gop/sec"
            self.g2.max_value = 8
        elif kind == "Graphics":
            self.g1.title = "GPU"
            self.g1.unit = "score"
            self.g1.max_value = 1000
            self.g2.setVisible(False)
        elif kind == "Storage":
            self.g1.title = "WRITE"
            self.g1.unit = "MB/s"
            self.g1.max_value = 4000
            self.g2.setVisible(False)
        elif kind == "Network":
            self.g1.title = "LATENCY"
            self.g1.unit = "score"
            self.g1.max_value = 1000
            self.g2.setVisible(False)
        else:
            self.g1.title = "SYSTEM"
            self.g1.unit = "score"
            self.g1.max_value = 1000
            self.g2.setVisible(True)
            self.g2.title = "DETAIL"
            self.g2.unit = "Gop/sec"
            self.g2.max_value = 8
        self.g1.update()
        self.g2.update()

    def _clear_history(self) -> None:
        self._history.clear()
        self._refresh_table()

    def _refresh_table(self) -> None:
        self.table.setRowCount(len(self._history))
        self._empty.setVisible(len(self._history) == 0)
        for i, row in enumerate(self._history):
            for c, v in enumerate(row):
                text = f"{v:.1f}" if isinstance(v, float) else str(v)
                self.table.setItem(i, c, QTableWidgetItem(text))
        if self._history and self.sidebar.currentRow() == 0:
            _date, single, multi, _note = self._history[-1]
            self.g1.set_instant(single)
            self.g2.set_instant(multi)

    def _run(self) -> None:
        if self._running:
            return
        self._running = True
        self.start.setEnabled(False)
        self.progress.set_value(0.1, "")
        kind = self.sidebar.currentItem().text() if self.sidebar.currentItem() else _BENCH_KINDS[0]
        try:
            if kind == "Processor":
                single, multi, note = self._bench_cpu()
                self.g1.max_value = max(800, single * 1.2)
                self.g2.max_value = max(8, multi * 1.2)
                self.g1.set_instant(single)
                self.g2.set_instant(multi)
                self._history.append((time.strftime("%Y-%m-%d %H:%M"), single, multi, note))
            elif kind == "Graphics":
                score = self._bench_gpu()
                self.g1.max_value = max(1000, score * 1.2)
                self.g1.set_instant(score)
                self._history.append((time.strftime("%Y-%m-%d %H:%M"), score, 0.0, "gpu"))
            elif kind == "Storage":
                mbps = self._bench_disk()
                self.g1.max_value = max(4000, mbps * 1.2)
                self.g1.set_instant(mbps)
                self._history.append((time.strftime("%Y-%m-%d %H:%M"), mbps, 0.0, "disk write MB/s"))
            elif kind == "Network":
                score = self._bench_internet()
                self.g1.set_instant(score)
                self._history.append((time.strftime("%Y-%m-%d %H:%M"), score, 0.0, "internet"))
            else:
                single, multi, note = self._bench_cpu()
                disk = self._bench_disk()
                net = self._bench_internet()
                composite = single * 0.5 + multi * 200 + disk * 0.1 + net * 0.05
                self.g1.max_value = max(1000, composite * 1.2)
                self.g1.set_instant(composite)
                self.g2.set_instant(multi)
                self._history.append((time.strftime("%Y-%m-%d %H:%M"), composite, multi, f"cpu+disk+net {note}"))
            self.progress.set_value(1.0, "Done")
        finally:
            self._running = False
            self.start.setEnabled(True)
            self._refresh_table()

    def tick(self, dt: float = 1 / 60) -> None:
        self.g1.tick(dt)
        self.g2.tick(dt)
        self.progress.tick(dt)

    def _bench_cpu(self) -> tuple[float, float, str]:
        t0 = time.perf_counter()
        x = 0
        for _ in range(8_000_000):
            x = (x * 1664525 + 1013904223) & 0xFFFFFFFF
        dt = max(1e-6, time.perf_counter() - t0)
        single = 8.0 / dt
        self.progress.set_value(0.45, "Multi…")
        t0 = time.perf_counter()
        n = os.cpu_count() or 4
        from concurrent.futures import ThreadPoolExecutor

        def work(_i: int) -> None:
            y = 0
            for _j in range(2_000_000):
                y = (y * 1664525 + 1013904223) & 0xFFFFFFFF

        with ThreadPoolExecutor(max_workers=n) as ex:
            list(ex.map(work, range(n)))
        dtm = max(1e-6, time.perf_counter() - t0)
        multi = (n * 2.0) / dtm / 10