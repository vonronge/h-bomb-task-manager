00.0
        return single, multi, f"x={x}"

    def _bench_gpu(self) -> float:
        t0 = time.perf_counter()
        data = [0.0] * 1_000_000
        for i in range(len(data)):
            data[i] = math.sin(i * 0.001) * math.cos(i * 0.002)
        dt = max(1e-6, time.perf_counter() - t0)
        return 500.0 / dt

    def _bench_disk(self) -> float:
        path = "/tmp/hbomb_score.bin"
        payload = os.urandom(4 * 1024 * 1024)
        t0 = time.perf_counter()
        with open(path, "wb") as fh:
            for _ in range(32):
                fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        dt = max(1e-6, time.perf_counter() - t0)
        try:
            os.remove(path)
        except OSError:
            pass
        return 128.0 / dt

    def _bench_internet(self) -> float:
        import urllib.request

        t0 = time.perf_counter()
        urllib.request.urlopen("https://example.com", timeout=5).read(64)
        dt = time.perf_counter() - t0
        return 1000.0 / max(dt, 0.01)


class FlightRecorderPage(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._buf: deque[dict] = deque(maxlen=3600)
        self._playing = False
        self._i = 0
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Flight Recorder"))
        row = QHBoxLayout()
        self.cap = QPushButton("Capture")
        self.play = QPushButton("Replay")
        row.addWidget(self.cap)
        row.addWidget(self.play)
        row.addStretch()
        lay.addLayout(row)
        self.chart = TimeSeriesWidget()
        lay.addWidget(self.chart, 1)
        self.body = QLabel("Records CPU, mem, GPU, power, disk, net each structural tick.")
        lay.addWidget(self.body)
        self.cap.clicked.connect(self._toggle)
        self.play.clicked.connect(self._replay)
        self._on = False

    def apply_theme(self, theme: Theme, visual: VisualState) -> None:
        self.chart.theme = theme
        self.chart.visual = visual

    def _toggle(self) -> None:
        self._on = not self._on
        self.cap.setText("Stop" if self._on else "Capture")

    def ingest(self, snap: Snapshot) -> None:
        if not self._on:
            return
        self._buf.append(
            {
                "t": snap.timestamp,
                "cpu": snap.cpu.overall.total * 100,
                "mem": snap.memory.used_ratio * 100,
                "gpu": snap.gpu.util * 100,
                "power": snap.energy.watts or 0.0,
            }
        )
        self.body.setText(f"{len(self._buf)} samples")

    def _replay(self) -> None:
        from hbomb.snapshot.history import LogHistory

        cpu, mem, gpu = LogHistory(), LogHistory(), LogHistory()
        for i, s in enumerate(self._buf):
            cpu.push(s["t"], s["cpu"])
            mem.push(s["t"], s["mem"])
            gpu.push(s["t"], s["gpu"])
        t = self.chart.theme
        col = t.cpu if t else QColor("#3dff8a")
        self.chart.set_series(
            [
                ("CPU", cpu, col),
                ("Mem", mem, t.mem if t else QColor("#b07cff")),
                ("GPU", gpu, t.gpu if t else QColor("#4da3ff")),
            ]
        )


class _SettingsCard(QFrame):
    def __init__(self, title: str, icon_name: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("settingsCard")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 12, 14, 14)
        outer.setSpacing(10)
        head = QHBoxLayout()
        self._icon = QLabel()
        self._icon.setFixedSize(18, 18)
        lab = QLabel(title)
        lab.setObjectName("settingsSection")
        head.addWidget(self._icon)
        head.addWidget(lab)
        head.addStretch()
        outer.addLayout(head)
        self.body = QVBoxLayout()
        self.body.setSpacing(8)
        outer.addLayout(self.body)
        self._icon_name = icon_name

    def apply_theme(self, theme: Theme) -> None:
        pm = nav_icon(self._icon_name, theme.text, 16).pixmap(16, 16)
        self._icon.setPixmap(pm)


class _SettingsRow(QWidget):
    def __init__(self, label: str, widget: QWidget, hint: str = "", parent=None) -> None:
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        row.addStretch()
        row.addWidget(widget)
        lay.addLayout(row)
        if hint:
            h = QLabel(hint)
            h.setObjectName("settingsHint")
            h.setWordWrap(True)
            lay.addWidget(h)


class ColorsPanel(QWidget):
    """Color tuning controls — embedded in ColorsPage or used as a popup."""

    changed = Signal()

    def __init__(self, visual: VisualState, parent=None, *, popup: bool = False, embedded: bool = False) -> None:
        flags = Qt.WindowType(0)
        if popup:
            flags = Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint
        super().__init__(parent, flags)
        self.visual = visual
        self.setObjectName("colorsPanel")
        if popup:
            self.setFixedWidth(260)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0 if embedded else 12, 0 if embedded else 10, 0 if embedded else 12, 0 if embedded else 12)
        lay.setSpacing(8)
        if not embedded:
            title = QLabel("Colors")
            title.setObjectName("settingsSection")
            lay.addWidget(title)
        self.display = QComboBox()
        self.display.addItems(["Color", "Green", "Amber", "White", "Blue", "Mono"])
        mode_map = {"full": 0, "green": 1, "amber": 2, "white": 3, "blue": 4, "mono": 5}
        self.display.setCurrentIndex(mode_map.get(visual.color_mode, 0))
        self.ambiance = QComboBox()
        self.ambiance.addItems([label for _key, label in AMBIANCE_CHOICES])
        self.ambiance.setCurrentIndex(ambiance_index(visual.chrome))
        self.sat = 