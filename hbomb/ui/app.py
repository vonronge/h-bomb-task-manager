from __future__ import annotations

import time

from PySide6.QtCore import Qt, QSettings, QSize, QTimer
from PySide6.QtGui import QAction, QGuiApplication, QColor, QFont, QFontMetrics
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QListView,
    QStackedWidget,
    QLabel,
    QStatusBar,
    QMessageBox,
    QPushButton,
    QApplication,
)

from hbomb.providers.linux.extras import list_connections
from hbomb.snapshot.engine import SnapshotEngine
from hbomb.snapshot.flags import FeatureFlags
from hbomb.snapshot import health_label
from hbomb.snapshot.types import Snapshot, ProviderHealth
from hbomb.ui.home import HomePage
from hbomb.ui.icons import nav_icon
from hbomb.ui.pages import (
    PerformancePage,
    ProcessPage,
    PowerFreqPage,
    DiskSpacePage,
    BenchmarksPage,
    FlightRecorderPage,
    SettingsPage,
    SimpleTablePage,
    MoreHubPage,
    MORE_NAV,
    MORE_FLAG_MAP,
    make_inventory_pages,
)
from hbomb.ui.theme import VisualState, resolve_theme, apply_palette
from hbomb.ui.widgets import BlinkenDisk, StatusLed, BrandLogo


NAV = [
    ("summary", "Overview"),
    ("performance", "Performance"),
    ("processes", "Running Apps"),
    ("sysinfo", "Hardware"),
    ("disk", "Disk Usage"),
    ("more", "Extras"),
    ("settings", "Preferences"),
]

MORE_KEYS = {key for key, _ in MORE_NAV}

NAV_ICONS = {
    "summary": "summary",
    "performance": "performance",
    "processes": "processes",
    "sysinfo": "sysinfo",
    "disk": "disk",
    "more": "more",
    "settings": "settings",
}

TITLES = {k: label for k, label in NAV}
TITLES.update({k: label for k, label in MORE_NAV})


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("H-Bomb Task Manager")
        self.resize(1280, 800)
        self.flags = FeatureFlags()
        self.visual = VisualState()
        self._load_settings()
        self.engine = SnapshotEngine(self)
        self._snap: Snapshot | None = None
        self._last_ui_paint = 0.0
        self._last_proc_paint = 0.0
        self._icon_color = QColor("#c5c9d0")
        self._current_key = "summary"

        self.home = HomePage()
        self.performance = PerformancePage()
        self.procs = ProcessPage()
        self.power = PowerFreqPage()
        self.disk = DiskSpacePage()
        self.score = BenchmarksPage()
        self.settings = SettingsPage(self.visual, self.flags)
        inv = make_inventory_pages()
        self.flight = FlightRecorderPage()
        self.journal = inv.pop("journal")
        self.mounts = inv.pop("mounts")
        self.startup = inv.pop("startup")
        self.users = inv.pop("users")
        self.services = inv.pop("services")
        self.apps_page = inv.pop("apps")

        def conn_rows():
            snap = self._snap
            pn = {p.pid: p.name for p in snap.processes} if snap else {}
            return [(c.proto, c.local, c.remote, c.state, c.pid, c.process or pn.get(c.pid, "")) for c in list_connections(pn)]

        self.connections = SimpleTablePage(
            "Connections",
            ["Proto", "Local", "Remote", "State", "PID", "Process"],
            conn_rows,
        )

        self.more = MoreHubPage(
            [
                ("startup", "Login Items", self.startup),
                ("users", "Accounts", self.users),
                ("services", "System Services", self.services),
                ("connections", "Open Connections", self.connections),
                ("power", "Power & Clocks", self.power),
                ("benchmarks", "Speed Tests", self.score),
                ("apps", "Installed Software", self.apps_page),
            ],
            self.flags,
        )

        self.pages: dict[str, QWidget] = {
            "summary": self.home,
            "performance": self.performance,
            "processes": self.procs,
            "sysinfo": inv["sysinfo"],
            "disk": self.disk,
            "more": self.more,
            "settings": self.settings,
            "flight": self.flight,
            "journal": self.journal,
            "mounts": self.mounts,
        }

        hist = self.engine.history
        self.home.bind_history(hist)
        self.performance.bind_history(hist)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        top_bar = QWidget()
        top_bar.setObjectName("topNav")
        top_lay = QHBoxLayout(top_bar)
        top_lay.setContentsMargins(8, 4, 8, 0)
        top_lay.setSpacing(8)
        self.nav = QListWidget()
        self.nav.setObjectName("nav")
        self.nav.setFlow(QListView.Flow.LeftToRight)
        self.nav.setWrapping(False)
        self.nav.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.nav.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.nav.setIconSize(QSize(20, 20))
        self.nav.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.nav.setFixedHeight(46)
        self._fill_nav()
        top_lay.addWidget(self.nav, 1)
        self._brand = BrandLogo()
        self._brand.setFixedHeight(40)
        self._brand.setMinimumWidth(100)
        top_lay.addWidget(self._brand)
        self._refresh = QPushButton("Refresh")
        self._refresh.clicked.connect(self._refresh_clicked)
        top_lay.addWidget(self._refresh)
        layout.addWidget(top_bar)

        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(8, 6, 8, 0)
        cl.setSpacing(4)
        self._page_title = QLabel("Overview")
        self._page_title.setObjectName("pageTitle")
        cl.addWidget(self._page_title)

        self.stack = QStackedWidget()
        self._stack_index: dict[str, int] = {}
        for key, w in self.pages.items():
            self._stack_index[key] = self.stack.addWidget(w)
        cl.addWidget(self.stack, 1)
        layout.addWidget(content, 1)

        self.setCentralWidget(central)

        self.nav.currentRowChanged.connect(self._nav_row)
        self.home.navigate.connect(self.go)
        self.more.section_changed.connect(self._on_more_section)
        self.settings.changed.connect(self._on_settings_changed)

        self._led = StatusLed()
        self._blink = BlinkenDisk()
        self._health = QLabel("Native providers…")
        bar = QStatusBar()
        bar.addWidget(self._led)
        bar.addWidget(self._health, 1)
        bar.addPermanentWidget(self._blink)
        self.setStatusBar(bar)

        self._menu()
        self.engine.updated.connect(self._on_snap)
        self.engine.error.connect(self._on_err)
        self._display = QTimer(self)
        self._display.setTimerType(Qt.TimerType.PreciseTimer)
        self._display.setInterval(16)
        self._display.timeout.connect(self._tick_display)
        self._display.start()
        self.engine.start()
        self._apply_window_flags()
        self._apply_font()
        self._apply_display_timer()
        self._apply_theme()
        self.go("summary")

    def _menu(self) -> None:
        m = self.menuBar()
        f = m.addMenu("File")
        quit_a = QAction("Quit", self)
        quit_a.triggered.connect(self.close)
        f.addAction(quit_a)
        ed = m.addMenu("Edit")
        copy_a = QAction("Copy", self)
        copy_a.setShortcut("Ctrl+C")
        copy_a.triggered.connect(self._copy)
        ed.addAction(copy_a)
        find_a = QAction("Find", self)
        find_a.setShortcut("Ctrl+F")
        find_a.triggered.connect(self._find)
        ed.addAction(find_a)
        v = m.addMenu("View")
        for key, label in NAV:
            act = QAction(label, self)
            act.triggered.connect(lambda _=False, k=key: self.go(k))
            v.addAction(act)
        v.addSeparator()
        more_menu = v.addMenu("More")
        for key, label in MORE_NAV:
            if key in MORE_FLAG_MAP and not self.flags.enabled(MORE_FLAG_MAP[key]):
                continue
            act = QAction(label, self)
            act.triggered.connect(lambda _=False, k=key: self.go(k))
            more_menu.addAction(act)
        h = m.addMenu("Help")
        about = QAction("About", self)
        about.triggered.connect(
            lambda: QMessageBox.about(
                self,
                "H-Bomb",
                "H-Bomb Task Manager\nNative Qt. Linux user-mode. No browser shell.",
            )
        )
        h.addAction(about)

    def _copy(self) -> None:
        w = self._active_page()
        tree = getattr(w, "tree", None)
        if tree is not None and tree.currentItem():
            QApplication.clipboard().setText(tree.currentItem().text(0))

    def _find(self) -> None:
        w = self._active_page()
        filt = getattr(w, "filter", None)
        if filt is not None:
            filt.setFocus()
            filt.selectAll()

    def _icon(self, key: str):
        name = NAV_ICONS.get(key, "summary")
        return nav_icon(name, self._icon_color, 20)

    def _fill_nav(self) -> None:
        self.nav.blockSignals(True)
        self.nav.clear()
        self._nav_keys: list[str] = []
        flag_map = {
            "disk": "disk_space",
        }
        nav_font = QFont(self.font().family(), 11, QFont.Weight.Medium)
        fm = QFontMetrics(nav_font)
        icon_w = self.nav.iconSize().width()
        for key, label in NAV:
            if key in flag_map and not self.flags.enabled(flag_map[key]):
                continue
            item = QListWidgetItem(self._icon(key), label)
            pad = 28
            item.setSizeHint(QSize(fm.horizontalAdvance(label) + icon_w + pad, 38))
            item.setFont(nav_font)
            self.nav.addItem(item)
            self._nav_keys.append(key)
        self.nav.blockSignals(False)

    def _nav_row(self, row: int) -> None:
        if 0 <= row < len(self._nav_keys) and self._nav_keys[row]:
            self.go(self._nav_keys[row], from_list=True)

    def _on_more_section(self, key: str, label: str) -> None:
        self._current_key = key
        self._page_title.setText(label)

    def _active_page(self) -> QWidget | None:
        cur = self.stack.currentWidget()
        if cur is self.more:
            return self.more.current_page()
        return cur

    def go(self, key: str, from_list: bool = False) -> None:
        perf_tab = None
        if key in ("memory", "energy", "thermals", "storage", "network", "gpu"):
            perf_tab = key
            key = "performance"
        if key == "colors":
            key = "settings"
        more_key: str | None = None
        if key in MORE_KEYS:
            more_key = key
            key = "more"
        idx = self._stack_index.get(key)
        if idx is None:
            return
        self._current_key = more_key or key
        self.stack.setCurrentIndex(idx)
        if more_key:
            self.more.select(more_key)
            self._page_title.setText(TITLES.get(more_key, more_key))
        elif key == "more":
            mk = self.more.current_key()
            self._current_key = mk
            self._page_title.setText(TITLES.get(mk, "Extras"))
        else:
            self._page_title.setText(TITLES.get(key, key.title()))
        if perf_tab is not None:
            self.performance.select_tab(perf_tab)
        if not from_list:
            nav_key = "more" if more_key else key
            if nav_key in self._nav_keys:
                self.nav.blockSignals(True)
                self.nav.setCurrentRow(self._nav_keys.index(nav_key))
                self.nav.blockSignals(False)
        if self._snap:
            page = self.more.current_page() if more_key or key == "more" else self.stack.widget(idx)
            self._refresh_page(page, self._snap)

    def _ui_paint_interval(self) -> float:
        return {"slow": 0.5, "normal": 0.08, "fast": 0.04}.get(self.visual.update_speed, 0.08)

    def _apply_font(self) -> None:
        family = self.visual.app_font
        if family == "System Default":
            family = QApplication.font().family()
        f = QFont(family, QApplication.font().pointSize())
        QApplication.setFont(f)

    def _apply_window_flags(self) -> None:
        on = self.visual.always_on_top
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, on)
        self.show()

    def _apply_display_timer(self) -> None:
        if self.visual.high_freq_visuals:
            if not self._display.isActive():
                self._display.start(16)
        else:
            self._display.stop()

    def _on_settings_changed(self) -> None:
        self._apply_font()
        self._apply_window_flags()
        self._apply_display_timer()
        self._apply_theme()
        self._persist_settings()

    def _refresh_clicked(self) -> None:
        w = self._active_page()
        if w is not None and hasattr(w, "reload"):
            w.reload()
        if self._snap:
            self._refresh_page(w, self._snap)

    def _apply_theme(self) -> None:
        dark = QGuiApplication.palette().color(QGuiApplication.palette().ColorRole.Window).lightness() < 128
        theme = resolve_theme(self.visual, system_dark=dark)
        self._icon_color = theme.text
        apply_palette(self, theme, self.visual)
        row = self.nav.currentRow()
        key = self._current_key
        self._fill_nav()
        self.nav.blockSignals(True)
        if key in self._nav_keys:
            self.nav.setCurrentRow(self._nav_keys.index(key))
        elif 0 <= row < self.nav.count():
            self.nav.setCurrentRow(row)
        self.nav.blockSignals(False)
        self._refresh.setIcon(nav_icon("refresh", theme.text, 14))
        self._brand.set_palette(theme.accent, theme.panel)
        for w in self.pages.values():
            if hasattr(w, "apply_theme"):
                w.apply_theme(theme, self.visual)
        self.more.apply_theme(theme, self.visual)
        self.visual.disk_view = self.disk.current_view_id()

    def _refresh_page(self, page: QWidget | None, snap: Snapshot) -> None:
        if page is None:
            return
        inc = self.visual.include_self
        if page is self.home:
            self.home.update_snapshot(snap, inc)
        elif page is self.performance:
            self.performance.update_snapshot(snap)
        elif page is self.procs:
            self.procs.update_snapshot(snap, inc)
        elif page is self.power:
            self.power.update_snapshot(snap)

    def _tick_display(self) -> None:
        if not self.visual.high_freq_visuals:
            return
        dt = 1 / 60
        self.home.tick(dt)
        self._blink.tick(dt)
        cur = self.stack.currentWidget()
        if cur is not None and hasattr(cur, "tick"):
            cur.tick(dt)

    def _on_snap(self, snap: Snapshot) -> None:
        self._snap = snap
        now = time.monotonic()
        disk_max = max((d.read_bps + d.write_bps for d in snap.disk.devices), default=1.0)
        r = snap.disk.read_bps / max(disk_max, 1.0)
        w = snap.disk.write_bps / max(disk_max, 1.0)
        self._blink.set_activity(r, w)
        self._health.setText(health_label(snap))
        h = snap.health()
        if h == ProviderHealth.HEALTHY:
            self._led.set_color(resolve_theme(self.visual).cpu)
        elif h == ProviderHealth.DEGRADED:
            self._led.set_color(resolve_theme(self.visual).temp)
        else:
            self._led.set_color(resolve_theme(self.visual).danger)
        if now - self._last_ui_paint < self._ui_paint_interval():
            return
        self._last_ui_paint = now
        cur = self.stack.currentWidget()
        self.home.update_snapshot(snap, self.visual.include_self)
        if cur is self.procs:
            if now - self._last_proc_paint < 0.4:
                return
            self._last_proc_paint = now
        if cur is not self.home:
            active = self._active_page()
            if active is not None:
                self._refresh_page(active, snap)
        if cur is self.flight:
            self.flight.ingest(snap)

    def _on_err(self, msg: str) -> None:
        self._health.setText("Sampler error — see stderr")
        self._led.set_color(QColor("#ff5a5a"))
        print(msg)

    def _load_settings(self) -> None:
        s = QSettings("H-Bomb", "H-Bomb Task Manager")
        self.visual.include_self = s.value("include_self", False, bool)
        self.visual.appearance = str(s.value("appearance", "dark"))
        self.visual.color_mode = str(s.value("color_mode", "full"))
        self.visual.chrome = str(s.value("chrome", "baldurs"))
        raw_sat = float(s.value("saturation", 7 / 11))
        self.visual.saturation = raw_sat if raw_sat <= 1.0 else raw_sat / 11.0
        self.visual.bloom = s.value("bloom", True, bool)
        raw_disk_view = str(s.value("disk_view", "buckets"))
        if raw_disk_view in ("windirstat", "balls", "block"):
            raw_disk_view = "buckets"
        elif raw_disk_view == "treesize":
            raw_disk_view = "paths"
        self.visual.disk_view = raw_disk_view
        self.visual.app_font = str(s.value("app_font", "IBM Plex Sans"))
        self.visual.popout = str(s.value("popout", "off"))
        self.visual.high_freq_visuals = s.value("high_freq_visuals", True, bool)
        self.visual.color_keyed_graphs = s.value("color_keyed_graphs", True, bool)
        self.visual.compress_history = s.value("compress_history", True, bool)
        self.visual.history_multiplier = int(s.value("history_multiplier", 15))
        self.visual.pixels_per_update = int(s.value("pixels_per_update", 8))
        self.visual.update_speed = str(s.value("update_speed", "normal"))
        start_page = str(s.value("start_page", "summary"))
        if start_page == "colors":
            start_page = "settings"
        self.visual.start_page = start_page
        self.visual.show_in_reports = s.value("show_in_reports", False, bool)
        self.visual.always_on_top = s.value("always_on_top", False, bool)
        self.visual.brightness = float(s.value("brightness", 1.0))
        self.visual.contrast = float(s.value("contrast", 1.0))

    def _persist_settings(self) -> None:
        s = QSettings("H-Bomb", "H-Bomb Task Manager")
        s.setValue("include_self", self.visual.include_self)
        s.setValue("appearance", self.visual.appearance)
        s.setValue("color_mode", self.visual.color_mode)
        s.setValue("chrome", self.visual.chrome)
        s.setValue("saturation", self.visual.saturation)
        s.setValue("bloom", self.visual.bloom)
        s.setValue("disk_view", self.disk.current_view_id())
        s.setValue("app_font", self.visual.app_font)
        s.setValue("popout", self.visual.popout)
        s.setValue("high_freq_visuals", self.visual.high_freq_visuals)
        s.setValue("color_keyed_graphs", self.visual.color_keyed_graphs)
        s.setValue("compress_history", self.visual.compress_history)
        s.setValue("history_multiplier", self.visual.history_multiplier)
        s.setValue("pixels_per_update", self.visual.pixels_per_update)
        s.setValue("update_speed", self.visual.update_speed)
        s.setValue("start_page", self.visual.start_page)
        s.setValue("show_in_reports", self.visual.show_in_reports)
        s.setValue("always_on_top", self.visual.always_on_top)
        s.setValue("brightness", self.visual.brightness)
        s.setValue("contrast", self.visual.contrast)

    def closeEvent(self, ev) -> None:
        self._persist_settings()
        self.engine.stop()
        super().closeEvent(ev)
