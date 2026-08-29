from __future__ import annotations

from dataclasses import dataclass, replace
from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtCore import Qt


@dataclass(frozen=True)
class Theme:
    name: str
    bg: QColor
    panel: QColor
    text: QColor
    muted: QColor
    accent: QColor
    cpu: QColor
    mem: QColor
    gpu: QColor
    temp: QColor
    disk: QColor
    net: QColor
    danger: QColor
    grid: QColor
    phosphor: str | None = None  # green/amber/white or None
    chrome: str = "obsidian"


def _c(h: str) -> QColor:
    return QColor(h)


OBSIDIAN = Theme(
    name="Obsidian",
    bg=_c("#0a0c10"),
    panel=_c("#141820"),
    text=_c("#e8eaed"),
    muted=_c("#7d8490"),
    accent=_c("#3d8bfd"),
    cpu=_c("#3dff8a"),
    mem=_c("#b07cff"),
    gpu=_c("#4da3ff"),
    temp=_c("#ffb347"),
    disk=_c("#5dff9a"),
    net=_c("#5ad0ff"),
    danger=_c("#ff5a5a"),
    grid=_c("#232a36"),
    chrome="obsidian",
)

# Warm tavern hearth — Baldur's Gate parchment gold meets Witcher weathered leather.
HYGGELIG = Theme(
    name="Hygge",
    bg=_c("#1a1610"),
    panel=_c("#2a231a"),
    text=_c("#f0e4d0"),
    muted=_c("#a89478"),
    accent=_c("#d4a84b"),
    cpu=_c("#e8c468"),
    mem=_c("#b88898"),
    gpu=_c("#7a9e8e"),
    temp=_c("#d4844a"),
    disk=_c("#8aa67a"),
    net=_c("#c9a87a"),
    danger=_c("#c45c52"),
    grid=_c("#3d3428"),
    chrome="hyggelig",
)

WITCHER = Theme(
    name="Witcher",
    bg=_c("#18140f"),
    panel=_c("#2a2118"),
    text=_c("#ebe0cc"),
    muted=_c("#9a8870"),
    accent=_c("#c45c26"),
    cpu=_c("#d4a84b"),
    mem=_c("#9a7088"),
    gpu=_c("#6a9080"),
    temp=_c("#d07040"),
    disk=_c("#7a9468"),
    net=_c("#b89068"),
    danger=_c("#b84840"),
    grid=_c("#382e24"),
    chrome="witcher",
)

SWORD_COAST = Theme(
    name="Sword Coast",
    bg=_c("#1c1814"),
    panel=_c("#2c261e"),
    text=_c("#f3e6c8"),
    muted=_c("#9a8a70"),
    accent=_c("#c4a574"),
    cpu=_c("#c9b060"),
    mem=_c("#a07898"),
    gpu=_c("#789888"),
    temp=_c("#c87848"),
    disk=_c("#88a070"),
    net=_c("#c0a070"),
    danger=_c("#b85048"),
    grid=_c("#3a3228"),
    chrome="sword_coast",
)

# Temple stone, brass trim, arcane violet — classic CRPG inventory panes.
BALDURS = Theme(
    name="Baldur's Theme",
    bg=_c("#1a1418"),
    panel=_c("#2a2228"),
    text=_c("#f2e8d4"),
    muted=_c("#9a8878"),
    accent=_c("#d4af37"),
    cpu=_c("#e6c35c"),
    mem=_c("#9b7bb8"),
    gpu=_c("#6a8a9a"),
    temp=_c("#d4723a"),
    disk=_c("#6a8a5a"),
    net=_c("#e8c878"),
    danger=_c("#c43828"),
    grid=_c("#3a3028"),
    chrome="baldurs",
)

# Cool slate and river stone — muted, grounded, low glare.
GRAVEL = Theme(
    name="Gravel",
    bg=_c("#1c1e22"),
    panel=_c("#2a2e34"),
    text=_c("#e2e4e8"),
    muted=_c("#8a9098"),
    accent=_c("#9aa4b0"),
    cpu=_c("#7a9aaa"),
    mem=_c("#8a7a9a"),
    gpu=_c("#6a8494"),
    temp=_c("#a89078"),
    disk=_c("#7a9488"),
    net=_c("#88a0b0"),
    danger=_c("#b05858"),
    grid=_c("#3a4048"),
    chrome="gravel",
)

# Wool blankets, hearth glow, honey wood — soft and warm.
COZY_COTTAGE = Theme(
    name="Cozy Cottage",
    bg=_c("#1f1a16"),
    panel=_c("#2f2820"),
    text=_c("#f8f0e4"),
    muted=_c("#b8a898"),
    accent=_c("#e0a860"),
    cpu=_c("#e8c080"),
    mem=_c("#b8a0b8"),
    gpu=_c("#7a9890"),
    temp=_c("#e07848"),
    disk=_c("#98b080"),
    net=_c("#d8a8a0"),
    danger=_c("#c06058"),
    grid=_c("#423830"),
    chrome="cozy_cottage",
)

NIGHT_CITY = replace(
    OBSIDIAN,
    name="Night City",
    bg=_c("#0d0a12"),
    panel=_c("#1a1224"),
    accent=_c("#ff2bd6"),
    cpu=_c("#00f0ff"),
    mem=_c("#ff2bd6"),
    chrome="night_city",
)

BREEZE = replace(
    OBSIDIAN,
    name="Breeze",
    bg=_c("#1b1e20"),
    panel=_c("#2a2e32"),
    accent=_c("#3daee9"),
    chrome="breeze",
)

PARCHMENT = Theme(
    name="Parchment",
    bg=_c("#f4efe4"),
    panel=_c("#fffaf0"),
    text=_c("#2a241c"),
    muted=_c("#6a5f52"),
    accent=_c("#8b4513"),
    cpu=_c("#2e7d32"),
    mem=_c("#6a1b9a"),
    gpu=_c("#1565c0"),
    temp=_c("#e65100"),
    disk=_c("#00695c"),
    net=_c("#0277bd"),
    danger=_c("#b71c1c"),
    grid=_c("#d9cbb8"),
    chrome="parchment",
)

CHROMES = {
    "hyggelig": HYGGELIG,
    "baldurs": BALDURS,
    "gravel": GRAVEL,
    "cozy_cottage": COZY_COTTAGE,
    "witcher": WITCHER,
    "sword_coast": SWORD_COAST,
    "obsidian": OBSIDIAN,
    "night_city": NIGHT_CITY,
    "breeze": BREEZE,
    "parchment": PARCHMENT,
}

# (chrome id, label shown in Colors → Ambiance)
AMBIANCE_CHOICES: tuple[tuple[str, str], ...] = (
    ("baldurs", "Baldur's Theme"),
    ("hyggelig", "Hygge"),
    ("gravel", "Gravel"),
    ("cozy_cottage", "Cozy Cottage"),
    ("witcher", "Witcher"),
    ("sword_coast", "Sword Coast"),
    ("obsidian", "Obsidian"),
)


def ambiance_index(chrome_id: str) -> int:
    for i, (key, _label) in enumerate(AMBIANCE_CHOICES):
        if key == chrome_id:
            return i
    return 0


def ambiance_id(index: int) -> str:
    if 0 <= index < len(AMBIANCE_CHOICES):
        return AMBIANCE_CHOICES[index][0]
    return AMBIANCE_CHOICES[0][0]

PHOSPHOR = {
    "green": _c("#33ff66"),
    "amber": _c("#ffbf00"),
    "white": _c("#e8f0ff"),
    "blue": _c("#6cb6ff"),
}


@dataclass
class VisualState:
    appearance: str = "dark"  # follow / light / dark
    color_mode: str = "full"  # full / green / amber / white / blue / mono
    chrome: str = "baldurs"
    saturation: float = 1.0  # 0..11
    bloom: bool = True
    sickbay: bool = False
    include_self: bool = False
    disk_view: str = "buckets"
    app_font: str = "IBM Plex Sans"
    popout: str = "off"
    high_freq_visuals: bool = True
    color_keyed_graphs: bool = True
    compress_history: bool = True
    history_multiplier: int = 15
    pixels_per_update: int = 8
    update_speed: str = "normal"  # slow / normal / fast
    start_page: str = "summary"
    show_in_reports: bool = False
    always_on_top: bool = False
    brightness: float = 1.0
    contrast: float = 1.0


def apply_saturation(c: QColor, sat: float, mono: bool) -> QColor:
    h, s, v, a = c.getHsv()
    if mono:
        s = 0
    else:
        factor = sat if sat <= 1.0 else min(sat, 11.0) / 11.0
        s = min(255, int(s * max(0.15, factor)))
    out = QColor()
    out.setHsv(h, s, v, a)
    return out


def tone_color(c: QColor, brightness: float, contrast: float) -> QColor:
    def ch(v: int) -> int:
        x = v / 255.0
        x = (x - 0.5) * contrast + 0.5
        x *= brightness
        return int(min(255, max(0, round(x * 255))))

    return QColor(ch(c.red()), ch(c.green()), ch(c.blue()), c.alpha())


def apply_display_tone(theme: Theme, state: VisualState) -> Theme:
    b, c = state.brightness, state.contrast
    if abs(b - 1.0) < 0.01 and abs(c - 1.0) < 0.01:
        return theme
    return replace(
        theme,
        bg=tone_color(theme.bg, b, c),
        panel=tone_color(theme.panel, b, c),
        text=tone_color(theme.text, b, c),
        muted=tone_color(theme.muted, b, c),
        grid=tone_color(theme.grid, b, c),
        accent=tone_color(theme.accent, b, c),
        cpu=tone_color(theme.cpu, b, c),
        mem=tone_color(theme.mem, b, c),
        gpu=tone_color(theme.gpu, b, c),
        temp=tone_color(theme.temp, b, c),
        disk=tone_color(theme.disk, b, c),
        net=tone_color(theme.net, b, c),
        danger=tone_color(theme.danger, b, c),
    )


def resolve_theme(state: VisualState, system_dark: bool = True) -> Theme:
    chrome = CHROMES.get(state.chrome, BALDURS)
    light = state.appearance == "light" or (
        state.appearance == "follow" and not system_dark
    )
    if light:
        base = PARCHMENT if state.chrome == "parchment" else replace(
            chrome,
            bg=_c("#f2f4f8"),
            panel=_c("#ffffff"),
            text=_c("#1a1d21"),
            muted=_c("#5c6570"),
            grid=_c("#d8dee8"),
        )
    else:
        base = chrome
    mode = state.color_mode
    if mode in PHOSPHOR:
        p = PHOSPHOR[mode]
        return apply_display_tone(
            replace(
                base,
                accent=p,
                cpu=p,
                mem=p,
                gpu=p,
                temp=p,
                disk=p,
                net=p,
                phosphor=mode,
            ),
            state,
        )
    if mode == "mono":
        g = _c("#c8c8c8") if not light else _c("#333333")
        return apply_display_tone(
            replace(base, accent=g, cpu=g, mem=g, gpu=g, temp=g, disk=g, net=g, phosphor=None),
            state,
        )
    return apply_display_tone(base, state)


UI_FONT = "IBM Plex Sans"
MONO_FONT = "IBM Plex Mono"


def _hex(c: QColor) -> str:
    return c.name()


def _input_surface(theme: Theme, panel: QColor, bg: QColor) -> tuple[QColor, QColor]:
    """Pick input background + guaranteed-readable foreground."""
    surface = QColor(panel)
    # Slightly separate inputs from cards when panel is same as page bg.
    if surface.lightness() == bg.lightness():
        surface = QColor(
            min(255, surface.red() + 8),
            min(255, surface.green() + 8),
            min(255, surface.blue() + 8),
        ) if surface.lightness() < 128 else QColor(
            max(0, surface.red() - 6),
            max(0, surface.green() - 6),
            max(0, surface.blue() - 6),
        )
    light_surface = surface.lightness() > 140
    if light_surface:
        fg = theme.text if theme.text.lightness() < 128 else _c("#1a1d21")
    else:
        fg = theme.text if theme.text.lightness() > 128 else _c("#f0e4d0")
    return surface, fg


def stylesheet_for(theme: Theme, state: VisualState) -> str:
    mono = state.color_mode == "mono"
    bg = apply_saturation(theme.bg, state.saturation, mono)
    panel = apply_saturation(theme.panel, state.saturation, mono)
    text = theme.text
    muted = theme.muted
    accent = apply_saturation(theme.accent, state.saturation, mono)
    grid = apply_saturation(theme.grid, state.saturation, False)
    sel = QColor(accent)
    sel.setAlpha(90)
    select_bg = QColor(
        int(panel.red() * 0.72 + accent.red() * 0.28),
        int(panel.green() * 0.72 + accent.green() * 0.28),
        int(panel.blue() * 0.72 + accent.blue() * 0.28),
    )
    nav_hover = QColor(panel)
    nav_hover.setAlpha(220)
    input_bg, input_fg = _input_surface(theme, panel, bg)
    return f"""
    QWidget {{
        color: {_hex(text)};
        font-family: "{UI_FONT}";
        font-size: 10pt;
    }}
    QMainWindow, QStackedWidget, QSplitter {{
        background-color: {_hex(bg)};
    }}
    QSplitter::handle {{
        width: 1px;
        background: {_hex(grid)};
    }}
    QWidget#topNav {{
        background-color: {_hex(bg)};
        border-bottom: 1px solid {_hex(grid)};
    }}
    QWidget#sidebar {{
        background-color: {_hex(bg)};
        border-right: 1px solid {_hex(grid)};
    }}
    QListWidget#nav {{
        background-color: transparent;
        border: none;
        outline: none;
        padding: 2px 4px;
    }}
    QListWidget#nav::item {{
        padding: 6px 14px;
        border-radius: 8px;
        margin: 0 2px;
        color: {_hex(text)};
        font-size: 11pt;
        font-weight: 500;
        min-height: 24px;
    }}
    QListWidget#nav::item:selected {{
        background-color: {_hex(select_bg)};
        color: {_hex(text)};
        border-bottom: 3px solid {_hex(accent)};
    }}
    QListWidget#perfRail {{
        background-color: transparent;
        border: none;
        outline: none;
        padding: 4px 2px;
    }}
    QListWidget#perfRail::item {{
        background: transparent;
        border: none;
        padding: 0;
        margin: 2px 0;
    }}
    QListWidget#perfRail::item:selected {{
        background: transparent;
        border: none;
    }}
    QListWidget#nav::item:hover {{
        background-color: {_hex(nav_hover)};
    }}
    QLabel#pageTitle {{
        font-size: 22px;
        font-weight: 600;
        background: transparent;
    }}
    QLabel#muted {{
        color: {_hex(muted)};
        background: transparent;
    }}
    QFrame#card {{
        background-color: {_hex(panel)};
        border: 1px solid {_hex(grid)};
        border-radius: 10px;
    }}
    QFrame#settingsCard {{
        background-color: {_hex(panel)};
        border: 1px solid {_hex(grid)};
        border-radius: 10px;
    }}
    QWidget#colorsPanel {{
        background-color: {_hex(panel)};
        border: 1px solid {_hex(grid)};
        border-radius: 8px;
    }}
    QLabel#settingsHint {{
        color: {_hex(muted)};
        font-size: 9pt;
        background: transparent;
    }}
    QLabel#settingsSection {{
        font-size: 11pt;
        font-weight: 600;
        background: transparent;
    }}
    QPushButton {{
        background-color: {_hex(panel)};
        color: {_hex(text)};
        border: 1px solid {_hex(grid)};
        border-radius: 6px;
        padding: 4px 12px;
        min-height: 22px;
    }}
    QPushButton:hover {{
        border-color: {_hex(accent)};
    }}
    QPushButton:pressed {{
        background-color: {_hex(select_bg)};
    }}
    QPushButton:disabled {{
        color: {_hex(muted)};
    }}
    QToolButton {{
        background: transparent;
        border: none;
        border-radius: 4px;
        padding: 4px;
    }}
    QToolButton:hover {{
        background-color: {_hex(panel)};
    }}
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit {{
        background-color: {_hex(input_bg)};
        color: {_hex(input_fg)};
        border: 1px solid {_hex(grid)};
        border-radius: 6px;
        padding: 4px 8px;
        min-height: 22px;
        selection-background-color: {_hex(accent)};
        selection-color: {_hex(input_bg if input_bg.lightness() < 128 else _c('#1a1d21'))};
    }}
    QComboBox QAbstractItemView {{
        background-color: {_hex(input_bg)};
        color: {_hex(input_fg)};
        border: 1px solid {_hex(grid)};
        selection-background-color: {_hex(select_bg)};
        selection-color: {_hex(input_fg)};
        outline: none;
    }}
    QComboBox::drop-down {{
        border: none;
        width: 18px;
        background: transparent;
    }}
    QSpinBox::up-button, QSpinBox::down-button,
    QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
        background-color: {_hex(panel)};
        border: 1px solid {_hex(grid)};
        width: 16px;
    }}
    QSpinBox::up-button:hover, QSpinBox::down-button:hover,
    QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {{
        background-color: {_hex(select_bg)};
    }}
    QHeaderView::section {{
        background-color: {_hex(panel)};
        color: {_hex(muted)};
        border: none;
        border-bottom: 1px solid {_hex(grid)};
        padding: 4px 8px;
        font-weight: 500;
    }}
    QTableWidget, QTreeWidget, QTableView, QTreeView {{
        background-color: {_hex(bg)};
        alternate-background-color: {_hex(panel)};
        gridline-color: {_hex(grid)};
        border: 1px solid {_hex(grid)};
        border-radius: 4px;
        selection-background-color: {_hex(select_bg)};
        selection-color: {_hex(text)};
    }}
    QTableWidget::item, QTreeWidget::item {{
        padding: 2px 4px;
    }}
    QScrollBar:vertical {{
        background: {_hex(bg)};
        width: 10px;
        margin: 0;
        border: none;
    }}
    QScrollBar::handle:vertical {{
        background: {_hex(grid)};
        border-radius: 4px;
        min-height: 24px;
    }}
    QScrollBar:horizontal {{
        background: {_hex(bg)};
        height: 10px;
        margin: 0;
        border: none;
    }}
    QScrollBar::handle:horizontal {{
        background: {_hex(grid)};
        border-radius: 4px;
        min-width: 24px;
    }}
    QScrollBar::add-line, QScrollBar::sub-line {{
        width: 0;
        height: 0;
    }}
    QStatusBar {{
        background-color: {_hex(bg)};
        color: {_hex(muted)};
        border-top: 1px solid {_hex(grid)};
    }}
    QStatusBar QLabel {{
        background: transparent;
        color: {_hex(muted)};
    }}
    QMenuBar {{
        background-color: {_hex(bg)};
        color: {_hex(text)};
        border-bottom: 1px solid {_hex(grid)};
    }}
    QMenuBar::item:selected {{
        background-color: {_hex(panel)};
    }}
    QMenu {{
        background-color: {_hex(panel)};
        color: {_hex(text)};
        border: 1px solid {_hex(grid)};
    }}
    QMenu::item:selected {{
        background-color: {_hex(select_bg)};
    }}
    QGroupBox {{
        border: 1px solid {_hex(grid)};
        border-radius: 6px;
        margin-top: 12px;
        padding-top: 8px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 4px;
        color: {_hex(muted)};
    }}
    QCheckBox, QSlider, QFormLayout {{
        background: transparent;
    }}
    QTabWidget::pane {{
        border: 1px solid {_hex(grid)};
    }}
    """


def apply_palette(widget, theme: Theme, state: VisualState) -> None:
    pal = widget.palette()
    mono = state.color_mode == "mono"
    bg = apply_saturation(theme.bg, state.saturation, mono)
    panel = apply_saturation(theme.panel, state.saturation, mono)
    input_bg, input_fg = _input_surface(theme, panel, bg)
    text = theme.text
    pal.setColor(QPalette.ColorRole.Window, bg)
    pal.setColor(QPalette.ColorRole.Base, input_bg)
    pal.setColor(QPalette.ColorRole.Text, input_fg)
    pal.setColor(QPalette.ColorRole.WindowText, text)
    pal.setColor(QPalette.ColorRole.Button, theme.panel)
    pal.setColor(QPalette.ColorRole.ButtonText, text)
    pal.setColor(QPalette.ColorRole.Highlight, theme.accent)
    pal.setColor(
        QPalette.ColorRole.HighlightedText,
        input_bg if input_bg.lightness() < 128 else _c("#1a1d21"),
    )
    widget.setPalette(pal)
    widget.setFont(QFont(UI_FONT, 10))
    widget.setStyleSheet(stylesheet_for(theme, state))
