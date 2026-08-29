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
