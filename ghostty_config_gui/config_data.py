"""
Ghostty configuration options data model.
Every option has: name, type, category, default, description, and possible values.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class OptType(Enum):
    STRING = "string"
    BOOLEAN = "boolean"
    INTEGER = "integer"
    FLOAT = "float"
    COLOR = "color"
    ENUM = "enum"
    FONT = "font"
    PATH = "path"
    DURATION = "duration"
    KEY_VALUE = "key_value"
    REPEATABLE_STRING = "repeatable_string"
    INTEGER_OR_PAIR = "integer_or_pair"
    PERCENTAGE_OR_INT = "percentage_or_int"
    THEME = "theme"


@dataclass
class ConfigOption:
    name: str
    opt_type: OptType
    category: str
    default: Any = None
    description: str = ""
    enum_values: list[str] = field(default_factory=list)
    min_val: float | None = None
    max_val: float | None = None
    repeatable: bool = False
    platform: str = ""  # empty = all, "macos", "linux", "gtk"


CATEGORIES = [
    "Font",
    "Colors & Theme",
    "Cursor",
    "Window",
    "Tabs & Splits",
    "Mouse & Selection",
    "Keyboard",
    "Shell & Command",
    "Clipboard",
    "Scrollback",
    "Rendering",
    "Desktop Integration",
    "Quick Terminal",
    "macOS",
    "Linux & GTK",
]


CONFIG_OPTIONS: list[ConfigOption] = [
    # ── Font ──────────────────────────────────────────────────
    ConfigOption("font-family", OptType.FONT, "Font", "", "Primary font family", repeatable=True),
    ConfigOption("font-family-bold", OptType.FONT, "Font", "", "Bold font family (blank = derive from regular)", repeatable=True),
    ConfigOption("font-family-italic", OptType.FONT, "Font", "", "Italic font family (blank = derive from regular)", repeatable=True),
    ConfigOption("font-family-bold-italic", OptType.FONT, "Font", "", "Bold italic font family (blank = derive from regular)", repeatable=True),
    ConfigOption("font-style", OptType.STRING, "Font", "", "Named font style for regular weight (e.g. 'Heavy')"),
    ConfigOption("font-style-bold", OptType.STRING, "Font", "", "Named font style for bold (or 'false' to disable)"),
    ConfigOption("font-style-italic", OptType.STRING, "Font", "", "Named font style for italic (or 'false' to disable)"),
    ConfigOption("font-style-bold-italic", OptType.STRING, "Font", "", "Named font style for bold italic (or 'false' to disable)"),
    ConfigOption("font-size", OptType.FLOAT, "Font", "13", "Font size in points", min_val=1, max_val=200),
    ConfigOption("font-synthetic-style", OptType.ENUM, "Font", "true",
                 "Synthesize missing bold/italic styles",
                 enum_values=["true", "false", "no-bold", "no-italic", "no-bold-italic"]),
    ConfigOption("font-feature", OptType.REPEATABLE_STRING, "Font", "", "OpenType font features (e.g. -calt, liga=1)", repeatable=True),
    ConfigOption("font-variation", OptType.REPEATABLE_STRING, "Font", "", "Variable font axis values (e.g. wght=400)", repeatable=True),
    ConfigOption("font-variation-bold", OptType.REPEATABLE_STRING, "Font", "", "Variable font axis values for bold", repeatable=True),
    ConfigOption("font-variation-italic", OptType.REPEATABLE_STRING, "Font", "", "Variable font axis values for italic", repeatable=True),
    ConfigOption("font-variation-bold-italic", OptType.REPEATABLE_STRING, "Font", "", "Variable font axis values for bold italic", repeatable=True),
    ConfigOption("font-codepoint-map", OptType.REPEATABLE_STRING, "Font", "",
                 "Map Unicode codepoint ranges to specific fonts (e.g. U+E000-U+E100=NerdFont)", repeatable=True),
    ConfigOption("font-shaping-break", OptType.ENUM, "Font", "cursor",
                 "Where to break font shaping runs",
                 enum_values=["cursor", "no-cursor"]),
    ConfigOption("adjust-cell-width", OptType.PERCENTAGE_OR_INT, "Font", "", "Cell width adjustment (pixels or %)"),
    ConfigOption("adjust-cell-height", OptType.PERCENTAGE_OR_INT, "Font", "", "Cell height adjustment (pixels or %)"),
    ConfigOption("adjust-font-baseline", OptType.PERCENTAGE_OR_INT, "Font", "", "Font baseline adjustment (pixels or %)"),
    ConfigOption("adjust-underline-position", OptType.PERCENTAGE_OR_INT, "Font", "", "Underline position adjustment"),
    ConfigOption("adjust-underline-thickness", OptType.PERCENTAGE_OR_INT, "Font", "", "Underline thickness adjustment"),
    ConfigOption("adjust-strikethrough-position", OptType.PERCENTAGE_OR_INT, "Font", "", "Strikethrough position adjustment"),
    ConfigOption("adjust-strikethrough-thickness", OptType.PERCENTAGE_OR_INT, "Font", "", "Strikethrough thickness adjustment"),
    ConfigOption("adjust-overline-position", OptType.PERCENTAGE_OR_INT, "Font", "", "Overline position adjustment"),
    ConfigOption("adjust-overline-thickness", OptType.PERCENTAGE_OR_INT, "Font", "", "Overline thickness adjustment"),
    ConfigOption("adjust-cursor-thickness", OptType.PERCENTAGE_OR_INT, "Font", "", "Cursor bar thickness adjustment"),
    ConfigOption("adjust-cursor-height", OptType.PERCENTAGE_OR_INT, "Font", "", "Cursor height adjustment"),
    ConfigOption("adjust-box-thickness", OptType.PERCENTAGE_OR_INT, "Font", "", "Box-drawing thickness adjustment"),
    ConfigOption("adjust-icon-height", OptType.PERCENTAGE_OR_INT, "Font", "", "Nerd font icon max height adjustment"),
    ConfigOption("grapheme-width-method", OptType.ENUM, "Font", "unicode",
                 "Method for calculating grapheme cell width",
                 enum_values=["legacy", "unicode"]),
    ConfigOption("alpha-blending", OptType.ENUM, "Font", "native",
                 "Color space for alpha blending",
                 enum_values=["native", "linear", "linear-corrected"]),

    # ── Colors & Theme ────────────────────────────────────────
    ConfigOption("theme", OptType.THEME, "Colors & Theme", "", "Theme name or light:name,dark:name"),
    ConfigOption("background", OptType.COLOR, "Colors & Theme", "#282c34", "Background color"),
    ConfigOption("foreground", OptType.COLOR, "Colors & Theme", "#ffffff", "Foreground text color"),
    ConfigOption("selection-foreground", OptType.COLOR, "Colors & Theme", "", "Selected text foreground (blank = invert)"),
    ConfigOption("selection-background", OptType.COLOR, "Colors & Theme", "", "Selected text background (blank = invert)"),
    ConfigOption("minimum-contrast", OptType.FLOAT, "Colors & Theme", "1", "Minimum contrast ratio (1.0 - 21.0)", min_val=1.0, max_val=21.0),
    # Note: "palette" is not listed here - it is managed by the PalettePreviewPanel
    ConfigOption("palette-generate", OptType.BOOLEAN, "Colors & Theme", "false",
                 "Auto-generate extended palette from base 16 colors"),
    ConfigOption("palette-harmonious", OptType.BOOLEAN, "Colors & Theme", "false",
                 "Invert palette generation order"),
    ConfigOption("bold-is-bright", OptType.BOOLEAN, "Colors & Theme", "false",
                 "Interpret bold as bright in 16-color palette"),
    ConfigOption("bold-color", OptType.STRING, "Colors & Theme", "",
                 "Color for bold text (hex color or 'bright' to use bright palette)"),
    ConfigOption("faint-opacity", OptType.FLOAT, "Colors & Theme", "0.5",
                 "Opacity of faint/dim text (0.0 - 1.0)", min_val=0.0, max_val=1.0),
    ConfigOption("background-opacity", OptType.FLOAT, "Colors & Theme", "1", "Window background transparency (0.0 - 1.0)", min_val=0.0, max_val=1.0),
    ConfigOption("background-opacity-cells", OptType.BOOLEAN, "Colors & Theme", "false",
                 "Apply background opacity to cells with explicit colors"),
    ConfigOption("background-blur", OptType.STRING, "Colors & Theme", "false",
                 "Background blur (integer, true/false, or macOS glass style)"),
    ConfigOption("unfocused-split-opacity", OptType.FLOAT, "Colors & Theme", "0.7",
                 "Opacity of unfocused split panes (0.15 - 1.0)", min_val=0.15, max_val=1.0),
    ConfigOption("unfocused-split-fill", OptType.COLOR, "Colors & Theme", "",
                 "Color to dim unfocused splits (blank = background)"),
    ConfigOption("split-divider-color", OptType.COLOR, "Colors & Theme", "", "Split divider line color"),
    ConfigOption("search-foreground", OptType.COLOR, "Colors & Theme", "", "Search match text color"),
    ConfigOption("search-background", OptType.COLOR, "Colors & Theme", "", "Search match background color"),
    ConfigOption("search-selected-foreground", OptType.COLOR, "Colors & Theme", "", "Focused search match text color"),
    ConfigOption("search-selected-background", OptType.COLOR, "Colors & Theme", "", "Focused search match background color"),

    # ── Cursor ────────────────────────────────────────────────
    ConfigOption("cursor-color", OptType.COLOR, "Cursor", "", "Cursor color (blank = auto)"),
    ConfigOption("cursor-opacity", OptType.FLOAT, "Cursor", "1", "Cursor opacity (0.0 - 1.0)", min_val=0.0, max_val=1.0),
    ConfigOption("cursor-style", OptType.ENUM, "Cursor", "block",
                 "Cursor shape",
                 enum_values=["block", "bar", "underline", "block_hollow"]),
    ConfigOption("cursor-style-blink", OptType.ENUM, "Cursor", "",
                 "Cursor blink state (blank = terminal default)",
                 enum_values=["true", "false", ""]),
    ConfigOption("cursor-text", OptType.COLOR, "Cursor", "", "Text color under cursor (blank = auto)"),
    ConfigOption("cursor-click-to-move", OptType.BOOLEAN, "Cursor", "false",
                 "Click to move cursor at shell prompts (requires shell integration)"),

    # ── Window ────────────────────────────────────────────────
    ConfigOption("maximize", OptType.BOOLEAN, "Window", "false", "Start maximized"),
    ConfigOption("fullscreen", OptType.ENUM, "Window", "false",
                 "Fullscreen mode",
                 enum_values=["false", "true", "non-native", "non-native-visible-menu", "non-native-padded-notch"]),
    ConfigOption("title", OptType.STRING, "Window", "", "Fixed window title (blank = dynamic)"),
    ConfigOption("working-directory", OptType.STRING, "Window", "", "Initial working directory (path, 'home', or 'inherit')"),
    ConfigOption("window-padding-x", OptType.INTEGER_OR_PAIR, "Window", "2", "Horizontal padding in points (single value or left,right)"),
    ConfigOption("window-padding-y", OptType.INTEGER_OR_PAIR, "Window", "2", "Vertical padding in points (single value or top,bottom)"),
    ConfigOption("window-padding-balance", OptType.BOOLEAN, "Window", "false", "Balance padding on all edges"),
    ConfigOption("window-padding-color", OptType.ENUM, "Window", "background",
                 "Padding area color mode",
                 enum_values=["background", "extend", "extend-always"]),
    ConfigOption("window-vsync", OptType.BOOLEAN, "Window", "true", "VSync rendering"),
    ConfigOption("window-inherit-working-directory", OptType.BOOLEAN, "Window", "true", "New windows inherit working directory"),
    ConfigOption("window-inherit-font-size", OptType.BOOLEAN, "Window", "true", "New windows inherit font size"),
    ConfigOption("window-decoration", OptType.ENUM, "Window", "auto",
                 "Window decoration style",
                 enum_values=["none", "auto", "client", "server"]),
    ConfigOption("window-title-font-family", OptType.STRING, "Window", "", "Font for window/tab titles"),
    ConfigOption("window-theme", OptType.ENUM, "Window", "auto",
                 "Window UI theme",
                 enum_values=["auto", "system", "light", "dark", "ghostty"]),
    ConfigOption("window-height", OptType.INTEGER, "Window", "", "Initial height in grid cells", min_val=4, max_val=1000),
    ConfigOption("window-width", OptType.INTEGER, "Window", "", "Initial width in grid cells", min_val=10, max_val=1000),
    ConfigOption("window-new-tab-position", OptType.ENUM, "Window", "current",
                 "New tab position",
                 enum_values=["current", "end"]),
    ConfigOption("resize-overlay", OptType.ENUM, "Window", "after-first",
                 "Resize overlay display",
                 enum_values=["always", "never", "after-first"]),
    ConfigOption("resize-overlay-position", OptType.ENUM, "Window", "center",
                 "Resize overlay position",
                 enum_values=["center", "top-left", "top-center", "top-right",
                              "bottom-left", "bottom-center", "bottom-right"]),
    ConfigOption("resize-overlay-duration", OptType.DURATION, "Window", "750ms", "Resize overlay display duration"),
    ConfigOption("focus-follows-mouse", OptType.BOOLEAN, "Window", "false", "Mouse-follows-focus for splits"),

    # ── Tabs & Splits ─────────────────────────────────────────
    ConfigOption("tab-inherit-working-directory", OptType.BOOLEAN, "Tabs & Splits", "true", "New tabs inherit working directory"),
    ConfigOption("split-inherit-working-directory", OptType.BOOLEAN, "Tabs & Splits", "true", "New splits inherit working directory"),
    ConfigOption("split-preserve-zoom", OptType.ENUM, "Tabs & Splits", "",
                 "Preserve zoomed split during navigation",
                 enum_values=["", "navigation", "no-navigation"]),

    # ── Mouse & Selection ─────────────────────────────────────
    ConfigOption("mouse-hide-while-typing", OptType.BOOLEAN, "Mouse & Selection", "false", "Hide mouse cursor while typing"),
    ConfigOption("mouse-shift-capture", OptType.ENUM, "Mouse & Selection", "false",
                 "Shift+click behavior with mouse protocol",
                 enum_values=["true", "false", "always", "never"]),
    ConfigOption("mouse-reporting", OptType.BOOLEAN, "Mouse & Selection", "true", "Enable mouse event reporting to apps"),
    ConfigOption("mouse-scroll-multiplier", OptType.STRING, "Mouse & Selection", "precision:1,discrete:3",
                 "Scroll multiplier (precision:N, discrete:N)"),
    ConfigOption("selection-clear-on-typing", OptType.BOOLEAN, "Mouse & Selection", "true", "Clear selection when typing"),
    ConfigOption("selection-clear-on-copy", OptType.BOOLEAN, "Mouse & Selection", "false", "Clear selection after copy"),
    ConfigOption("selection-word-chars", OptType.STRING, "Mouse & Selection", "",
                 "Additional word boundary characters for double-click selection"),
    ConfigOption("copy-on-select", OptType.BOOLEAN, "Mouse & Selection", "false", "Copy text on selection"),
    ConfigOption("right-click-action", OptType.ENUM, "Mouse & Selection", "context-menu",
                 "Action on right-click",
                 enum_values=["context-menu", "paste", "none"]),
    ConfigOption("click-repeat-interval", OptType.INTEGER, "Mouse & Selection", "0",
                 "Time in ms between clicks for repeat detection (0 = platform default)", min_val=0),
    ConfigOption("scroll-to-bottom", OptType.STRING, "Mouse & Selection", "keystroke,no-output",
                 "When to scroll to bottom (keystroke, output, no-keystroke, no-output)"),

    # ── Keyboard ──────────────────────────────────────────────
    ConfigOption("keybind", OptType.REPEATABLE_STRING, "Keyboard", "",
                 "Key binding: trigger=action (e.g. ctrl+shift+c=copy_to_clipboard)", repeatable=True),
    ConfigOption("key-remap", OptType.REPEATABLE_STRING, "Keyboard", "",
                 "Remap modifier keys (e.g. left_alt=left_ctrl)", repeatable=True),

    # ── Shell & Command ───────────────────────────────────────
    ConfigOption("command", OptType.STRING, "Shell & Command", "", "Command to run (blank = default shell)"),
    ConfigOption("initial-command", OptType.STRING, "Shell & Command", "", "Command for first terminal only"),
    ConfigOption("env", OptType.REPEATABLE_STRING, "Shell & Command", "", "Extra environment variables (KEY=VALUE)", repeatable=True),
    ConfigOption("input", OptType.REPEATABLE_STRING, "Shell & Command", "",
                 "Startup input data (raw:string or path:filepath)", repeatable=True),
    ConfigOption("wait-after-command", OptType.BOOLEAN, "Shell & Command", "false", "Keep terminal open after command exits"),
    ConfigOption("abnormal-command-exit-runtime", OptType.INTEGER, "Shell & Command", "",
                 "Abnormal exit detection threshold (ms)", min_val=0),
    ConfigOption("shell-integration", OptType.ENUM, "Shell & Command", "detect",
                 "Shell integration mode",
                 enum_values=["detect", "none", "bash", "fish", "zsh", "elvish"]),
    ConfigOption("shell-integration-features", OptType.STRING, "Shell & Command", "cursor,sudo,title",
                 "Shell integration features (comma-separated, prefix with no- to disable)"),
    ConfigOption("term", OptType.STRING, "Shell & Command", "xterm-ghostty",
                 "TERM environment variable value"),
    ConfigOption("enquiry-response", OptType.STRING, "Shell & Command", "", "Response to ENQ character"),
    ConfigOption("notify-on-command-finish", OptType.ENUM, "Shell & Command", "never",
                 "When to notify on command completion",
                 enum_values=["never", "unfocused", "always"]),
    ConfigOption("notify-on-command-finish-action", OptType.STRING, "Shell & Command",
                 "bell,no-notify", "Notification actions (bell, notify, no-bell, no-notify)"),
    ConfigOption("notify-on-command-finish-after", OptType.DURATION, "Shell & Command", "5s",
                 "Minimum runtime before notification"),
    ConfigOption("command-palette-entry", OptType.REPEATABLE_STRING, "Shell & Command", "",
                 "Custom command palette entry (title:X, action:Y, description:Z)", repeatable=True),

    # ── Clipboard ─────────────────────────────────────────────
    ConfigOption("clipboard-read", OptType.ENUM, "Clipboard", "ask",
                 "Allow clipboard reading (OSC 52)",
                 enum_values=["ask", "allow", "deny"]),
    ConfigOption("clipboard-write", OptType.ENUM, "Clipboard", "allow",
                 "Allow clipboard writing (OSC 52)",
                 enum_values=["ask", "allow", "deny"]),
    ConfigOption("clipboard-trim-trailing-spaces", OptType.BOOLEAN, "Clipboard", "false",
                 "Trim trailing whitespace on copy"),
    ConfigOption("clipboard-paste-protection", OptType.BOOLEAN, "Clipboard", "true",
                 "Confirm before pasting unsafe text"),
    ConfigOption("clipboard-paste-bracketed-safe", OptType.BOOLEAN, "Clipboard", "true",
                 "Consider bracketed pastes as safe"),
    ConfigOption("clipboard-codepoint-map", OptType.REPEATABLE_STRING, "Clipboard", "",
                 "Map codepoints when copying (U+1234=U+ABCD or text)", repeatable=True),
    ConfigOption("title-report", OptType.BOOLEAN, "Clipboard", "false",
                 "Enable title reporting via CSI 21 t"),

    # ── Scrollback ────────────────────────────────────────────
    ConfigOption("scrollback-limit", OptType.INTEGER, "Scrollback", "10000000",
                 "Scrollback buffer size in bytes", min_val=0),
    ConfigOption("scrollbar", OptType.ENUM, "Scrollback", "system",
                 "Scrollbar visibility",
                 enum_values=["system", "never"]),

    # ── Rendering ─────────────────────────────────────────────
    ConfigOption("custom-shader", OptType.PATH, "Rendering", "",
                 "Path to custom GLSL fragment shader", repeatable=True),
    ConfigOption("custom-shader-animation", OptType.BOOLEAN, "Rendering", "false",
                 "Enable shader animation support"),
    ConfigOption("background-image", OptType.PATH, "Rendering", "", "Background image path (PNG/JPEG)"),
    ConfigOption("background-image-opacity", OptType.FLOAT, "Rendering", "1",
                 "Background image opacity multiplier", min_val=0.0, max_val=10.0),
    ConfigOption("background-image-position", OptType.ENUM, "Rendering", "center",
                 "Background image placement",
                 enum_values=["top-left", "top-center", "top-right",
                              "center-left", "center", "center-right",
                              "bottom-left", "bottom-center", "bottom-right"]),
    ConfigOption("background-image-fit", OptType.ENUM, "Rendering", "contain",
                 "Background image scaling",
                 enum_values=["contain", "cover", "stretch", "none"]),
    ConfigOption("background-image-repeat", OptType.BOOLEAN, "Rendering", "false",
                 "Tile background image"),
    ConfigOption("image-storage-limit", OptType.INTEGER, "Rendering", "320000000",
                 "Maximum memory for terminal images in bytes (0 = no limit)", min_val=0),
    ConfigOption("link", OptType.REPEATABLE_STRING, "Rendering", "",
                 "Custom link matching rules", repeatable=True),
    ConfigOption("link-url", OptType.BOOLEAN, "Rendering", "true", "Enable URL auto-detection"),
    ConfigOption("link-previews", OptType.ENUM, "Rendering", "true",
                 "Show link previews on hover",
                 enum_values=["true", "false", "osc8"]),
    ConfigOption("osc-color-report-format", OptType.ENUM, "Rendering", "rgb",
                 "Color reporting format for OSC sequences",
                 enum_values=["rgb", "x11", "legacy"]),
    ConfigOption("vt-kam-allowed", OptType.BOOLEAN, "Rendering", "true",
                 "Allow keyboard action mode (VT KAM)"),
    ConfigOption("progress-style", OptType.BOOLEAN, "Rendering", "true",
                 "Show graphical progress bars via ConEmu OSC 9;4"),

    # ── Desktop Integration ───────────────────────────────────
    ConfigOption("desktop-notifications", OptType.BOOLEAN, "Desktop Integration", "true",
                 "Enable desktop notifications from terminal apps"),
    ConfigOption("confirm-close-surface", OptType.ENUM, "Desktop Integration", "if-running",
                 "Confirm before closing terminal",
                 enum_values=["never", "always", "if-running"]),
    ConfigOption("quit-after-last-window-closed", OptType.BOOLEAN, "Desktop Integration", "false",
                 "Quit when last window closes"),
    ConfigOption("quit-after-last-window-closed-delay", OptType.DURATION, "Desktop Integration", "",
                 "Delay before quitting after last window closes"),
    ConfigOption("initial-window", OptType.ENUM, "Desktop Integration", "same-parent",
                 "How to launch initial window",
                 enum_values=["same-parent", "new-process"]),
    ConfigOption("config-file", OptType.PATH, "Desktop Integration", "",
                 "Include additional config file (prefix ? for optional)", repeatable=True),
    ConfigOption("config-default-files", OptType.BOOLEAN, "Desktop Integration", "true",
                 "Whether to load default config files"),
    ConfigOption("app-notifications", OptType.STRING, "Desktop Integration", "",
                 "Control in-app notifications (comma-separated, prefix no- to disable)"),
    ConfigOption("undo-timeout", OptType.DURATION, "Desktop Integration", "5s",
                 "Duration that undo operations remain available"),
    ConfigOption("bell-features", OptType.STRING, "Desktop Integration", "",
                 "Bell features to enable (system, audio, visual; prefix no- to disable)"),
    ConfigOption("bell-audio-path", OptType.PATH, "Desktop Integration", "",
                 "Path to audio file for bell sound"),
    ConfigOption("bell-audio-volume", OptType.FLOAT, "Desktop Integration", "0.5",
                 "Bell audio volume (0.0 - 1.0)", min_val=0.0, max_val=1.0),
    ConfigOption("async-backend", OptType.ENUM, "Desktop Integration", "auto",
                 "Low-level async IO backend",
                 enum_values=["auto", "io_uring", "epoll", "kqueue"]),

    # ── Quick Terminal ────────────────────────────────────────
    ConfigOption("quick-terminal-screen", OptType.ENUM, "Quick Terminal", "main",
                 "Screen where quick terminal appears",
                 enum_values=["main", "mouse"]),
    ConfigOption("quick-terminal-position", OptType.ENUM, "Quick Terminal", "top",
                 "Edge where quick terminal slides in",
                 enum_values=["top", "bottom", "left", "right", "center"]),
    ConfigOption("quick-terminal-animation-duration", OptType.DURATION, "Quick Terminal", "200ms",
                 "Show/hide animation duration (0 to disable)"),
    ConfigOption("quick-terminal-autohide", OptType.BOOLEAN, "Quick Terminal", "true",
                 "Auto-hide quick terminal on focus loss"),
    ConfigOption("quick-terminal-space-behavior", OptType.ENUM, "Quick Terminal", "move",
                 "Space/desktop behavior for quick terminal",
                 enum_values=["move", "stay"]),
    ConfigOption("quick-terminal-size", OptType.STRING, "Quick Terminal", "",
                 "Quick terminal size (e.g. 20%, 300px)"),
    ConfigOption("quick-terminal-keyboard-interactivity", OptType.ENUM, "Quick Terminal", "exclusive",
                 "When quick terminal receives keyboard input",
                 enum_values=["exclusive", "on-demand", "none"]),

    # ── macOS ─────────────────────────────────────────────────
    ConfigOption("macos-titlebar-style", OptType.ENUM, "macOS", "system",
                 "macOS titlebar style",
                 enum_values=["system", "transparent", "tabs", "hidden"], platform="macos"),
    ConfigOption("macos-titlebar-proxy-icon", OptType.ENUM, "macOS", "visible",
                 "Show proxy icon in titlebar",
                 enum_values=["visible", "hidden"], platform="macos"),
    ConfigOption("macos-option-as-alt", OptType.ENUM, "macOS", "false",
                 "Treat Option key as Alt modifier",
                 enum_values=["false", "true", "left", "right"], platform="macos"),
    ConfigOption("macos-window-shadow", OptType.BOOLEAN, "macOS", "true",
                 "Enable window drop shadow", platform="macos"),
    ConfigOption("macos-icon", OptType.STRING, "macOS", "official",
                 "Application icon style (official, glass, chalkboard, retro, microchip, paper, etc.)",
                 platform="macos"),
    ConfigOption("macos-icon-frame", OptType.ENUM, "macOS", "aluminum",
                 "Icon frame/border style",
                 enum_values=["aluminum", "beige", "chrome", "flat", "glossy", "plastic"],
                 platform="macos"),
    ConfigOption("macos-icon-ghost-color", OptType.COLOR, "macOS", "",
                 "Custom ghost color in app icon", platform="macos"),
    ConfigOption("macos-icon-screen-color", OptType.COLOR, "macOS", "",
                 "Custom screen color in app icon", platform="macos"),
    ConfigOption("macos-secure-input-indication", OptType.BOOLEAN, "macOS", "true",
                 "Show indicator when secure input is active", platform="macos"),
    ConfigOption("macos-auto-secure-input", OptType.BOOLEAN, "macOS", "true",
                 "Auto-enable secure input for password prompts", platform="macos"),
    ConfigOption("macos-non-native-fullscreen", OptType.ENUM, "macOS", "false",
                 "Use non-native fullscreen mode",
                 enum_values=["false", "true", "visible-menu", "padded-notch"], platform="macos"),
    ConfigOption("macos-window-buttons", OptType.ENUM, "macOS", "visible",
                 "Visibility of window buttons (traffic lights) in titlebar",
                 enum_values=["visible", "hidden", "hidden-when-inactive"], platform="macos"),
    ConfigOption("macos-dock-drop-behavior", OptType.ENUM, "macOS", "new-tab",
                 "Behavior when dropping files onto Ghostty dock icon",
                 enum_values=["new-tab", "new-window", "new-split"], platform="macos"),
    ConfigOption("macos-hidden", OptType.BOOLEAN, "macOS", "false",
                 "Hide Ghostty from dock and app switcher", platform="macos"),
    ConfigOption("macos-applescript", OptType.BOOLEAN, "macOS", "true",
                 "Enable AppleScript support", platform="macos"),
    ConfigOption("macos-custom-icon", OptType.PATH, "macOS", "",
                 "Path to custom icon file (PNG, JPEG, or ICNS)", platform="macos"),
    ConfigOption("macos-shortcuts", OptType.BOOLEAN, "macOS", "true",
                 "Allow macOS Shortcuts to control Ghostty", platform="macos"),
    ConfigOption("font-thicken", OptType.BOOLEAN, "macOS", "false",
                 "Thicken font strokes for better readability", platform="macos"),
    ConfigOption("font-thicken-strength", OptType.INTEGER, "macOS", "255",
                 "Font thickening strength (0-255)", min_val=0, max_val=255, platform="macos"),
    ConfigOption("window-colorspace", OptType.ENUM, "macOS", "srgb",
                 "Window color space",
                 enum_values=["srgb", "display-p3"], platform="macos"),
    ConfigOption("window-position-x", OptType.INTEGER, "macOS", "",
                 "Initial window X position in pixels", platform="macos"),
    ConfigOption("window-position-y", OptType.INTEGER, "macOS", "",
                 "Initial window Y position in pixels", platform="macos"),
    ConfigOption("window-save-state", OptType.ENUM, "macOS", "default",
                 "Window state persistence across restarts",
                 enum_values=["default", "never", "always"], platform="macos"),
    ConfigOption("window-step-resize", OptType.BOOLEAN, "macOS", "false",
                 "Resize in cell-size increments", platform="macos"),
    ConfigOption("auto-update", OptType.ENUM, "macOS", "check",
                 "Auto-update behavior",
                 enum_values=["off", "check", "download"], platform="macos"),
    ConfigOption("auto-update-channel", OptType.ENUM, "macOS", "",
                 "Release channel for auto-updates",
                 enum_values=["stable", "tip"], platform="macos"),

    # ── Linux & GTK ───────────────────────────────────────────
    ConfigOption("gtk-single-instance", OptType.ENUM, "Linux & GTK", "detect",
                 "Run as single instance (new invocations open in existing)",
                 enum_values=["detect", "true", "false"], platform="gtk"),
    ConfigOption("gtk-tabs-location", OptType.ENUM, "Linux & GTK", "top",
                 "Tab bar position",
                 enum_values=["top", "bottom", "left", "right", "hidden"], platform="gtk"),
    ConfigOption("gtk-wide-tabs", OptType.BOOLEAN, "Linux & GTK", "true",
                 "Expand tabs to fill available width", platform="gtk"),
    ConfigOption("gtk-adwaita", OptType.ENUM, "Linux & GTK", "true",
                 "Use GNOME Adwaita theme styling",
                 enum_values=["true", "false"], platform="gtk"),
    ConfigOption("gtk-toolbar-style", OptType.ENUM, "Linux & GTK", "raised",
                 "Header bar / toolbar style",
                 enum_values=["raised", "flat", "raised-border", "hidden"], platform="gtk"),
    ConfigOption("gtk-titlebar", OptType.BOOLEAN, "Linux & GTK", "true",
                 "Display full GTK titlebar instead of simple WM titlebar", platform="gtk"),
    ConfigOption("gtk-titlebar-hide-when-maximized", OptType.BOOLEAN, "Linux & GTK", "false",
                 "Hide titlebar when window is maximized", platform="gtk"),
    ConfigOption("gtk-titlebar-style", OptType.ENUM, "Linux & GTK", "native",
                 "GTK titlebar style",
                 enum_values=["native", "tabs"], platform="gtk"),
    ConfigOption("gtk-custom-css", OptType.PATH, "Linux & GTK", "",
                 "Path to custom GTK CSS file", repeatable=True, platform="gtk"),
    ConfigOption("gtk-opengl-debug", OptType.BOOLEAN, "Linux & GTK", "false",
                 "Enable GTK OpenGL debugging logs", platform="gtk"),
    ConfigOption("gtk-quick-terminal-layer", OptType.ENUM, "Linux & GTK", "overlay",
                 "Layer of the quick terminal window",
                 enum_values=["overlay", "top", "bottom", "background"], platform="gtk"),
    ConfigOption("gtk-quick-terminal-namespace", OptType.STRING, "Linux & GTK", "",
                 "Wayland namespace for quick terminal window", platform="gtk"),
    ConfigOption("linux-cgroup", OptType.ENUM, "Linux & GTK", "single-instance",
                 "Put surfaces into transient systemd scopes for resource management",
                 enum_values=["never", "always", "single-instance"], platform="linux"),
    ConfigOption("linux-cgroup-memory-limit", OptType.INTEGER, "Linux & GTK", "",
                 "Memory limit per terminal surface in bytes", min_val=0, platform="linux"),
    ConfigOption("linux-cgroup-processes-limit", OptType.INTEGER, "Linux & GTK", "",
                 "Process count limit per terminal surface", min_val=0, platform="linux"),
    ConfigOption("linux-cgroup-hard-fail", OptType.BOOLEAN, "Linux & GTK", "false",
                 "Fail surface creation if cgroup setup fails", platform="linux"),
    ConfigOption("class", OptType.STRING, "Linux & GTK", "com.mitchellh.ghostty",
                 "WM_CLASS / Wayland app ID / DBus name", platform="gtk"),
    ConfigOption("x11-instance-name", OptType.STRING, "Linux & GTK", "ghostty",
                 "X11 WM_CLASS instance name", platform="linux"),
    ConfigOption("freetype-load-flags", OptType.REPEATABLE_STRING, "Linux & GTK", "",
                 "FreeType rendering flags (hinting, force-autohint, monochrome, autohint, light)",
                 repeatable=True, platform="linux"),
    ConfigOption("window-show-tab-bar", OptType.ENUM, "Linux & GTK", "auto",
                 "Tab bar visibility",
                 enum_values=["always", "auto", "never"], platform="gtk"),
    ConfigOption("window-subtitle", OptType.ENUM, "Linux & GTK", "false",
                 "Window subtitle content",
                 enum_values=["false", "working-directory"], platform="gtk"),
    ConfigOption("window-titlebar-background", OptType.COLOR, "Linux & GTK", "",
                 "Titlebar background color (with ghostty theme)", platform="gtk"),
    ConfigOption("window-titlebar-foreground", OptType.COLOR, "Linux & GTK", "",
                 "Titlebar foreground color (with ghostty theme)", platform="gtk"),
    ConfigOption("language", OptType.STRING, "Linux & GTK", "",
                 "GUI language override (e.g. de, en, ja)", platform="gtk"),
]


def get_options_by_category() -> dict[str, list[ConfigOption]]:
    result: dict[str, list[ConfigOption]] = {cat: [] for cat in CATEGORIES}
    for opt in CONFIG_OPTIONS:
        if opt.category in result:
            result[opt.category].append(opt)
    return result


# Default ANSI 16-color palette
DEFAULT_PALETTE = {
    0: "#1d1f21",   # black
    1: "#cc6666",   # red
    2: "#b5bd68",   # green
    3: "#f0c674",   # yellow
    4: "#81a2be",   # blue
    5: "#b294bb",   # magenta
    6: "#8abeb7",   # cyan
    7: "#c5c8c6",   # white
    8: "#969896",   # bright black
    9: "#de935f",   # bright red
    10: "#b5bd68",  # bright green
    11: "#f0c674",  # bright yellow
    12: "#81a2be",  # bright blue
    13: "#b294bb",  # bright magenta
    14: "#8abeb7",  # bright cyan
    15: "#ffffff",  # bright white
}

PALETTE_NAMES = [
    "Black", "Red", "Green", "Yellow", "Blue", "Magenta", "Cyan", "White",
    "Bright Black", "Bright Red", "Bright Green", "Bright Yellow",
    "Bright Blue", "Bright Magenta", "Bright Cyan", "Bright White",
]
