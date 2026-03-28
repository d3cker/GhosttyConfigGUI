"""
Main window for Ghostty Configuration GUI.
"""

import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import (
    QFont, QFontDatabase, QColor, QPalette, QIcon, QPainter, QPixmap, QAction,
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QComboBox, QCheckBox, QSpinBox, QDoubleSpinBox,
    QScrollArea, QFrame, QSplitter, QListWidget, QListWidgetItem,
    QGroupBox, QPushButton, QFileDialog, QColorDialog, QMessageBox,
    QSizePolicy, QTextEdit, QSlider, QToolButton, QStackedWidget,
    QAbstractItemView,
)

from .config_data import (
    CONFIG_OPTIONS, CATEGORIES, ConfigOption, OptType,
    get_options_by_category, DEFAULT_PALETTE, PALETTE_NAMES,
)
from .config_io import default_config_path, parse_config, write_config
from .themes import list_themes, load_theme, ThemeColors


# ── Font Resolution Helper ────────────────────────────────────────────────────

def _resolve_font(name: str) -> QFont:
    """Resolve a font name like 'Family Style' into a QFont with proper style.

    Qt needs family and style set separately. We check if the name matches
    a known 'family + style' combination by iterating known families.
    """
    if not name:
        return QFont("monospace")

    # First try exact family match (no style suffix)
    families = QFontDatabase.families()
    if name in families:
        return QFont(name)

    # Try to find a family that is a prefix of the name, with the rest being a style
    # Longer family matches first to avoid e.g. "Noto Sans" matching before "Noto Sans Mono"
    for fam in sorted(families, key=len, reverse=True):
        if name.startswith(fam) and len(name) > len(fam):
            style = name[len(fam):].strip()
            if style and style in QFontDatabase.styles(fam):
                font = QFont(fam)
                font.setStyleName(style)
                return font

    # Fallback: let Qt try to resolve it
    return QFont(name)


# ── Color Swatch Button ──────────────────────────────────────────────────────

class ColorButton(QPushButton):
    """A button that shows a color and opens a color picker on click."""
    color_changed = pyqtSignal(str)

    def __init__(self, color: str = "", parent=None):
        super().__init__(parent)
        self._color = color or ""
        self.setFixedSize(36, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(self._pick_color)
        self._update_style()

    @property
    def color(self) -> str:
        return self._color

    @color.setter
    def color(self, value: str):
        self._color = value
        self._update_style()

    def _update_style(self):
        if self._color:
            self.setStyleSheet(
                f"background-color: {self._color}; border: 1px solid #555; border-radius: 3px;"
            )
        else:
            self.setStyleSheet(
                "background-color: transparent; border: 1px dashed #666; border-radius: 3px;"
            )
        self.setToolTip(self._color or "(not set)")

    def _pick_color(self):
        initial = QColor(self._color) if self._color else QColor("#ffffff")
        color = QColorDialog.getColor(initial, self, "Choose Color",
                                      QColorDialog.ColorDialogOption.ShowAlphaChannel)
        if color.isValid():
            self._color = color.name()
            self._update_style()
            self.color_changed.emit(self._color)


# ── Option Editor Widget Factory ─────────────────────────────────────────────

class OptionEditor(QWidget):
    """Widget for editing a single config option.

    Tracks whether the user has explicitly changed the value (dirty flag).
    Shows defaults as initial/placeholder values but only marks dirty when
    the value comes from the loaded config or user interaction.
    """
    value_changed = pyqtSignal(str, str)  # (option_name, new_value)

    def __init__(self, option: ConfigOption, current_value: str = "",
                 from_config: bool = False, parent=None):
        super().__init__(parent)
        self.option = option
        # dirty = value was in the loaded config OR user explicitly changed it
        self._dirty = from_config and bool(current_value)
        self._inhibit_dirty = True  # suppress dirty during initial setup
        self._setup_ui(current_value)
        self._inhibit_dirty = False

    def _setup_ui(self, current_value: str):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)

        # Label
        label = QLabel(self.option.name)
        label.setFixedWidth(260)
        label.setToolTip(self.option.description)
        font = label.font()
        font.setFamily("monospace")
        font.setPointSize(9)
        label.setFont(font)
        if self.option.platform:
            label.setText(f"{self.option.name}  [{self.option.platform}]")
        layout.addWidget(label)

        opt = self.option
        # Resolve display value: use current_value if from config, else show default
        display = current_value if current_value else (opt.default or "")

        if opt.opt_type == OptType.BOOLEAN:
            self._editor = QCheckBox()
            self._editor.setChecked(display.lower() == "true")
            self._editor.stateChanged.connect(
                lambda _: self._mark_dirty_and_emit(
                    "true" if self._editor.isChecked() else "false")
            )
        elif opt.opt_type == OptType.ENUM:
            self._editor = QComboBox()
            self._editor.setMinimumWidth(180)
            if "" not in opt.enum_values:
                self._editor.addItem("(default)", "")
            for v in opt.enum_values:
                disp_text = v if v else "(default)"
                self._editor.addItem(disp_text, v)
            idx = self._editor.findData(display)
            if idx >= 0:
                self._editor.setCurrentIndex(idx)
            self._editor.currentIndexChanged.connect(
                lambda _: self._mark_dirty_and_emit(self._editor.currentData())
            )
        elif opt.opt_type == OptType.COLOR:
            w = QWidget()
            hl = QHBoxLayout(w)
            hl.setContentsMargins(0, 0, 0, 0)
            self._color_btn = ColorButton(display)
            self._color_edit = QLineEdit(display)
            self._color_edit.setPlaceholderText(opt.default or "#RRGGBB")
            self._color_edit.setMaximumWidth(120)
            self._color_btn.color_changed.connect(self._on_color_btn)
            self._color_edit.editingFinished.connect(self._on_color_text)
            hl.addWidget(self._color_btn)
            hl.addWidget(self._color_edit)
            hl.addStretch()
            self._editor = w
        elif opt.opt_type == OptType.FLOAT:
            self._editor = QDoubleSpinBox()
            self._editor.setMinimum(opt.min_val if opt.min_val is not None else -9999)
            self._editor.setMaximum(opt.max_val if opt.max_val is not None else 9999)
            self._editor.setSingleStep(0.1)
            self._editor.setDecimals(2)
            if display:
                try:
                    self._editor.setValue(float(display))
                except ValueError:
                    pass
            self._editor.valueChanged.connect(
                lambda v: self._mark_dirty_and_emit(str(v))
            )
        elif opt.opt_type == OptType.INTEGER:
            self._editor = QSpinBox()
            self._editor.setMinimum(int(opt.min_val) if opt.min_val is not None else -999999)
            self._editor.setMaximum(int(opt.max_val) if opt.max_val is not None else 999999)
            if display:
                try:
                    self._editor.setValue(int(display))
                except ValueError:
                    pass
            self._editor.valueChanged.connect(
                lambda v: self._mark_dirty_and_emit(str(v))
            )
        elif opt.opt_type == OptType.THEME:
            self._editor = QComboBox()
            self._editor.setEditable(True)
            self._editor.setMinimumWidth(300)
            self._editor.addItem("(none)")
            theme_names = list_themes()
            self._editor.addItems(theme_names)
            if current_value:
                idx = self._editor.findText(current_value, Qt.MatchFlag.MatchFixedString)
                if idx >= 0:
                    self._editor.setCurrentIndex(idx)
                else:
                    self._editor.setCurrentText(current_value)
            self._editor.currentTextChanged.connect(
                lambda t: self._mark_dirty_and_emit(t if t != "(none)" else "")
            )
        elif opt.opt_type == OptType.FONT:
            self._editor = QComboBox()
            self._editor.setEditable(True)
            self._editor.setMinimumWidth(250)
            self._editor.addItem("(default)")
            families = sorted(set(QFontDatabase.families()))
            for fam in families:
                self._editor.addItem(fam)
                styles = QFontDatabase.styles(fam)
                for style in sorted(styles):
                    if style not in ("Regular", "Normal"):
                        self._editor.addItem(f"{fam} {style}")
            if current_value:
                idx = self._editor.findText(current_value, Qt.MatchFlag.MatchFixedString)
                if idx >= 0:
                    self._editor.setCurrentIndex(idx)
                else:
                    self._editor.setCurrentText(current_value)
            self._editor.currentTextChanged.connect(
                lambda t: self._mark_dirty_and_emit(t if t != "(default)" else "")
            )
        elif opt.opt_type == OptType.PATH:
            w = QWidget()
            hl = QHBoxLayout(w)
            hl.setContentsMargins(0, 0, 0, 0)
            self._path_edit = QLineEdit(current_value)
            self._path_edit.setMinimumWidth(200)
            browse = QPushButton("Browse...")
            browse.setMinimumWidth(100)
            browse.clicked.connect(self._browse_path)
            self._path_edit.editingFinished.connect(
                lambda: self._mark_dirty_and_emit(self._path_edit.text())
            )
            hl.addWidget(self._path_edit)
            hl.addWidget(browse)
            self._editor = w
        elif opt.opt_type in (OptType.REPEATABLE_STRING, OptType.KEY_VALUE):
            self._editor = QLineEdit(current_value)
            self._editor.setMinimumWidth(300)
            self._editor.setPlaceholderText("(one value per entry; add more with + button)")
            self._editor.editingFinished.connect(
                lambda: self._mark_dirty_and_emit(self._editor.text())
            )
        else:
            # STRING, DURATION, INTEGER_OR_PAIR, PERCENTAGE_OR_INT, etc.
            self._editor = QLineEdit(current_value)
            self._editor.setMinimumWidth(200)
            placeholder = opt.default or ""
            if opt.opt_type == OptType.DURATION:
                placeholder = opt.default or "e.g. 750ms, 5s, 1m30s"
            elif opt.opt_type == OptType.PERCENTAGE_OR_INT:
                placeholder = opt.default or "e.g. 1, 20%"
            elif opt.opt_type == OptType.INTEGER_OR_PAIR:
                placeholder = opt.default or "e.g. 2 or 2,4"
            if placeholder and not current_value:
                self._editor.setPlaceholderText(placeholder)
            self._editor.editingFinished.connect(
                lambda: self._mark_dirty_and_emit(self._editor.text())
            )

        layout.addWidget(self._editor)

        # Description
        desc = QLabel(self.option.description)
        desc.setStyleSheet("color: #888; font-size: 11px;")
        desc.setWordWrap(True)
        desc.setMinimumWidth(150)
        layout.addWidget(desc, 1)

    def _mark_dirty_and_emit(self, value: str):
        if not self._inhibit_dirty:
            self._dirty = True
        self.value_changed.emit(self.option.name, value)

    def _emit(self, value: str):
        self.value_changed.emit(self.option.name, value)

    def _on_color_btn(self, color: str):
        self._color_edit.setText(color)
        self._dirty = True
        self._emit(color)

    def _on_color_text(self):
        text = self._color_edit.text().strip()
        if text and QColor(text).isValid():
            self._color_btn.color = text
        self._dirty = True
        self._emit(text)

    def _browse_path(self):
        path, _ = QFileDialog.getOpenFileName(self, f"Select file for {self.option.name}")
        if path:
            self._path_edit.setText(path)
            self._dirty = True
            self._emit(path)

    @property
    def is_dirty(self) -> bool:
        return self._dirty

    def get_value(self) -> str:
        opt = self.option
        if opt.opt_type == OptType.BOOLEAN:
            return "true" if self._editor.isChecked() else "false"
        elif opt.opt_type == OptType.ENUM:
            return self._editor.currentData() or ""
        elif opt.opt_type == OptType.COLOR:
            return self._color_edit.text().strip()
        elif opt.opt_type == OptType.FLOAT:
            return str(self._editor.value())
        elif opt.opt_type == OptType.INTEGER:
            return str(self._editor.value())
        elif opt.opt_type in (OptType.FONT, OptType.THEME):
            t = self._editor.currentText()
            return "" if t in ("(default)", "(none)") else t
        elif opt.opt_type == OptType.PATH:
            return self._path_edit.text().strip()
        else:
            return self._editor.text().strip()


# ── Font Preview Panel ────────────────────────────────────────────────────────

class FontPreviewPanel(QGroupBox):
    """Live font preview with sample text."""

    SAMPLE_TEXT = (
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ\n"
        "abcdefghijklmnopqrstuvwxyz\n"
        "0123456789 !@#$%^&*()-=+[]{}\n"
        "The quick brown fox jumps over the lazy dog.\n"
        ">>> import ghostty  # Python\n"
        "fn main() { println!(\"Hello, Ghostty!\"); }\n"
        "0O 1lI |  ()[]{}<>  ;:,.  '\"` ~-_=+"
    )

    def __init__(self, parent=None):
        super().__init__("Font Preview", parent)
        layout = QVBoxLayout(self)
        self._preview = QTextEdit()
        self._preview.setReadOnly(True)
        self._preview.setPlainText(self.SAMPLE_TEXT)
        self._preview.setMinimumHeight(200)
        layout.addWidget(self._preview)

        self._font_name = ""
        self._font_size = 13.0
        self._update_preview()

    def set_font(self, family: str, size: float = 0):
        if family:
            self._font_name = family
        if size > 0:
            self._font_size = size
        self._update_preview()

    def _update_preview(self):
        font = _resolve_font(self._font_name or "monospace")
        font.setPointSizeF(self._font_size)
        self._preview.setFont(font)


# ── Palette Preview Panel ────────────────────────────────────────────────────

class PalettePreviewPanel(QGroupBox):
    """Visual editor for the 16-color ANSI palette."""
    palette_changed = pyqtSignal(int, str)  # (index, color)

    def __init__(self, parent=None):
        super().__init__("Color Palette (ANSI 16)", parent)
        self._colors = dict(DEFAULT_PALETTE)
        self._dirty: set[int] = set()  # indices touched by user or loaded from config
        self._buttons: dict[int, ColorButton] = {}
        self._setup_ui()

    def _setup_ui(self):
        layout = QGridLayout(self)
        layout.setSpacing(4)

        # Normal colors row
        layout.addWidget(QLabel("Normal:"), 0, 0)
        for i in range(8):
            btn = ColorButton(self._colors[i])
            btn.setToolTip(f"{PALETTE_NAMES[i]} ({i})")
            btn.color_changed.connect(lambda c, idx=i: self._on_color_changed(idx, c))
            self._buttons[i] = btn
            layout.addWidget(btn, 0, i + 1)
            lbl = QLabel(PALETTE_NAMES[i])
            lbl.setStyleSheet("font-size: 9px; color: #888;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(lbl, 1, i + 1)

        # Bright colors row
        layout.addWidget(QLabel("Bright:"), 2, 0)
        for i in range(8):
            idx = i + 8
            btn = ColorButton(self._colors[idx])
            btn.setToolTip(f"{PALETTE_NAMES[idx]} ({idx})")
            btn.color_changed.connect(lambda c, ix=idx: self._on_color_changed(ix, c))
            self._buttons[idx] = btn
            layout.addWidget(btn, 2, i + 1)
            lbl = QLabel(PALETTE_NAMES[idx].replace("Bright ", "Br "))
            lbl.setStyleSheet("font-size: 9px; color: #888;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(lbl, 3, i + 1)

    def _on_color_changed(self, idx: int, color: str):
        self._colors[idx] = color
        self._dirty.add(idx)
        self.palette_changed.emit(idx, color)

    def set_color(self, idx: int, color: str, from_config: bool = False):
        self._colors[idx] = color
        if from_config:
            self._dirty.add(idx)
        if idx in self._buttons:
            self._buttons[idx].color = color

    def get_dirty_colors(self) -> dict[int, str]:
        """Return only palette entries that were loaded from config or changed by user."""
        return {idx: self._colors[idx] for idx in sorted(self._dirty)}

    def reset_dirty(self):
        self._dirty.clear()


# ── Terminal Preview Panel ────────────────────────────────────────────────────

class TerminalPreview(QFrame):
    """Simulated terminal preview showing colors, syntax highlighting, and palette."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.Box)
        self.setMinimumHeight(320)
        self._bg = "#282c34"
        self._fg = "#ffffff"
        self._cursor_color = "#ffffff"
        self._cursor_style = "block"
        self._selection_bg = ""
        self._selection_fg = ""
        self._palette = dict(DEFAULT_PALETTE)
        self._font_family = "monospace"
        self._font_size = 11.0
        self._opacity = 1.0
        self._theme_name = ""

    def set_colors(self, bg: str = "", fg: str = "", cursor: str = ""):
        if bg:
            self._bg = bg
        if fg:
            self._fg = fg
        if cursor:
            self._cursor_color = cursor
        self.update()

    def set_palette(self, palette: dict[int, str]):
        self._palette.update(palette)
        self.update()

    def set_selection(self, bg: str = "", fg: str = ""):
        if bg:
            self._selection_bg = bg
        if fg:
            self._selection_fg = fg
        self.update()

    def set_cursor_style(self, style: str):
        self._cursor_style = style
        self.update()

    def set_font(self, family: str = "", size: float = 0):
        if family:
            self._font_family = family
        if size > 0:
            self._font_size = size
        self.update()

    def set_opacity(self, opacity: float):
        self._opacity = max(0.0, min(1.0, opacity))
        self.update()

    def apply_theme(self, theme: ThemeColors):
        """Apply a full theme to the preview."""
        self._theme_name = theme.name
        self._bg = theme.background
        self._fg = theme.foreground
        if theme.cursor_color:
            self._cursor_color = theme.cursor_color
        if theme.selection_background:
            self._selection_bg = theme.selection_background
        if theme.selection_foreground:
            self._selection_fg = theme.selection_foreground
        self._palette.update(theme.palette)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()

        # Background
        bg = QColor(self._bg)
        bg.setAlphaF(self._opacity)
        p.fillRect(rect, bg)

        # Font
        font = QFont(self._font_family)
        font.setPointSizeF(self._font_size)
        p.setFont(font)
        fm = p.fontMetrics()
        line_h = fm.height() + 2
        char_w = fm.horizontalAdvance("M")

        x0 = 10
        y = 10 + fm.ascent()

        # Helper to get palette color with fallback
        def pc(idx: int) -> str:
            return self._palette.get(idx, DEFAULT_PALETTE.get(idx, self._fg))

        # ── Title bar ──
        if self._theme_name:
            p.setPen(QColor(pc(8)))  # bright black / comment color
            p.drawText(x0, y, f"Theme: {self._theme_name}")
            y += line_h

        # ── Shell prompt ──
        prompt = [
            (pc(10), "user"),  # bright green
            (self._fg, "@"),
            (pc(14), "ghostty"),  # bright cyan
            (self._fg, ":"),
            (pc(12), "~/projects"),  # bright blue
            (self._fg, "$ "),
        ]
        x = x0
        for color, text in prompt:
            p.setPen(QColor(color))
            p.drawText(x, y, text)
            x += fm.horizontalAdvance(text)

        # Command
        cmd = "cat example.py"
        p.setPen(QColor(self._fg))
        p.drawText(x, y, cmd)
        cursor_x = x + fm.horizontalAdvance(cmd)

        # Cursor
        cc = QColor(self._cursor_color)
        if self._cursor_style == "block":
            p.fillRect(cursor_x, y - fm.ascent(), char_w, fm.height(), cc)
        elif self._cursor_style == "bar":
            p.fillRect(cursor_x, y - fm.ascent(), 2, fm.height(), cc)
        elif self._cursor_style == "underline":
            p.fillRect(cursor_x, y + 2, char_w, 2, cc)
        elif self._cursor_style == "block_hollow":
            p.setPen(cc)
            p.drawRect(cursor_x, y - fm.ascent(), char_w, fm.height())

        y += line_h + 2

        # ── Python syntax-highlighted code ──
        code_lines = [
            # (color_idx_or_hex, text) tuples per line
            [(8, "#!/usr/bin/env python3")],
            [(5, "import"), (self._fg, " "), (6, "sys")],
            [],
            [(5, "def"), (self._fg, " "), (4, "greet"),
             (self._fg, "("), (3, "name"), (self._fg, "):")],
            [(self._fg, "    "), (5, "if"), (self._fg, " name "),
             (5, "is"), (self._fg, " "), (5, "None"), (self._fg, ":")],
            [(self._fg, "        name "), (self._fg, "= "),
             (2, "\"World\"")],
            [(self._fg, "    "), (5, "print"),
             (self._fg, "("), (2, "f\"Hello, "),
             (3, "{name}"), (2, "!\""), (self._fg, ")")],
            [],
            [(8, "# Main entry point")],
            [(5, "if"), (self._fg, " __name__ == "),
             (2, "\"__main__\""), (self._fg, ":")],
            [(self._fg, "    greet(sys.argv["),
             (1, "1"), (self._fg, "] "), (5, "if"),
             (self._fg, " "), (4, "len"),
             (self._fg, "(sys.argv) > "),
             (1, "1"), (self._fg, " "),
             (5, "else"), (self._fg, " "),
             (5, "None"), (self._fg, ")")],
        ]

        for parts in code_lines:
            if not parts:
                y += line_h
                continue
            x = x0
            for item in parts:
                color_ref, text = item
                if isinstance(color_ref, int):
                    p.setPen(QColor(pc(color_ref)))
                else:
                    p.setPen(QColor(color_ref))
                p.drawText(x, y, text)
                x += fm.horizontalAdvance(text)
            y += line_h

        y += 4

        # ── Selection preview ──
        if self._selection_bg:
            sel_text = " Selected Text "
            sel_w = fm.horizontalAdvance(sel_text)
            p.fillRect(x0, y - fm.ascent(), sel_w, fm.height(),
                       QColor(self._selection_bg))
            sel_fg = self._selection_fg or self._fg
            p.setPen(QColor(sel_fg))
            p.drawText(x0, y, sel_text)
            y += line_h + 2

        # ── Palette swatches ──
        y += 2
        swatch_w = max(16, (rect.width() - 2 * x0) // 8 - 4)
        swatch_h = 14
        for row in range(2):
            for col in range(8):
                idx = row * 8 + col
                sx = x0 + col * (swatch_w + 3)
                sy = y + row * (swatch_h + 3)
                p.fillRect(sx, sy, swatch_w, swatch_h,
                           QColor(pc(idx)))
                p.setPen(QColor("#555"))
                p.drawRect(sx, sy, swatch_w, swatch_h)

        p.end()


# ── Category Page ─────────────────────────────────────────────────────────────

class CategoryPage(QScrollArea):
    """Scrollable page for one category of options."""
    value_changed = pyqtSignal(str, str)

    def __init__(self, options: list[ConfigOption], values: dict[str, list[str]], parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(2)

        self._editors: dict[str, OptionEditor] = {}
        for opt in options:
            from_config = opt.name in values
            val = values[opt.name][0] if from_config else ""
            editor = OptionEditor(opt, val, from_config=from_config)
            editor.value_changed.connect(self.value_changed.emit)
            self._editors[opt.name] = editor
            layout.addWidget(editor)

        layout.addStretch()
        self.setWidget(container)

    def get_dirty_values(self) -> dict[str, str]:
        """Return only values the user explicitly changed or that came from config."""
        return {
            name: ed.get_value()
            for name, ed in self._editors.items()
            if ed.is_dirty
        }


# ── Search Bar ────────────────────────────────────────────────────────────────

class SearchBar(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Search options...")
        self.setClearButtonEnabled(True)


# ── Main Window ───────────────────────────────────────────────────────────────

class GhosttyConfigWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ghostty Configuration")
        self.resize(1280, 860)

        self._config_path = default_config_path()
        self._values: dict[str, list[str]] = {}
        self._modified = False

        self._setup_ui()
        self._setup_menu()
        self._load_config()

    # ── UI Setup ──────────────────────────────────────────────

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # Left panel: search + category list
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(8, 8, 4, 8)

        self._search = SearchBar()
        self._search.textChanged.connect(self._on_search)
        left_layout.addWidget(self._search)

        self._cat_list = QListWidget()
        self._cat_list.setMinimumWidth(170)
        for cat in CATEGORIES:
            item = QListWidgetItem(cat)
            item.setSizeHint(QSize(0, 32))
            self._cat_list.addItem(item)
        self._cat_list.currentRowChanged.connect(self._on_category_changed)
        left_layout.addWidget(self._cat_list)

        splitter.addWidget(left)

        # Status label in the window status bar (full width, never truncated)
        self._status = QLabel("")
        self._status.setStyleSheet("color: #888; font-size: 11px;")
        self.statusBar().addWidget(self._status, 1)

        # Middle: stacked pages
        self._pages = QStackedWidget()
        splitter.addWidget(self._pages)

        # Right: preview panel
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(4, 8, 8, 8)

        self._font_preview = FontPreviewPanel()
        right_layout.addWidget(self._font_preview)

        self._palette_preview = PalettePreviewPanel()
        self._palette_preview.palette_changed.connect(self._on_palette_preview_changed)
        right_layout.addWidget(self._palette_preview)

        self._terminal_preview = TerminalPreview()
        right_layout.addWidget(self._terminal_preview)

        right_layout.addStretch()
        splitter.addWidget(right)

        splitter.setSizes([195, 685, 400])

        # Build category pages
        self._category_pages: dict[str, CategoryPage] = {}
        options_by_cat = get_options_by_category()
        for cat in CATEGORIES:
            page = CategoryPage(options_by_cat[cat], self._values)
            page.value_changed.connect(self._on_value_changed)
            self._category_pages[cat] = page
            self._pages.addWidget(page)

        # Also build a search results page
        self._search_page = CategoryPage([], {})
        self._pages.addWidget(self._search_page)

        self._cat_list.setCurrentRow(0)

    def _setup_menu(self):
        menu = self.menuBar()
        file_menu = menu.addMenu("&File")

        open_action = QAction("&Open Config...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._open_config)
        file_menu.addAction(open_action)

        save_action = QAction("&Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self._save_config)
        file_menu.addAction(save_action)

        save_as_action = QAction("Save &As...", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self._save_config_as)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        reload_action = QAction("&Reload", self)
        reload_action.setShortcut("Ctrl+R")
        reload_action.triggered.connect(self._load_config)
        file_menu.addAction(reload_action)

        file_menu.addSeparator()

        quit_action = QAction("&Quit", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

    # ── Config I/O ────────────────────────────────────────────

    def _load_config(self):
        if self._config_path.exists():
            self._values = parse_config(self._config_path)
            self._status.setText(f"Loaded: {self._config_path}")
        else:
            self._values = {}
            self._status.setText(f"New config: {self._config_path}")

        # Remember which category was selected
        current_row = self._cat_list.currentRow()
        if current_row < 0:
            current_row = 0

        # Rebuild pages with loaded values
        options_by_cat = get_options_by_category()
        for i, cat in enumerate(CATEGORIES):
            old_page = self._category_pages[cat]
            page = CategoryPage(options_by_cat[cat], self._values)
            page.value_changed.connect(self._on_value_changed)
            self._pages.removeWidget(old_page)
            old_page.deleteLater()
            self._pages.insertWidget(i, page)
            self._category_pages[cat] = page

        self._apply_previews_from_config()
        self._modified = False
        self.setWindowTitle(f"Ghostty Configuration - {self._config_path}")

        # Restore category selection and ensure page is visible
        self._cat_list.setCurrentRow(current_row)
        self._pages.setCurrentIndex(current_row)

    def _save_config(self):
        all_values = self._collect_all_values()
        write_config(self._config_path, all_values, self._config_path)
        self._modified = False
        self._status.setText(f"Saved: {self._config_path}")

    def _save_config_as(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Ghostty Config As", str(self._config_path), "All Files (*)"
        )
        if path:
            self._config_path = Path(path)
            self._save_config()

    def _open_config(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Ghostty Config", str(self._config_path.parent), "All Files (*)"
        )
        if path:
            self._config_path = Path(path)
            self._load_config()

    def _collect_all_values(self) -> dict[str, list[str]]:
        """Collect only values that are dirty (user-changed or from loaded config)."""
        result: dict[str, list[str]] = {}
        for cat in CATEGORIES:
            page = self._category_pages[cat]
            for name, val in page.get_dirty_values().items():
                if not val or val == "(default)":
                    continue
                # Palette is managed by the palette preview panel, skip here
                if name == "palette":
                    continue
                opt = next((o for o in CONFIG_OPTIONS if o.name == name), None)
                if opt and opt.repeatable and name in self._values and len(self._values[name]) > 1:
                    vals = list(self._values[name])
                    vals[0] = val
                    result[name] = vals
                else:
                    result[name] = [val]

        # Build palette entries from dirty colors only (user-changed or from config).
        palette = self._palette_preview.get_dirty_colors()
        if palette:
            result["palette"] = [f"{idx}={color}" for idx, color in palette.items()]
        return result

    # ── Slot handlers ─────────────────────────────────────────

    def _on_category_changed(self, row: int):
        if 0 <= row < len(CATEGORIES):
            self._pages.setCurrentIndex(row)

    def _on_value_changed(self, name: str, value: str):
        self._modified = True

        # Update previews in real time
        if name == "theme":
            self._apply_theme_preview(value)
        elif name == "font-family":
            self._font_preview.set_font(value)
            self._terminal_preview.set_font(family=value)
        elif name == "font-size":
            try:
                self._font_preview.set_font("", float(value))
            except ValueError:
                pass
        elif name == "background":
            self._terminal_preview.set_colors(bg=value)
        elif name == "foreground":
            self._terminal_preview.set_colors(fg=value)
        elif name == "cursor-color":
            self._terminal_preview.set_colors(cursor=value)
        elif name == "cursor-style":
            self._terminal_preview.set_cursor_style(value)
        elif name == "background-opacity":
            try:
                self._terminal_preview.set_opacity(float(value))
            except ValueError:
                pass

    def _on_palette_preview_changed(self, idx: int, color: str):
        self._modified = True
        self._terminal_preview.set_palette({idx: color})

    def _apply_theme_preview(self, theme_name: str):
        """Load and apply a theme to all preview panels (visual only, not saved)."""
        if not theme_name:
            return
        theme = load_theme(theme_name)
        if not theme:
            return
        self._terminal_preview.apply_theme(theme)
        # Update palette preview swatches for display only - theme name is
        # what gets saved, not the individual palette colors.
        for idx, color in theme.palette.items():
            self._palette_preview.set_color(idx, color, from_config=False)

    def _apply_previews_from_config(self):
        v = self._values
        # Reset palette dirty state before applying config
        self._palette_preview.reset_dirty()
        # Apply theme first (individual colors override after)
        if "theme" in v:
            self._apply_theme_preview(v["theme"][0])
        if "font-family" in v:
            self._font_preview.set_font(v["font-family"][0])
            self._terminal_preview.set_font(family=v["font-family"][0])
        if "font-size" in v:
            try:
                self._font_preview.set_font("", float(v["font-size"][0]))
            except ValueError:
                pass
        if "background" in v:
            self._terminal_preview.set_colors(bg=v["background"][0])
        if "foreground" in v:
            self._terminal_preview.set_colors(fg=v["foreground"][0])
        if "cursor-color" in v:
            self._terminal_preview.set_colors(cursor=v["cursor-color"][0])
        if "cursor-style" in v:
            self._terminal_preview.set_cursor_style(v["cursor-style"][0])
        if "background-opacity" in v:
            try:
                self._terminal_preview.set_opacity(float(v["background-opacity"][0]))
            except ValueError:
                pass
        # Load palette colors (override theme palette if set)
        if "palette" in v:
            for entry in v["palette"]:
                if "=" in entry:
                    idx_s, _, color = entry.partition("=")
                    try:
                        idx = int(idx_s)
                        self._palette_preview.set_color(idx, color, from_config=True)
                        self._terminal_preview.set_palette({idx: color})
                    except ValueError:
                        pass

    def _on_search(self, text: str):
        text = text.strip().lower()
        if not text:
            # Restore to category view
            row = self._cat_list.currentRow()
            if row >= 0:
                self._pages.setCurrentIndex(row)
            return

        # Filter options matching search
        matching = [
            opt for opt in CONFIG_OPTIONS
            if text in opt.name.lower() or text in opt.description.lower()
               or text in opt.category.lower()
        ]

        # Replace search page
        old = self._search_page
        self._pages.removeWidget(old)
        old.deleteLater()

        self._search_page = CategoryPage(matching, self._values)
        self._search_page.value_changed.connect(self._on_value_changed)
        search_idx = self._pages.addWidget(self._search_page)
        self._pages.setCurrentIndex(search_idx)

    def closeEvent(self, event):
        if self._modified:
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "You have unsaved changes. Save before closing?",
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel,
            )
            if reply == QMessageBox.StandardButton.Save:
                self._save_config()
                event.accept()
            elif reply == QMessageBox.StandardButton.Discard:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


def main():
    app = QApplication(sys.argv)

    # Dark fusion style
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(43, 43, 43))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(210, 210, 210))
    palette.setColor(QPalette.ColorRole.Base, QColor(35, 35, 35))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(50, 50, 50))
    palette.setColor(QPalette.ColorRole.Text, QColor(210, 210, 210))
    palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(210, 210, 210))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(75, 110, 175))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(50, 50, 50))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(210, 210, 210))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(120, 120, 120))
    app.setPalette(palette)

    app.setStyleSheet("""
        QMainWindow { background: #2b2b2b; }
        QGroupBox {
            font-weight: bold;
            border: 1px solid #555;
            border-radius: 4px;
            margin-top: 8px;
            padding-top: 12px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 4px;
        }
        QListWidget {
            border: 1px solid #444;
            border-radius: 4px;
            padding: 4px;
            outline: none;
        }
        QListWidget::item {
            padding: 4px 8px;
            border-radius: 3px;
        }
        QListWidget::item:selected {
            background: #4b6eaf;
        }
        QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
            padding: 3px 6px;
            border: 1px solid #555;
            border-radius: 3px;
            background: #333;
        }
        QScrollArea { border: none; }
        QPushButton {
            padding: 5px 14px;
            border: 1px solid #555;
            border-radius: 3px;
            background: #404040;
            min-height: 22px;
        }
        QPushButton:hover { background: #505050; }
        QTextEdit {
            border: 1px solid #555;
            border-radius: 4px;
            background: #1e1e1e;
            color: #d4d4d4;
        }
    """)

    window = GhosttyConfigWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
