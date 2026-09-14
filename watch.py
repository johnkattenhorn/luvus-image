#!/usr/bin/env python3
"""Keep the IMAGES dock on the workspace the sidebar says is active.

Module hooks never run pane.focused. The event stream, while idle, is
almost only terminal.output_ready — a sidebar click does not wake us.
So we poll workspace list and rescan when `active` cwd changes.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from state import dir as state_dir

LUVUS = os.environ.get("LUVUS_BIN_PATH", "luvus")
POLL = 0.4


def pid_path() -> Path:
    return state_dir() / "watch.pid"


def log_path() -> Path:
    return state_dir() / "watch.log"


def log(msg: str) -> None:
    line = time.strftime("%Y-%m-%dT%H:%M:%S ") + msg + "\n"
    try:
        with log_path().open("a", encoding="utf-8") as fh:
            fh.write(line)
    except OSError:
        pass


def pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def stop_old() -> None:
    try:
        pid = int(pid_path().read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return
    if pid == os.getpid() or not pid_alive(pid):
        return
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        return
    for _ in range(20):
        if not pid_alive(pid):
            return
        time.sleep(0.05)
    try:
        os.kill(pid, signal.SIGKILL)
    except OSError:
        pass


def ensure() -> None:
    try:
        pid = int(pid_path().read_text(encoding="utf-8").strip())
        if pid_alive(pid) and pid != os.getpid():
            return
    except (OSError, ValueError):
        pass
    stop_old()
    proc = subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve())],
        cwd=str(Path(__file__).resolve().parent),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        env={**os.environ},
    )
    pid_path().write_text(str(proc.pid) + "\n", encoding="utf-8")
    log(f"started pid {proc.pid}")


def active_workspace() -> dict | None:
    try:
        raw = subprocess.check_output(
            [LUVUS, "workspace", "list"], timeout=5, text=True,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    try:
        workspaces = json.loads(raw)["result"]["workspaces"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return None
    for w in workspaces:
        if w.get("active"):
            return w
    return None


def refresh(cwd: str) -> None:
    env = {**os.environ, "LUVUS_WORKSPACE_CWD": cwd, "LUVUS_MODULE_EVENT": "watch"}
    subprocess.run(
        [sys.executable, str(Path(__file__).resolve().parent / "dock.py")],
        cwd=str(Path(__file__).resolve().parent),
        env=env,
        timeout=30,
        check=False,
        capture_output=True,
    )


def loop() -> None:
    pid_path().write_text(str(os.getpid()) + "\n", encoding="utf-8")
    log(f"loop pid {os.getpid()}")
    last = None
    while True:
        ws = active_workspace()
        cwd = (ws or {}).get("cwd") or (ws or {}).get("terminal_cwd")
        name = (ws or {}).get("name") or ""
        if cwd and cwd != last:
            log(f"active {name!r} {cwd}")
            refresh(cwd)
            last = cwd
        time.sleep(POLL)


if __name__ == "__main__":
    loop()
