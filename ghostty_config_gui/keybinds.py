"""
Keybind editor: press a key combo to record the trigger, then pick the action
from a searchable list.

Ghostty keybind syntax:  keybind = [prefix:]trigger=action[:param]
  - trigger: '+'-separated modifiers and a key, e.g. ctrl+shift+c
  - sequences (leader keys) are joined with '>', e.g. ctrl+a>n
  - prefixes: global:, all:, unconsumed:, performable:
"""

import html
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, QEvent, pyqtSignal
from PyQt6.QtGui import QFontDatabase, QKeyEvent, QKeySequence, QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, QComboBox, QPushButton,
    QToolButton, QFrame, QCompleter, QMenu, QCheckBox, QSizePolicy,
)

IS_MAC = sys.platform == "darwin"
PREFIXES = ("global", "all", "unconsumed", "performable")
PREFIX_HELP = {
    "global": "System-wide: works even when Ghostty isn't focused (macOS needs Accessibility permission)",
    "all": "Apply to all terminal surfaces, not just the focused one",
    "unconsumed": "Run the action but still send the key to the program",
    "performable": "Only consume the key if the action can actually be performed",
}
DOC_URL = "https://ghostty.org/docs/config/keybind"


# ── Action catalog ────────────────────────────────────────────────────────────

@dataclass
class ActionInfo:
    name: str
    summary: str = ""
    doc: str = ""
    param: str = "none"   # none | optional | required
    values: list[str] = field(default_factory=list)
    hint: str = ""


@lru_cache(maxsize=1)
def load_actions() -> dict[str, ActionInfo]:
    path = Path(__file__).resolve().parent / "ghostty_actions.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return {a["name"]: ActionInfo(**a) for a in data.get("actions", [])}


def _find_ghostty() -> str | None:
    found = shutil.which("ghostty")
    if found:
        return found
    mac_app = "/Applications/Ghostty.app/Contents/MacOS/ghostty"
    return mac_app if Path(mac_app).exists() else None


@lru_cache(maxsize=1)
def load_default_keybinds() -> dict[str, str]:
    """Ghostty's built-in bindings for this platform: {normalized trigger: action}.

    Empty if the ghostty binary isn't available.
    """
    exe = _find_ghostty()
    if not exe:
        return {}
    try:
        out = subprocess.run([exe, "+list-keybinds", "--default", "--plain"],
                             capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return {}
    result: dict[str, str] = {}
    for line in out.splitlines():
        _, _, value = line.partition("=")
        trigger, action, param = split_keybind(value.strip())
        if trigger and action:
            result[normalize_trigger(trigger)] = join_action(action, param)
    return result


# ── Parsing helpers ───────────────────────────────────────────────────────────

def split_keybind(value: str) -> tuple[str, str, str]:
    """Split 'trigger=action:param' -> (trigger, action, param).

    Keys may themselves be '=' or '+' (e.g. 'super+==…', 'super++=…'), so this
    tokenizes: the first character of each key token is always part of the key,
    and only a later '=' ends the trigger.
    """
    s = value.strip()
    token_start = True
    for i, ch in enumerate(s):
        if token_start:
            token_start = False
        elif ch in "+>:/":
            token_start = True
        elif ch == "=":
            action, _, param = s[i + 1:].partition(":")
            return s[:i].strip(), action.strip(), param
    return s, "", ""


def join_action(action: str, param: str) -> str:
    return f"{action}:{param}" if param else action


def split_prefixes(trigger: str) -> tuple[list[str], str]:
    """'global:unconsumed:ctrl+a' -> (['global', 'unconsumed'], 'ctrl+a')."""
    prefixes: list[str] = []
    rest = trigger
    while True:
        head, sep, tail = rest.partition(":")
        if sep and head in PREFIXES:
            prefixes.append(head)
            rest = tail
        else:
            return prefixes, rest


_MOD_ALIASES = {
    "cmd": "super", "command": "super", "super": "super",
    "ctrl": "ctrl", "control": "ctrl",
    "alt": "alt", "opt": "alt", "option": "alt",
    "shift": "shift",
}
_KEY_ALIASES = {"=": "equal", "up": "arrow_up", "down": "arrow_down",
                "left": "arrow_left", "right": "arrow_right", "return": "enter"}


def normalize_trigger(trigger: str) -> str:
    """Canonical form for comparing triggers (ignores modifier order and aliases)."""
    prefixes, rest = split_prefixes(trigger.strip().lower())
    steps = []
    for step in rest.split(">"):
        # '+' as a key shows up as an empty part: 'super++' -> ['super', '', '']
        parts = step.split("+")
        key = parts[-1] if parts[-1] else "+"
        mods = sorted({_MOD_ALIASES.get(p, p) for p in parts[:-1] if p})
        if key.startswith("digit_"):
            key = key[len("digit_"):]
        elif key.startswith("key_") and len(key) == 5:
            key = key[-1]
        key = _KEY_ALIASES.get(key, key)
        steps.append("+".join(mods + [key]))
    return ":".join(sorted(prefixes) + [">".join(steps)])


# ── Key event → trigger ───────────────────────────────────────────────────────

_MODIFIER_KEYS = {
    Qt.Key.Key_Shift, Qt.Key.Key_Control, Qt.Key.Key_Meta, Qt.Key.Key_Alt,
    Qt.Key.Key_AltGr, Qt.Key.Key_CapsLock, Qt.Key.Key_Super_L, Qt.Key.Key_Super_R,
    Qt.Key.Key_Hyper_L, Qt.Key.Key_Hyper_R, Qt.Key.Key_NumLock,
}

_NAMED_KEYS = {
    Qt.Key.Key_Up: "arrow_up", Qt.Key.Key_Down: "arrow_down",
    Qt.Key.Key_Left: "arrow_left", Qt.Key.Key_Right: "arrow_right",
    Qt.Key.Key_PageUp: "page_up", Qt.Key.Key_PageDown: "page_down",
    Qt.Key.Key_Home: "home", Qt.Key.Key_End: "end",
    Qt.Key.Key_Insert: "insert", Qt.Key.Key_Delete: "delete",
    Qt.Key.Key_Backspace: "backspace", Qt.Key.Key_Return: "enter",
    Qt.Key.Key_Enter: "enter", Qt.Key.Key_Tab: "tab", Qt.Key.Key_Backtab: "tab",
    Qt.Key.Key_Escape: "escape", Qt.Key.Key_Space: "space",
    Qt.Key.Key_Print: "print_screen", Qt.Key.Key_ScrollLock: "scroll_lock",
    Qt.Key.Key_Pause: "pause", Qt.Key.Key_Menu: "context_menu",
    Qt.Key.Key_Equal: "equal",
}
_NAMED_KEYS.update({getattr(Qt.Key, f"Key_F{i}"): f"f{i}" for i in range(1, 26)})

_KEYPAD_KEYS = {
    Qt.Key.Key_Plus: "numpad_add", Qt.Key.Key_Minus: "numpad_subtract",
    Qt.Key.Key_Asterisk: "numpad_multiply", Qt.Key.Key_Slash: "numpad_divide",
    Qt.Key.Key_Period: "numpad_decimal", Qt.Key.Key_Comma: "numpad_separator",
    Qt.Key.Key_Enter: "numpad_enter", Qt.Key.Key_Equal: "numpad_equal",
}
_KEYPAD_KEYS.update({getattr(Qt.Key, f"Key_{i}"): f"numpad_{i}" for i in range(10)})

# Qt reports the shifted symbol (shift+1 -> '!'); Ghostty wants the base key
# with the shift modifier. US layout.
_UNSHIFT = dict(zip('!@#$%^&*()_+{}|:"<>?~', "1234567890-=[]\\;',./`"))


def modifier_names(mods: Qt.KeyboardModifier) -> list[str]:
    # Qt on macOS maps Command -> ControlModifier and Control -> MetaModifier.
    has_ctrl = bool(mods & Qt.KeyboardModifier.ControlModifier)
    has_meta = bool(mods & Qt.KeyboardModifier.MetaModifier)
    sup, ctrl = (has_ctrl, has_meta) if IS_MAC else (has_meta, has_ctrl)
    names = []
    if sup:
        names.append("super")
    if ctrl:
        names.append("ctrl")
    if mods & Qt.KeyboardModifier.AltModifier:
        names.append("alt")
    if mods & Qt.KeyboardModifier.ShiftModifier:
        names.append("shift")
    return names


def key_event_to_trigger(event: QKeyEvent) -> str | None:
    """Convert a key press to a Ghostty trigger step, or None for a bare modifier."""
    key = event.key()
    if key in _MODIFIER_KEYS or key == 0 or key == Qt.Key.Key_unknown:
        return None
    mods = event.modifiers()
    names = modifier_names(mods)

    keypad = bool(mods & Qt.KeyboardModifier.KeypadModifier)
    if keypad and key in _KEYPAD_KEYS:
        name = _KEYPAD_KEYS[key]
    elif key in _NAMED_KEYS:
        name = _NAMED_KEYS[key]
    else:
        if 0x20 < key < 0x7F:
            ch = chr(key).lower()
        else:
            text = event.text()
            if len(text) == 1 and text.isprintable() and not text.isspace():
                ch = text.lower()
            else:
                ch = QKeySequence(key).toString().lower() or f"0x{key:x}"
        if "shift" in names and ch in _UNSHIFT:
            ch = _UNSHIFT[ch]
        name = "equal" if ch == "=" else ch
    return "+".join(names + [name])


# ── Key capture field ────────────────────────────────────────────────────────

class KeyCaptureEdit(QLineEdit):
    """Line edit that records key presses as a Ghostty trigger while recording.

    Successive combos pressed within a short window become a sequence
    (ctrl+a>n). Outside recording mode it's a normal editable field.
    """
    recording_changed = pyqtSignal(bool)
    trigger_edited = pyqtSignal()

    SEQUENCE_TIMEOUT_MS = 1100

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self._recording = False
        self._steps: list[str] = []
        self._saved = ""
        self._prefixes: list[str] = []
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(self.SEQUENCE_TIMEOUT_MS)
        self._timer.timeout.connect(self.stop_recording)
        self.setPlaceholderText("click ⏺ and press keys")
        self.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self.editingFinished.connect(self._on_editing_finished)

    @property
    def recording(self) -> bool:
        return self._recording

    def start_recording(self):
        self._saved = self.text()
        self._prefixes, _ = split_prefixes(self._saved)
        self._steps = []
        self._recording = True
        self.setReadOnly(True)
        self.clear()
        self.setPlaceholderText("press a key combo…")
        self.setFocus(Qt.FocusReason.OtherFocusReason)
        self.recording_changed.emit(True)

    def stop_recording(self):
        if not self._recording:
            return
        self._recording = False
        self._timer.stop()
        self.setReadOnly(False)
        self.setPlaceholderText("click ⏺ and press keys")
        if self._steps:
            self.setText(self._compose())
        else:
            self.setText(self._saved)
        self.recording_changed.emit(False)
        if self.text() != self._saved:
            self.trigger_edited.emit()

    def _compose(self, pending: str = "") -> str:
        steps = self._steps + ([pending] if pending else [])
        return "".join(f"{p}:" for p in self._prefixes) + ">".join(steps)

    def event(self, e):
        if self._recording:
            # Swallow app shortcuts (Ctrl+S, Ctrl+Q, ...) and Tab focus handling.
            if e.type() == QEvent.Type.ShortcutOverride:
                e.accept()
                return True
            if e.type() == QEvent.Type.KeyPress:
                self.keyPressEvent(e)
                return True
        return super().event(e)

    def keyPressEvent(self, e: QKeyEvent):
        if not self._recording:
            return super().keyPressEvent(e)
        if e.isAutoRepeat():
            return
        step = key_event_to_trigger(e)
        if step is None:
            # Bare modifier: show live preview
            mods = modifier_names(e.modifiers())
            self.setText(self._compose("+".join(mods) + "+…" if mods else ""))
            return
        self._steps.append(step)
        self.setText(self._compose())
        self._timer.start()

    def keyReleaseEvent(self, e: QKeyEvent):
        if not self._recording:
            return super().keyReleaseEvent(e)
        if not self._timer.isActive():
            mods = modifier_names(e.modifiers())
            self.setText(self._compose("+".join(mods) + "+…" if mods else ""))

    def focusOutEvent(self, e):
        if self._recording:
            self.stop_recording()
        super().focusOutEvent(e)

    def _on_editing_finished(self):
        if not self._recording:
            self.trigger_edited.emit()


# ── Searchable action picker ─────────────────────────────────────────────────

_NAME_ROLE = Qt.ItemDataRole.UserRole + 1


class _ActionCompleter(QCompleter):
    """Matches against 'name — summary' but inserts only the action name."""

    def pathFromIndex(self, index):
        return index.data(_NAME_ROLE) or ""

    def splitPath(self, path):
        return [path]


def _doc_tooltip(info: ActionInfo) -> str:
    return (f'<p style="max-width:460px;"><b>{html.escape(info.name)}</b></p>'
            f'<p style="white-space:pre-wrap; max-width:460px;">{html.escape(info.doc)}</p>')


@lru_cache(maxsize=1)
def _action_model() -> QStandardItemModel:
    model = QStandardItemModel()
    for info in load_actions().values():
        item = QStandardItem(f"{info.name}  —  {info.summary}")
        item.setData(info.name, _NAME_ROLE)
        item.setToolTip(_doc_tooltip(info))
        model.appendRow(item)
    return model


class ActionPicker(QWidget):
    """Line edit with a filter-as-you-type popup of all Ghostty actions."""
    action_changed = pyqtSignal(str)

    def __init__(self, action: str = "", parent=None):
        super().__init__(parent)
        hl = QHBoxLayout(self)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(0)

        self._edit = QLineEdit(action)
        self._edit.setPlaceholderText("search actions…")
        self._edit.setMinimumWidth(150)
        self._edit.setClearButtonEnabled(True)

        self._completer = _ActionCompleter(_action_model(), self)
        self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self._completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self._completer.setMaxVisibleItems(14)
        self._completer.activated[str].connect(self._on_activated)
        self._edit.setCompleter(self._completer)
        popup = self._completer.popup()
        popup.setMinimumWidth(520)

        drop = QToolButton()
        drop.setText("▾")
        drop.setToolTip("Browse all actions")
        drop.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        drop.clicked.connect(self.show_all)

        hl.addWidget(self._edit, 1)
        hl.addWidget(drop)

        self._last = action
        self._edit.editingFinished.connect(self._commit)
        self._edit.textEdited.connect(lambda _: self._validate())
        self._validate()

    def action(self) -> str:
        return self._edit.text().strip()

    def setFocusToEdit(self):
        self._edit.setFocus()

    def show_all(self):
        self._edit.setFocus()
        self._completer.setCompletionPrefix(self._edit.text() if self.action() not in load_actions() else "")
        self._completer.complete()

    def _on_activated(self, text: str):
        # `text` is the path (action name) thanks to pathFromIndex
        self._edit.setText(text)
        self._commit()

    def _commit(self):
        self._validate()
        val = self.action()
        if val != self._last:
            self._last = val
            self.action_changed.emit(val)

    def _validate(self):
        val = self.action()
        info = load_actions().get(val)
        bad = bool(val) and info is None
        self._edit.setStyleSheet("border: 1px solid #b55;" if bad else "")
        self._edit.setToolTip(_doc_tooltip(info) if info else
                              ("Unknown action" if bad else "Type to search actions by name or description"))


# ── One keybind row ──────────────────────────────────────────────────────────

class KeybindRow(QFrame):
    changed = pyqtSignal()
    remove_requested = pyqtSignal(object)

    def __init__(self, value: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("keybindRow")
        self.setStyleSheet("#keybindRow { border-bottom: 1px solid #3a3a3a; }")
        trigger, action, param = split_keybind(value)

        vl = QVBoxLayout(self)
        vl.setContentsMargins(2, 4, 2, 4)
        vl.setSpacing(2)
        top = QHBoxLayout()
        top.setSpacing(4)
        vl.addLayout(top)

        # Prefix menu
        self._prefix_btn = QToolButton()
        self._prefix_btn.setText("⋯")
        self._prefix_btn.setToolTip("Trigger prefixes (global, all, unconsumed, performable)")
        self._prefix_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._prefix_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(self._prefix_btn)
        self._prefix_actions = {}
        for p in PREFIXES:
            act = menu.addAction(p)
            act.setCheckable(True)
            act.setToolTip(PREFIX_HELP[p])
            act.toggled.connect(lambda on, name=p: self._toggle_prefix(name, on))
            self._prefix_actions[p] = act
        menu.setToolTipsVisible(True)
        self._prefix_btn.setMenu(menu)
        menu.aboutToShow.connect(self._sync_prefix_menu)

        self.trigger_edit = KeyCaptureEdit(trigger)
        self.trigger_edit.setMinimumWidth(130)
        self.trigger_edit.trigger_edited.connect(self._on_changed)
        self.trigger_edit.recording_changed.connect(self._on_recording_changed)

        self._rec_btn = QToolButton()
        self._rec_btn.setText("⏺")
        self._rec_btn.setToolTip("Record a key combo (press several quickly for a sequence like ctrl+a>n)")
        self._rec_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._rec_btn.setCheckable(True)
        self._rec_btn.clicked.connect(self._toggle_recording)

        eq = QLabel("=")
        eq.setStyleSheet("color: #888; font-weight: bold;")

        self.action_picker = ActionPicker(action)
        self.action_picker.action_changed.connect(self._on_action_changed)

        self.param_combo = QComboBox()
        self.param_combo.setEditable(True)
        self.param_combo.setMinimumWidth(100)
        self.param_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.param_combo.lineEdit().editingFinished.connect(self._on_changed)
        self.param_combo.activated.connect(lambda _: self._on_changed())

        remove = QToolButton()
        remove.setText("✕")
        remove.setToolTip("Remove this binding")
        remove.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        remove.clicked.connect(lambda: self.remove_requested.emit(self))

        top.addWidget(self._prefix_btn)
        top.addWidget(self.trigger_edit, 3)
        top.addWidget(self._rec_btn)
        top.addWidget(eq)
        top.addWidget(self.action_picker, 4)
        top.addWidget(self.param_combo, 2)
        top.addWidget(remove)

        self._info = QLabel()
        self._info.setWordWrap(True)
        self._info.setStyleSheet("color: #888; font-size: 11px; padding-left: 30px;")
        vl.addWidget(self._info)

        self._status = ""   # set by the editor (duplicate / overrides default)
        self._populate_params(action, param)
        self._update_info()

    # values
    def trigger(self) -> str:
        return self.trigger_edit.text().strip()

    def action(self) -> str:
        return self.action_picker.action()

    def param(self) -> str:
        return self.param_combo.currentText().strip()

    def is_complete(self) -> bool:
        return bool(self.trigger()) and bool(self.action())

    def value(self) -> str:
        return f"{self.trigger()}={join_action(self.action(), self.param())}"

    def matches(self, text: str) -> bool:
        info = load_actions().get(self.action())
        hay = " ".join([self.trigger(), self.action(), self.param(),
                        info.summary if info else ""]).lower()
        return text in hay

    def start_recording(self):
        self._rec_btn.setChecked(True)
        self.trigger_edit.start_recording()

    def set_status(self, text: str, warn: bool = False):
        self._status = text
        self.trigger_edit.setStyleSheet("border: 1px solid #c9a227;" if warn else "")
        self._update_info()

    # internals
    def _toggle_recording(self, on: bool):
        if on:
            self.trigger_edit.start_recording()
        else:
            self.trigger_edit.stop_recording()

    def _on_recording_changed(self, on: bool):
        self._rec_btn.setChecked(on)
        self._rec_btn.setStyleSheet("color: #e05555;" if on else "")
        if not on and self.trigger() and not self.action():
            self.action_picker.setFocusToEdit()

    def _sync_prefix_menu(self):
        prefixes, _ = split_prefixes(self.trigger())
        for p, act in self._prefix_actions.items():
            act.blockSignals(True)
            act.setChecked(p in prefixes)
            act.blockSignals(False)

    def _toggle_prefix(self, name: str, on: bool):
        prefixes, rest = split_prefixes(self.trigger())
        if on and name not in prefixes:
            prefixes.append(name)
        elif not on and name in prefixes:
            prefixes.remove(name)
        prefixes = [p for p in PREFIXES if p in prefixes]
        self.trigger_edit.setText("".join(f"{p}:" for p in prefixes) + rest)
        self._on_changed()

    def _populate_params(self, action: str, param: str = "", autofill: bool = False):
        info = load_actions().get(action)
        self.param_combo.blockSignals(True)
        self.param_combo.clear()
        if info and info.param == "none" and not param:
            self.param_combo.setEnabled(False)
            self.param_combo.lineEdit().setPlaceholderText("no argument")
        else:
            self.param_combo.setEnabled(True)
            values = list(info.values) if info else []
            if info and info.param == "optional":
                values = [""] + values
            self.param_combo.addItems(values)
            hint = (info.hint if info else "") or ("argument" if info and info.param != "none" else "")
            self.param_combo.lineEdit().setPlaceholderText(hint or "argument")
            self.param_combo.setToolTip(hint)
            if param:
                self.param_combo.setCurrentText(param)
            elif autofill and info and info.param == "required" and info.values:
                self.param_combo.setCurrentIndex(0)
            else:
                self.param_combo.setCurrentText("")
        self.param_combo.blockSignals(False)

    def _on_action_changed(self, action: str):
        self._populate_params(action, autofill=True)
        self._on_changed()
        if self.param_combo.isEnabled() and not self.param():
            self.param_combo.setFocus()

    def _on_changed(self):
        self._update_info()
        self.changed.emit()

    def _update_info(self):
        info = load_actions().get(self.action())
        parts = []
        if info:
            parts.append(html.escape(info.summary))
            if info.param == "required" and not self.param():
                parts.append('<span style="color:#c9a227;">needs an argument</span>')
        if self._status:
            parts.append(self._status)
        self._info.setText("  ·  ".join(parts))
        self._info.setVisible(bool(parts))


# ── Whole editor ─────────────────────────────────────────────────────────────

class KeybindEditor(QWidget):
    """Editor for all `keybind` entries. Mirrors OptionEditor's dirty/get_value API."""
    value_changed = pyqtSignal(str, str)

    def __init__(self, values: list[str], from_config: bool = False, parent=None):
        super().__init__(parent)
        self._dirty = from_config and bool(values)
        self._rows: list[KeybindRow] = []
        self._defaults = load_default_keybinds()

        vl = QVBoxLayout(self)
        vl.setContentsMargins(0, 4, 0, 8)
        vl.setSpacing(6)

        title = QLabel(
            f'<a href="{DOC_URL}" style="color:#d2d2d2; text-decoration:none; '
            f'font-family:monospace; font-size:11pt;"><b>keybind</b></a>'
            f'&nbsp;&nbsp;<span style="color:#888;">Click ⏺ (or Add) and press a key combo, '
            f'then search for an action.</span>')
        title.setTextFormat(Qt.TextFormat.RichText)
        title.setOpenExternalLinks(True)
        title.setWordWrap(True)
        vl.addWidget(title)

        bar = QHBoxLayout()
        self._filter = QLineEdit()
        self._filter.setPlaceholderText("Filter bindings…")
        self._filter.setClearButtonEnabled(True)
        self._filter.textChanged.connect(self._apply_filter)
        bar.addWidget(self._filter, 1)

        self._clear_cb = QCheckBox("Clear Ghostty defaults")
        self._clear_cb.setToolTip("Write 'keybind = clear' first, removing all built-in bindings")
        self._clear_cb.toggled.connect(lambda _: self._on_row_changed())
        bar.addWidget(self._clear_cb)

        add = QPushButton("+ Add binding")
        add.clicked.connect(self._add_new)
        bar.addWidget(add)
        vl.addLayout(bar)

        self._rows_layout = QVBoxLayout()
        self._rows_layout.setSpacing(0)
        vl.addLayout(self._rows_layout)

        self._empty = QLabel("No custom keybinds yet.")
        self._empty.setStyleSheet("color: #777; padding: 8px;")
        vl.addWidget(self._empty)

        self._summary = QLabel()
        self._summary.setStyleSheet("color: #777; font-size: 11px;")
        vl.addWidget(self._summary)

        self._clear_cb.blockSignals(True)
        for v in values:
            if v.strip().lower() == "clear":
                self._clear_cb.setChecked(True)
            else:
                self._add_row(v)
        self._clear_cb.blockSignals(False)
        self._refresh_status()

    # public API (matches OptionEditor)
    @property
    def is_dirty(self) -> bool:
        return self._dirty

    def get_value(self) -> list[str]:
        vals = ["clear"] if self._clear_cb.isChecked() else []
        vals += [r.value() for r in self._rows if r.is_complete()]
        return vals

    # rows
    def _add_row(self, value: str = "") -> KeybindRow:
        row = KeybindRow(value)
        row.changed.connect(self._on_row_changed)
        row.remove_requested.connect(self._remove_row)
        self._rows.append(row)
        self._rows_layout.addWidget(row)
        return row

    def _add_new(self):
        self._filter.clear()
        row = self._add_row()
        self._refresh_status()
        row.start_recording()

    def _remove_row(self, row: KeybindRow):
        self._rows.remove(row)
        row.setParent(None)
        row.deleteLater()
        self._on_row_changed()

    def _on_row_changed(self):
        self._dirty = True
        self._refresh_status()
        self.value_changed.emit("keybind", "\n".join(self.get_value()))

    def _apply_filter(self, text: str):
        text = text.strip().lower()
        for r in self._rows:
            r.setVisible(not text or r.matches(text))

    def _refresh_status(self):
        self._empty.setVisible(not self._rows)
        counts: dict[str, int] = {}
        for r in self._rows:
            if r.trigger():
                n = normalize_trigger(r.trigger())
                counts[n] = counts.get(n, 0) + 1
        seen: dict[str, int] = {}
        for r in self._rows:
            if not r.trigger():
                r.set_status("")
                continue
            n = normalize_trigger(r.trigger())
            seen[n] = seen.get(n, 0) + 1
            if counts[n] > 1:
                msg = ("duplicate trigger — overridden by a later binding"
                       if seen[n] < counts[n] else "duplicate trigger — this one wins")
                r.set_status(f'<span style="color:#c9a227;">⚠ {msg}</span>', warn=True)
            elif n in self._defaults and not self._clear_cb.isChecked():
                default = self._defaults[n]
                if default == join_action(r.action(), r.param()):
                    r.set_status("same as Ghostty default")
                else:
                    r.set_status(f"overrides default: {html.escape(default)}")
            else:
                r.set_status("")
        incomplete = sum(1 for r in self._rows if not r.is_complete())
        text = f"{len(self._rows)} binding(s)"
        if incomplete:
            text += f" · {incomplete} incomplete (won't be saved)"
        if not self._defaults:
            text += " · Ghostty binary not found, so default-override hints are off"
        self._summary.setText(text)
        self._apply_filter(self._filter.text())
