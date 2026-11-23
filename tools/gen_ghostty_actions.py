#!/usr/bin/env python3
"""Regenerate ghostty_config_gui/ghostty_actions.json from `ghostty +list-actions --docs`.

Usage: python tools/gen_ghostty_actions.py [path/to/ghostty]
"""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "ghostty_config_gui" / "ghostty_actions.json"

# Parameter specs. The docs don't say reliably whether an action takes an
# argument, so it's maintained by hand: name -> (required|optional, values, hint).
# Empty `values` means: use whatever was parsed from the docs.
_FILE_ACTIONS = ["copy", "paste", "open", "copy,plain", "paste,plain", "open,plain",
                 "copy,vt", "open,vt", "copy,html", "open,html"]
_DIRS = ["right", "down", "left", "up"]
PARAMS: dict[str, tuple[str, list[str], str]] = {
    "csi": ("required", [], "CSI sequence without the ESC [ header, e.g. 0m"),
    "esc": ("required", [], "sequence to send after ESC"),
    "text": ("required", [], r"text to send (Zig string syntax), e.g. \x15"),
    "cursor_key": ("required", [], "data to send (see docs)"),
    "copy_to_clipboard": ("optional", [], "format (default: mixed)"),
    "increase_font_size": ("required", ["1", "0.5", "2"], "points"),
    "decrease_font_size": ("required", ["1", "0.5", "2"], "points"),
    "set_font_size": ("required", ["12", "13", "14", "16"], "points"),
    "search": ("required", [], "search text"),
    "navigate_search": ("required", ["next", "previous"], ""),
    "scroll_to_row": ("required", ["0"], "absolute row (0 = first)"),
    "scroll_page_fractional": ("required", ["0.5", "-0.5", "1", "-1"], "fraction of a page (+down / -up)"),
    "scroll_page_lines": ("required", ["1", "-1", "3", "-3"], "lines (+down / -up)"),
    "adjust_selection": ("required", ["left", "right", "up", "down", "page_up", "page_down",
                                      "home", "end", "beginning_of_line", "end_of_line"], ""),
    "jump_to_prompt": ("required", ["-1", "1"], "prompts (+down / -up)"),
    "write_scrollback_file": ("required", _FILE_ACTIONS, "action[,format]"),
    "write_screen_file": ("required", _FILE_ACTIONS, "action[,format]"),
    "write_selection_file": ("required", _FILE_ACTIONS, "action[,format]"),
    "goto_tab": ("required", [str(i) for i in range(1, 10)], "tab index (1-based)"),
    "move_tab": ("required", ["1", "-1"], "relative offset"),
    "set_surface_title": ("optional", [], "title (empty clears)"),
    "set_tab_title": ("optional", [], "title (empty clears)"),
    "set_window_title": ("optional", [], "title (empty clears)"),
    "new_split": ("required", _DIRS + ["auto"], ""),
    "goto_split": ("required", _DIRS + ["previous", "next"], ""),
    "goto_window": ("required", ["previous", "next"], ""),
    "resize_split": ("required", [f"{d},10" for d in _DIRS], "direction,pixels"),
    "inspector": ("required", ["toggle", "show", "hide"], ""),
    "open_config": ("optional", ["os_open", "new_window"], "(default: os_open)"),
    "close_tab": ("optional", ["this", "other", "right"], "(default: this)"),
    "activate_key_table": ("required", [], "key table name"),
    "activate_key_table_once": ("required", [], "key table name"),
}


def find_ghostty() -> str:
    if len(sys.argv) > 1:
        return sys.argv[1]
    for cand in (shutil.which("ghostty"), "/Applications/Ghostty.app/Contents/MacOS/ghostty"):
        if cand and Path(cand).exists():
            return cand
    sys.exit("ghostty binary not found; pass its path as an argument")


def parse(text: str) -> list[dict]:
    actions: list[dict] = []
    cur = None
    for line in text.splitlines():
        m = re.match(r"^([a-z_]+):\s*$", line)
        if m:
            cur = {"name": m.group(1), "lines": []}
            actions.append(cur)
        elif cur is not None:
            cur["lines"].append(line[2:] if line.startswith("  ") else line.strip())

    out = []
    for a in actions:
        doc = "\n".join(a["lines"]).strip()
        summary = doc.split("\n\n")[0].replace("\n", " ").strip()
        values: list[str] = []
        vm = re.search(r"Valid (?:values|arguments)[^:]*:(.*?)(?:\n\n(?!\s*-|\s{2,})|\Z)", doc, re.S)
        if vm:
            block = vm.group(1)
            values = re.findall(r"^\s*-\s*`([^`]+)`", block, re.M)
            if not values:
                values = re.findall(r"`([^`]+)`", block.split("\n\n")[0])
        values = [v.removesuffix(" (default)").strip() for v in values]
        examples = re.findall(r"`" + re.escape(a["name"]) + r":([^`]+)`", doc)
        values = list(dict.fromkeys(values))
        param, hint = ("required" if values else "none"), ""
        if a["name"] in PARAMS:
            param, override, hint = PARAMS[a["name"]]
            values = override or values
        if not hint and examples:
            hint = f"e.g. {examples[0]}"
        out.append({
            "name": a["name"],
            "summary": summary,
            "doc": doc,
            "param": param,
            "values": values,
            "hint": hint,
        })
    return out


def main():
    ghostty = find_ghostty()
    text = subprocess.run([ghostty, "+list-actions", "--docs"], capture_output=True,
                          text=True, check=True).stdout
    version = subprocess.run([ghostty, "+version"], capture_output=True, text=True).stdout
    vline = next((l.strip() for l in version.splitlines() if l.startswith("Ghostty")), "")
    data = {"generated_from": vline, "actions": parse(text)}
    OUT.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {len(data['actions'])} actions to {OUT}")


if __name__ == "__main__":
    main()
