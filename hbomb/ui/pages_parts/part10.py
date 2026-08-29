QSlider(Qt.Orientation.Horizontal)
        self.sat.setRange(0, 11)
        self.sat.setValue(int(round(visual.saturation * 11)))
        self._sat_lbl = QLabel(f"{self.sat.value()} / 11")
        sat_row = QHBoxLayout()
        sat_row.addWidget(self.sat, 1)
        sat_row.addWidget(self._sat_lbl)
        self.bloom = QCheckBox("Visual bloom")
        self.bloom.setChecked(visual.bloom)
        self.brightness = QSlider(Qt.Orientation.Horizontal)
        self.brightness.setRange(50, 150)
        self.brightness.setValue(int(round(visual.brightness * 100)))
        self._bright_lbl = QLabel(f"{self.brightness.value()}%")
        bright_row = QHBoxLayout()
        bright_row.addWidget(self.brightness, 1)
        bright_row.addWidget(self._bright_lbl)
        self.contrast = QSlider(Qt.Orientation.Horizontal)
        self.contrast.setRange(50, 150)
        self.contrast.setValue(int(round(visual.contrast * 100)))
        self._contrast_lbl = QLabel(f"{self.contrast.value()}%")
        contrast_row = QHBoxLayout()
        contrast_row.addWidget(self.contrast, 1)
        contrast_row.addWidget(self._contrast_lbl)
        lay.addWidget(_SettingsRow("Display", self.display))
        lay.addWidget(_SettingsRow("Ambiance", self.ambiance))
        lay.addLayout(sat_row)
        lay.addWidget(QLabel("Saturation"))
        lay.addWidget(QLabel("Brightness"))
        lay.addLayout(bright_row)
        lay.addWidget(QLabel("Contrast"))
        lay.addLayout(contrast_row)
        lay.addWidget(self.bloom)
        self.display.currentIndexChanged.connect(self._apply)
        self.ambiance.currentIndexChanged.connect(self._apply)
        self.sat.valueChanged.connect(self._on_sat)
        self.brightness.valueChanged.connect(self._on_brightness)
        self.contrast.valueChanged.connect(self._on_contrast)
        self.bloom.toggled.connect(self._apply)

    def _on_brightness(self, v: int) -> None:
        self._bright_lbl.setText(f"{v}%")
        self._apply()

    def _on_contrast(self, v: int) -> None:
        self._contrast_lbl.setText(f"{v}%")
        self._apply()

    def _on_sat(self, v: int) -> None:
        self._sat_lbl.setText(f"{v} / 11")
        self._apply()

    def sync_from_visual(self) -> None:
        mode_map = {"full": 0, "green": 1, "amber": 2, "white": 3, "blue": 4, "mono": 5}
        self.display.blockSignals(True)
        self.display.setCurrentIndex(mode_map.get(self.visual.color_mode, 0))
        self.display.blockSignals(False)
        self.ambiance.blockSignals(True)
        self.ambiance.setCurrentIndex(ambiance_index(self.visual.chrome))
        self.ambiance.blockSignals(False)
        self.sat.blockSignals(True)
        self.sat.setValue(int(round(self.visual.saturation * 11)))
        self.sat.blockSignals(False)
        self._sat_lbl.setText(f"{self.sat.value()} / 11")
        self.brightness.blockSignals(True)
        self.brightness.setValue(int(round(self.visual.brightness * 100)))
        self.brightness.blockSignals(False)
        self._bright_lbl.setText(f"{self.brightness.value()}%")
        self.contrast.blockSignals(True)
        self.contrast.setValue(int(round(self.visual.contrast * 100)))
        self.contrast.blockSignals(False)
        self._contrast_lbl.setText(f"{self.contrast.value()}%")
        self.bloom.setChecked(self.visual.bloom)

    def _apply(self, *_a) -> None:
        modes = ["full", "green", "amber", "white", "blue", "mono"]
        self.visual.color_mode = modes[self.display.currentIndex()]
        self.visual.chrome = ambiance_id(self.ambiance.currentIndex())
        self.visual.saturation = self.sat.value() / 11.0
        self.visual.brightness = self.brightness.value() / 100.0
        self.visual.contrast = self.contrast.value() / 100.0
        self.visual.bloom = self.bloom.isChecked()
        self.changed.emit()


class ColorsPage(QWidget):
    """Deprecated — colors live in SettingsPage. Kept for compatibility."""

    changed = Signal()

    def __init__(self, visual: VisualState, parent=None) -> None:
        super().__init__(parent)
        self.panel = ColorsPanel(visual, popup=False, embedded=True)
        self.panel.changed.connect(self.changed.emit)


class SettingsPage(QWidget):
    changed = Signal()

    _START_PAGES = [
        ("summary", "Overview"),
        ("performance", "Performance"),
        ("processes", "Running Apps"),
        ("sysinfo", "Hardware"),
        ("power", "Power & Clocks"),
        ("benchmarks", "Speed Tests"),
    ]

    def __init__(self, visual: VisualState, flags: FeatureFlags, parent=None) -> None:
        super().__init__(parent)
        self.visual = visual
        self.flags = flags
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(8, 4, 8, 12)
        lay.setSpacing(12)

        appear = _SettingsCard("Appearance", "colors")
        self.theme_box = QComboBox()
        self.theme_box.addItems(["Dark", "Light", "Follow system"])
        appear_map = {"dark": 0, "light": 1, "follow": 2}
        self.theme_box.setCurrentIndex(appear_map.get(visual.appearance, 0))
        self.font_box = QComboBox()
        self.font_box.addItems(["IBM Plex Sans", "Selawik", "Noto Sans", "System Default"])
        idx = max(0, self.font_box.findText(visual.app_font))
        self.font_box.setCurrentIndex(idx)
        self.high_freq = QCheckBox("High frequency visuals")
        self.high_freq.setChecked(visual.high_freq_visuals)
        appear.body.addWidget(_SettingsRow("App theme", self.theme_box))
        appear.body.addWidget(_SettingsRow("Application font", self.font_box))
        appear.body.addWidget(self.high_freq)
        hf_hint = QLabel(
            "Smooth graph motion and gauge needles between data updates. Turn off to redraw only "
            "when new data 