"""
Load Ghostty themes from the system theme directory.
"""

import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ThemeColors:
    name: str = ""
    background: str = "#282c34"
    foreground: str = "#ffffff"
    cursor_color: str = ""
    cursor_text: str = ""
    selection_background: str = ""
    selection_foreground: str = ""
    palette: dict[int, str] = field(default_factory=dict)


def find_theme_dir() -> Path | None:
    """Find the Ghostty themes directory."""
    candidates = []
    if sys.platform == "darwin":
        # macOS: themes bundled inside the app
        candidates.append(
            Path("/Applications/Ghostty.app/Contents/Resources/ghostty/themes")
        )
        # Homebrew cask may also symlink into Cellar; check via the app bundle
        # User custom themes
        candidates.append(Path.home() / ".config" / "ghostty" / "themes")
    # Linux / cross-platform paths
    candidates += [
        Path("/usr/share/ghostty/themes"),
        Path("/usr/local/share/ghostty/themes"),
        Path("/opt/ghostty/share/ghostty/themes"),
        Path.home() / ".local" / "share" / "ghostty" / "themes",
    ]
    # Also check XDG_DATA_DIRS
    for d in os.environ.get("XDG_DATA_DIRS", "").split(":"):
        if d:
            candidates.append(Path(d) / "ghostty" / "themes")
    for p in candidates:
        if p.is_dir():
            return p
    return None


def list_themes() -> list[str]:
    """Get sorted list of available theme names."""
    theme_dir = find_theme_dir()
    if not theme_dir:
        # Fallback: try ghostty +list-themes
        try:
            result = subprocess.run(
                ["ghostty", "+list-themes"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return [
                    line.rsplit(" (", 1)[0].strip()
                    for line in result.stdout.splitlines()
                    if line.strip()
                ]
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return []

    names = []
    for entry in theme_dir.iterdir():
        if entry.is_file() and not entry.name.startswith("."):
            names.append(entry.name)
    return sorted(names)


def load_theme(name: str) -> ThemeColors | None:
    """Load a theme by name from the theme directory."""
    theme_dir = find_theme_dir()
    if not theme_dir:
        return None

    theme_file = theme_dir / name
    if not theme_file.is_file():
        return None

    theme = ThemeColors(name=name)
    for line in theme_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()

        if key == "background":
            theme.background = value
        elif key == "foreground":
            theme.foreground = value
        elif key == "cursor-color":
            theme.cursor_color = value
        elif key == "cursor-text":
            theme.cursor_text = value
        elif key == "selection-background":
            theme.selection_background = value
        elif key == "selection-foreground":
            theme.selection_foreground = value
        elif key == "palette":
            if "=" in value:
                idx_s, _, color = value.partition("=")
                try:
                    theme.palette[int(idx_s)] = color
                except ValueError:
                    pass

    return theme
