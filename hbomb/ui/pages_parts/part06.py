        _v, mn, mx = self._track("mem.used_gib", used_gib)
        self._row(mem, "In use", f"{used_gib:.1f} GiB", f"{mn:.1f} GiB", f"{mx:.1f} GiB")
        for dev in snap.disk.devices[:3]:
            disk = self._row(root, dev.name or "NVMe SSD", "", "", "")
            busy = dev.busy * 100.0
            _v, mn, mx = self._track(f"disk.{dev.name}.busy", busy)
            self._row(disk, "Activity", f"{busy:.1f}%", f"{mn:.1f}%", f"{mx:.1f}%")
        root.setExpanded(True)


class SimpleTablePage(QWidget):
    def __init__(self, title: str, headers: list[str], loader, parent=None) -> None:
        super().__init__(parent)
        self.loader = loader
        lay = QVBoxLayout(self)
        row = QHBoxLayout()
        lab = QLabel(title)
        lab.setStyleSheet("font-size: 22px; font-weight: 600;")
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self.reload)
        row.addWidget(lab)
        row.addStretch()
        row.addWidget(refresh)
        lay.addLayout(row)
        self.note = QLabel("")
        self.note.setWordWrap(True)
        lay.addWidget(self.note)
        self.table = QTableWidget(0, len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        lay.addWidget(self.table, 1)
        extra = QHBoxLayout()
        self.extra_layout = extra
        lay.addLayout(extra)
        self._loaded = False

    def showEvent(self, ev) -> None:
        super().showEvent(ev)
        if not self._loaded:
            self._loaded = True
            self.reload()

    def reload(self) -> None:
        try:
            rows = self.loader()
        except Exception as exc:
            self.note.setText(str(exc))
            return
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for c, v in enumerate(row):
                self.table.setItem(i, c, QTableWidgetItem(str(v)))


MORE_NAV = [
    ("startup", "Login Items"),
    ("users", "Accounts"),
    ("services", "System Services"),
    ("connections", "Open Connections"),
    ("power", "Power & Clocks"),
    ("benchmarks", "Speed Tests"),
    ("apps", "Installed Software"),
]

MORE_FLAG_MAP = {
    "connections": "connections",
    "power": "power_freq",
    "apps": "installed_apps",
    "benchmarks": "benchmarks",
}


class MoreHubPage(QWidget):
    section_changed = Signal(str, str)

    def __init__(
        self,
        sections: list[tuple[str, str, QWidget]],
        flags: FeatureFlags,
        parent=None,
    ) -> None:
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        self.rail = QListWidget()
        self.rail.setObjectName("nav")
        self.rail.setFixedWidth(200)
        self.stack = QStackedWidget()
        self._keys: list[str] = []
        self._labels: list[str] = []
        rail_font = QFont(self.font().family(), 10, QFont.Weight.Medium)
        fm = QFontMetrics(rail_font)
        for key, label, page in sections:
            if key in MORE_FLAG_MAP and not flags.enabled(MORE_FLAG_MAP[key]):
                continue
            item = QListWidgetItem(label)
            item.setFont(rail_font)
            item.setSizeHint(QSize(max(180, fm.horizontalAdvance(label) + 24), 32))
            self.rail.addItem(item)
            self.stack.addWidget(page)
            self._keys.append(key)
            self._labels.append(label)
        self.rail.currentRowChanged.connect(self._on_row)
        lay.addWidget(self.rail)
        lay.addWidget(self.stack, 1)
        if self._keys:
            self.rail.setCurrentRow(0)

    def _on_row(self, row: int) -> None:
        if 0 <= row < len(self._keys):
            self.stack.setCurrentIndex(row)
            self.section_changed.emit(self._keys[row], self.rail.item(row).text())

    def select(self, key: str) -> None:
        if key in self._keys:
            self.rail.setCurrentRow(self._keys.index(key))

    def current_key(self) -> str:
        row = self.rail.currentRow()
        if 0 <= row < len(self._keys):
            return self._keys[row]
        return self._keys[0] if self._keys else ""

    def current_page(self) -> QWidget | None:
        idx = self.stack.currentIndex()
        if idx < 0:
            return None
        return self.stack.widget(idx)

    def apply_theme(self, theme: Theme, visual: VisualState) -> None:
        for i in range(self.stack.count()):
            w = self.stack.widget(i)
            if w is not None and hasattr(w, "apply_theme"):
                w.apply_theme(theme, visual)


class DiskSpacePage(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._tree: DiskNode | None = None
        self._cancel = False
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        left = QVBoxLayout()
        left.setSpacing(6)
        title = QLabel("Disk Usage")
        title.setObjectName("settingsSection")
        left.addWidget(title)
        left.addWidget(QLabel("View"))
        self.view = QComboBox()
        self.view.addItems(["Treemap", "Folder Tree"])
        left.addWidget(self.view)
        self.browse = QPushButton("Browse…")
        self.scan = QPushButton("Scan")
        self.up = QPushButton("Up")
        left.addWidget(self.browse)
        left.addWidget(self.scan)
        left.addWidget(self.up)
        left.addStretch()
        left_w = QWidget()
        left_w.setLayout(left)
        left_w.setFixedWidth(132)
        root.addWidget(left_w)

        main = QVBoxLayout()
        path_row = QHBoxLayout()
        path_row.addWidget(QLabel("Path"))
        self.path = QLineEdit(os.path.expanduser("~"))
        path_row.addWidget(self.path, 1)
        main.addLayout(path_row)
        self.status = QLabel("One walker, several views. Switching views does not rescan.")
