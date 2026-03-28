"""
Read and write Ghostty config files.
Format: key = value (one per line), # comments, blank lines preserved.
"""

import os
from pathlib import Path


def default_config_path() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME", "")
    base = Path(xdg) / "ghostty" if xdg else Path.home() / ".config" / "ghostty"
    # Prefer config.ghostty, fall back to legacy config if it exists
    new_path = base / "config.ghostty"
    legacy_path = base / "config"
    if legacy_path.exists() and not new_path.exists():
        return legacy_path
    return new_path


def parse_config(path: Path) -> dict[str, list[str]]:
    """Parse a Ghostty config file. Returns {key: [values]} to support repeatable keys."""
    result: dict[str, list[str]] = {}
    if not path.exists():
        return result
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        key = key.strip()
        value = value.strip()
        result.setdefault(key, []).append(value)
    return result


def write_config(path: Path, values: dict[str, list[str]],
                 original_path: Path | None = None) -> None:
    """Write config, preserving comments and order from original if available."""
    path.parent.mkdir(parents=True, exist_ok=True)

    written_keys: set[str] = set()
    lines: list[str] = []

    # Preserve structure from original file
    if original_path and original_path.exists():
        for line in original_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                lines.append(line)
                continue
            if "=" not in stripped:
                lines.append(line)
                continue
            key, _, _ = stripped.partition("=")
            key = key.strip()
            if key in values:
                if key not in written_keys:
                    for val in values[key]:
                        lines.append(f"{key} = {val}")
                    written_keys.add(key)
                # else skip duplicate lines for already-written repeatable key
            else:
                # Key was removed / cleared - skip it
                pass

    # Append new keys not in original
    for key, vals in values.items():
        if key not in written_keys:
            for val in vals:
                lines.append(f"{key} = {val}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
