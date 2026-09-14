#!/usr/bin/env python3
"""Open the viewer pane on a path from a dock row or a pane selection."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from render import is_image
from state import set_current

LUVUS = os.environ.get("LUVUS_BIN_PATH", "luvus")
MODULE = os.environ.get("LUVUS_MODULE_ID", "image.preview")


def toast(text: str) -> None:
    try:
        subprocess.run([LUVUS, "ui", "toast", text], check=False,
                       capture_output=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        pass


def selected_path() -> Path | None:
    raw = os.environ.get("LUVUS_MODULE_ROW_VALUE") or ""
    if raw:
        return Path(raw.strip())
    blob = os.environ.get("LUVUS_MODULE_CONTEXT_JSON") or "{}"
    try:
        sel = (json.loads(blob).get("selection") or "").strip()
    except json.JSONDecodeError:
        sel = ""
    if not sel:
        return None
    # A selected relative path is against the pane's cwd, then the workspace.
    candidates = [Path(sel)]
    pane = os.environ.get("LUVUS_PANE_CWD")
    ws = os.environ.get("LUVUS_WORKSPACE_CWD")
    if pane:
        candidates.append(Path(pane) / sel)
    if ws:
        candidates.append(Path(ws) / sel)
    for c in candidates:
        if c.is_file():
            return c
    return Path(sel)


def main() -> int:
    if len(sys.argv) > 1:
        os.environ["LUVUS_MODULE_ROW_VALUE"] = sys.argv[1]
    path = selected_path()
    if path is None:
        toast("pick an image in the IMAGES dock, or select a path")
        return 0
    if not is_image(path):
        toast(f"not an image: {path.name}")
        return 1
    set_current(path)
    try:
        subprocess.run(
            [LUVUS, "module", "pane", "open", MODULE, "view",
             "--placement", "tab"],
            check=False, capture_output=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"pane open failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
