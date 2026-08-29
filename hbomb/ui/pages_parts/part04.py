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
