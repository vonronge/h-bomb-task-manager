arrives, minimizing CPU use."
        )
        hf_hint.setObjectName("settingsHint")
        hf_hint.setWordWrap(True)
        appear.body.addWidget(hf_hint)
        self.colors_panel = ColorsPanel(visual, popup=False, embedded=True)
        appear.body.addWidget(self.colors_panel)
        lay.addWidget(appear)

        graphs = _SettingsCard("Graphs & updates", "performance")
        self.speed = QComboBox()
        self.speed.addItems(["Slow — 1/sec", "Normal — 2/sec", "Fast — 4/sec"])
        speed_map = {"slow": 0, "normal": 1, "fast": 2}
        self.speed.setCurrentIndex(speed_map.get(visual.update_speed, 1))
        self.color_keyed = QCheckBox("Color keyed graphs")
        self.color_keyed.setChecked(visual.color_keyed_graphs)
        self.compress = QCheckBox("Compress older history")
        self.compress.setChecked(visual.compress_history)
        self.hist_mult = QSpinBox()
        self.hist_mult.setRange(1, 30)
        self.hist_mult.setSuffix("x")
        self.hist_mult.setValue(visual.history_multiplier)
        self.px_update = QSpinBox()
        self.px_update.setRange(1, 32)
        self.px_update.setValue(visual.pixels_per_update)
        graphs.body.addWidget(_SettingsRow("Real-time update speed", self.speed))
        graphs.body.addWidget(self.color_keyed)
        graphs.body.addWidget(self.compress)
        graphs.body.addWidget(
            _SettingsRow(
                "History multiplier",
                self.hist_mult,
                "Older time is compressed smoothly. At 15x, four equal-width regions contain "
                "1x, 2x, 4x, and 8x history; the live quarter tracks the grid 1:1.",
            )
        )
        graphs.body.addWidget(
            _SettingsRow(
                "Pixels per update",
                self.px_update,
                "Each data update advances the graph by this many pixels; motion is presented in "
                "whole-pixel steps between updates.",
            )
        )
        lay.addWidget(graphs)

        general = _SettingsCard("General", "settings")
        self.popout = QComboBox()
        self.popout.addItems(["Off", "On"])
        self.popout.setCurrentIndex(0 if visual.popout == "off" else 1)
        self.start_page = QComboBox()
        for _k, label in self._START_PAGES:
            self.start_page.addItem(label)
        for i, (k, _l) in enumerate(self._START_PAGES):
            if k == visual.start_page:
                self.start_page.setCurrentIndex(i)
                break
        self.show_reports = QCheckBox("Show Task Manager in reports")
        self.show_reports.setChecked(visual.show_in_reports)
        self.include_self = QCheckBox("Show H-Bomb in process lists")
        self.include_self.setChecked(visual.include_self)
        self.always_top = QCheckBox("Always on top")
        self.always_top.setChecked(visual.always_on_top)
        general.body.addWidget(_SettingsRow("Popout", self.popout))
        general.body.addWidget(_SettingsRow("Default start page", self.start_page))
        general.body.addWidget(self.include_self)
        general.body.addWidget(self.show_reports)
        general.body.addWidget(self.always_top)
        top_hint = QLabel(
            "Keeps the window above other applications. On Linux, some desktop environments "
            "may ignore this for tiled or fullscreen layouts."
        )
        top_hint.setObjectName("settingsHint")
        top_hint.setWordWrap(True)
        general.body.addWidget(top_hint)
        lay.addWidget(general)

        about = _SettingsCard("About", "sysinfo")
        about.body.addWidget(QLabel("H-Bomb Task Manager"))
        ver = QLabel("0.1.0 — Native Qt6")
        ver.setObjectName("muted")
        about.body.addWidget(ver)
        copy = QLabel("Copyright © 2026 H-Bomb Task Manager")
        copy.setObjectName("muted")
        about.body.addWidget(copy)
        lay.addWidget(about)
        lay.addStretch()
        scroll.setWidget(inner)
        root.addWidget(scroll)
        self._cards = (appear, graphs, general, about)

        for w in (
            self.theme_box,
            self.font_box,
            self.popout,
            self.speed,
            self.start_page,
        ):
            w.currentIndexChanged.connect(self._apply)
        for w in (self.high_freq, self.color_keyed, self.compress, self.show_reports, self.include_self, self.always_top):
            w.toggled.connect(self._apply)
        for w in (self.hist_mult, self.px_update):
            w.valueChanged.connect(self._apply)
        self.colors_panel.changed.connect(self._apply)

    def apply_theme(self, theme: Theme, visual: VisualState) -> None:
        for card in self._cards:
            card.apply_theme(theme)

    def _apply(self, *_a) -> None:
        appear_map = {0: "dark", 1: "light", 2: "follow"}
        self.visual.appearance = appear_map[self.theme_box.currentIndex()]
        self.visual.app_font = self.font_box.currentText()
        self.visual.popout = "off" if self.popout.currentIndex() == 0 else "on"
        self.visual.high_freq_visuals = self.high_freq.isChecked()
        self.visual.color_keyed_graphs = self.color_keyed.isChecked()
        self.visual.compress_history = self.compress.isChecked()
        self.visual.history_multiplier = self.hist_mult.value()
        self.visual.pixels_per_update = self.px_update.value()
        speed_map = {0: "slow", 1: "normal", 2: "fast"}
        self.visual.update_speed = speed_map[self.speed.currentIndex()]
        self.visual.start_page = self._START_PAGES[self.start_page.currentIndex()][0]
        self.visual.show_in_reports = self.show_reports.isChecked()
        self.visual.include_self = self.include_self.isChecked()
        self.visual.always_on_top = self.always_top.isChecked()
        self.changed.emit()


def make_inventory_pages() -> dict[str, QWidget]:
    def units():
        rows = []
        for u in list_user_units() + list_system_units_readonly():
            rows.append((u.name, u.desc