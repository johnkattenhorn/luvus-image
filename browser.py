#!/usr/bin/env python3
"""Open the selected image in a local browser. That is the readable view."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from http_view import ensure, save_gallery
from render import is_image
from scan import labelled
from state import set_current

LUVUS = os.environ.get("LUVUS_BIN_PATH", "luvus")


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


def open_url(url: str) -> None:
    opener = shutil.which("xdg-open") or shutil.which("gio")
    if opener and opener.endswith("gio"):
        cmd = [opener, "open", url]
    elif opener:
        cmd = [opener, url]
    else:
        cmd = ["python3", "-m", "webbrowser", url]
    subprocess.Popen(
        cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, start_new_session=True,
    )


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
    path = path.resolve()
    set_current(path)
    root = Path(os.environ.get("LUVUS_WORKSPACE_CWD") or os.getcwd())
    try:
        depth = int(os.environ.get("LUVUS_SETTING_DEPTH") or "4")
        limit = int(os.environ.get("LUVUS_SETTING_LIMIT") or "40")
    except ValueError:
        depth, limit = 4, 40
    items = labelled(root, depth, limit) if root.is_dir() else []
    files = [p.resolve() for p, _label in items]
    labels = [label for _p, label in items]
    try:
        index = files.index(path)
    except ValueError:
        files = [path]
        try:
            rel = path.relative_to(root.resolve())
        except ValueError:
            rel = path.name
        labels = [f"1  {rel}"]
        index = 0
    save_gallery(files, index, labels)
    try:
        port = ensure()
    except Exception as exc:
        toast(f"could not start the preview server: {exc}")
        print(exc, file=sys.stderr)
        return 1
    url = f"http://127.0.0.1:{port}/?n={index + 1}"
    open_url(url)
    toast(f"opened {path.name} in the browser")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
