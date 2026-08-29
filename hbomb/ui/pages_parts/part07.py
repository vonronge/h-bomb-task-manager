ck.addWidget(self.treesize)
        main.addWidget(self.stack, 1)
        self.smart = QTableWidget(0, 4)
        self.smart.setHorizontalHeaderLabels(["Device", "Temp", "Data units", "Model"])
        main.addWidget(self.smart)
        main_w = QWidget()
        main_w.setLayout(main)
        root.addWidget(main_w, 1)

        self.view.currentIndexChanged.connect(self.stack.setCurrentIndex)
        self.view.currentIndexChanged.connect(self._remember)
        self.browse.clicked.connect(self._browse)
        self.scan.clicked.connect(self._scan)
        self.up.clicked.connect(self.treemap.zoom_out)
        self._smart_loaded = False

    def showEvent(self, ev) -> None:
        super().showEvent(ev)
        if not self._smart_loaded:
            self._smart_loaded = True
            self._load_smart()

    def _remember(self, _i: int) -> None:
        pass

    def apply_theme(self, theme: Theme, visual: VisualState) -> None:
        self.treemap.theme = theme
        view_id = visual.disk_view
        if view_id in ("windirstat", "balls", "block"):
            view_id = "buckets"
        elif view_id == "treesize":
            view_id = "paths"
        idx = {"buckets": 0, "paths": 1}.get(view_id, 0)
        self.view.setCurrentIndex(idx)

    def current_view_id(self) -> str:
        return ["buckets", "paths"][self.view.currentIndex()]

    def _browse(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Scan folder", self.path.text())
        if d:
            self.path.setText(d)

    def _load_smart(self) -> None:
        rows = sample_smart()
        self.smart.setRowCount(len(rows))
        for i, r in enumerate(rows):
            for c, v in enumerate([r.name, r.temp_c, r.data_units, r.detail]):
                self.smart.setItem(i, c, QTableWidgetItem(v))

    def _scan(self) -> None:
        root = self.path.text().strip() or os.path.expanduser("~")
        self.status.setText(f"Scanning {root}…")
        self._cancel = False

        class _W(QObject):
            done = Signal(object)
            failed = Signal(str)

            def __init__(self, path: str) -> None:
                super().__init__()
                self.path = path

            def run(self) -> None:
                try:
                    rows = walk(self.path)
                    self.done.emit(build_tree(rows))
                except Exception as exc:
                    self.failed.emit(str(exc))

        self._thread = QThread(self)
        self._worker = _W(root)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.done.connect(self._on_tree)
        self._worker.failed.connect(lambda m: self.status.setText(m))
        self._worker.done.connect(self._thread.quit)
        self._thread.start()

    def _on_tree(self, tree: DiskNode) -> None:
        self._tree = tree
        self.treemap.set_tree(tree)
        self.treesize.set_tree(tree)
        self.status.setText(f"{tree.path}  {bytes_h(tree.size)}  {tree.file_count} files")


class BenchmarksPage(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._history: list[tuple[str, float, float, str]] = []
        self._running = False
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 4, 8, 8)
        self.note = QLabel("Benchmarks are a TMOG Pro feature. A TMOG Pro license is required to run benchmarks.")
        self.note.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.note.setObjectName("muted")
        root.addWidget(self.note)

        split = QHBoxLayout()
        root.addLayout(split, 1)
        self.sidebar = QListWidget()
        self.sidebar.setObjectName("benchNav")
        self.sidebar.setMaximumWidth(128)
        self.sidebar.setFrameShape(QListWidget.Shape.NoFrame)
        self.sidebar.setStyleSheet(
            "QListWidget#benchNav { border: none; background: transparent; }"
            "QListWidget#benchNav::item { padding: 8px 12px; border-radius: 4px; }"
            "QListWidget#benchNav::item:selected { background: #3d8bfd; color: #ffffff; }"
        )
        for label in _BENCH_KINDS:
            self.sidebar.addItem(label)
        self.sidebar.setCurrentRow(0)
        split.addWidget(self.sidebar)

        body = QVBoxLayout()
        split.addLayout(body, 1)

        self.title = QLabel("CPU Benchmark")
        self.title.setStyleSheet("font-size: 18px; font-weight: 400; color: #c5c9d0;")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body.addWidget(self.title)

        gauges = QHBoxLayout()
        self.g1 = CarbonBenchmarkGauge("SINGLE CORE", "Mops/sec", 800)
        self.g2 = CarbonBenchmarkGauge("MULTI CORE", "Gop/sec", 8)
        gauges.addWidget(self.g1, 1)
        gauges.addWidget(self.g2, 1)
        body.addLayout(gauges, 3)

        controls = QVBoxLayout()
        self.progress = VfdMeter("", QColor("#5ad0ff"), vertical=False)
        self.progress.ramp = "gpu"
        self.progress.setMaximumHeight(16)
        self.progress.setMaximumWidth(220)
        self.start = QPushButton("Start")
        self.start.setMinimumWidth(90)
        self.start.setMaximumWidth(90)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(self.progress)
        row.addStretch()
        controls.addLayout(row)
        brow = QHBoxLayout()
        brow.addStretch()
        brow.addWidget(self.start)
        brow.addStretch()
        controls.addLayout(brow)
        body.addLayout(controls)

        hist_head = QHBoxLayout()
        hist_head.addWidget(QLabel("History"))
        hist_head.addStretch()
        self.clear = QPushButton("Clear History…")
        hist_head.addWidget(self.clear)
        body.addLayout(hist_head)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            ["Date", "Single core (Mops/sec)", "Multi core (Gop/sec)", "Notes"]
        )
        self.table.horizontalHeader().setSection