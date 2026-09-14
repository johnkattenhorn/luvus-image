#!/usr/bin/env python3
"""Push the IMAGES dock from the focused workspace.

workspace.created/closed do not fire when you click an already-open
workspace. pane.focused does. Skip the scan when the workspace has not
changed, because pane focus also fires between panes in the same folder.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from http_view import save_gallery
from scan import labelled
from state import dir as state_dir

LUVUS = os.environ.get("LUVUS_BIN_PATH", "luvus")
DOCK = "images"


def _int(name: str, default: int) -> int:
    raw = os.environ.get(name, "")
    try:
        return int(raw)
    except ValueError:
        return default


def focused_root() -> Path:
    return Path(os.environ.get("LUVUS_WORKSPACE_CWD") or os.getcwd())


def last_root_path() -> Path:
    return state_dir() / "last_workspace"


def last_root() -> str:
    try:
        return last_root_path().read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def remember_root(root: Path) -> None:
    last_root_path().write_text(str(root.resolve()) + "\n", encoding="utf-8")


def force_refresh() -> bool:
    event = os.environ.get("LUVUS_MODULE_EVENT") or ""
    action = os.environ.get("LUVUS_MODULE_ACTION_ID") or ""
    if action == "refresh":
        return True
    if event in ("startup", "workspace.created", "workspace.closed"):
        return True
    return False


def should_scan(root: Path) -> bool:
    if force_refresh():
        return True
    try:
        key = str(root.resolve())
    except OSError:
        key = str(root)
    return key != last_root()


def push(title: str, rows: list[dict], *, state: str = "done") -> None:
    payload = json.dumps(rows, ensure_ascii=False)
    subprocess.run(
        [LUVUS, "ui", "dock", "push", "--id", DOCK, "--title", title,
         "--rows", payload],
        check=False, capture_output=True, timeout=10,
    )
    label = title.split("·", 1)[-1].strip() if "·" in title else title
    bar = [
        {"type": "text", "text": "IMG"},
        {"type": "state", "state": state, "label": label[:16]},
    ]
    subprocess.run(
        [LUVUS, "bar", "push", "--id", "images", "--region", "bottom-right",
         "--content", json.dumps(bar)],
        check=False, capture_output=True, timeout=5,
    )


def watcher_alive() -> bool:
    from watch import pid_alive, pid_path
    try:
        pid = int(pid_path().read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return False
    return pid_alive(pid)


def main() -> int:
    if not watcher_alive():
        from watch import ensure
        try:
            ensure()
        except Exception as exc:
            print(f"watch start failed: {exc}", file=sys.stderr)
    root = focused_root()
    if not should_scan(root):
        return 0
    name = root.name or "workspace"
    title = f"IMAGES · {name}"
    try:
        push(title, [{"text": f"scanning {name}…", "tone": "muted", "dot": "working"}],
             state="working")
    except (OSError, subprocess.SubprocessError):
        pass
    depth = _int("LUVUS_SETTING_DEPTH", 4)
    limit = _int("LUVUS_SETTING_LIMIT", 40)
    t0 = __import__("time").perf_counter()
    rows = []
    n = 0
    if not root.is_dir():
        rows = [{"text": "no workspace", "tone": "muted"}]
    else:
        items = labelled(root, depth, limit)
        n = len(items)
        if not items:
            rows = [{"text": "no images under this workspace", "tone": "muted"}]
        else:
            files = [path for path, _label in items]
            labels = [label for _path, label in items]
            save_gallery(files, 0, labels)
            for path, label in items:
                rows.append({
                    "text": label,
                    "action": "open",
                    "value": str(path),
                })
    ms = int((__import__("time").perf_counter() - t0) * 1000)
    try:
        push(title, rows, state="done")
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"dock push failed: {exc}", file=sys.stderr)
        return 1
    remember_root(root)
    print(f"scanned {n} files in {ms}ms from {root}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
