#!/usr/bin/env python3
"""Image pane. Fit is unreadable on a sheet; zoom in.

Keys: + - zoom, hjkl pan, 1-4 tiles, f fit, n/p siblings, r redraw, q quit.
"""

from __future__ import annotations

import os
import select
import signal
import sys
import termios
import tty
from pathlib import Path

from render import (
    EXTS, halfblocks, image_size, is_image, quadrant_box, terminal_size,
)
from state import current_path, set_current

HELP = "+/- zoom  hjkl pan  1-4 tile  f fit  n/p next  q quit"


def siblings(path: Path) -> list[Path]:
    parent = path.parent
    try:
        names = sorted(
            p for p in parent.iterdir()
            if p.is_file() and p.suffix.lower() in EXTS
        )
    except OSError:
        return [path]
    return names or [path]


def paint(path: Path, cam: dict) -> None:
    cols, rows = terminal_size()
    header_rows = 2
    body_rows = max(1, rows - header_rows)
    try:
        w, h = image_size(path)
    except Exception:
        w = h = 0
    sibs = siblings(path)
    try:
        idx = sibs.index(path) + 1
    except ValueError:
        idx = 1
    crop = None
    if cam["tile"] and w and h:
        crop = quadrant_box((w, h), cam["tile"])
    where = f"tile {cam['tile']}" if cam["tile"] else "fit"
    if cam["zoom"] > 1.01:
        where = f"{cam['zoom']:.1f}x {where}"
    title = f"{path.name}  {w}×{h}  {idx}/{len(sibs)}  {where}"
    sys.stdout.write("\x1b[2J\x1b[H\x1b[?25l")
    sys.stdout.write(title[:cols] + "\n")
    sys.stdout.write(HELP[:cols] + "\n")
    try:
        body = halfblocks(
            path, cols, body_rows,
            zoom=cam["zoom"], pan_x=cam["pan_x"], pan_y=cam["pan_y"], crop=crop,
        ).split("\n")[:body_rows]
        sys.stdout.write("\n".join(body))
    except Exception as exc:
        sys.stdout.write(f"cannot decode: {exc}")
    sys.stdout.write("\n")
    sys.stdout.flush()


def reset_cam(cam: dict) -> None:
    cam["zoom"] = 1.0
    cam["pan_x"] = 0.5
    cam["pan_y"] = 0.5
    cam["tile"] = None


def read_key() -> str:
    ch = sys.stdin.read(1)
    if ch != "\x1b":
        return ch
    rest = ""
    if select.select([sys.stdin], [], [], 0.05)[0]:
        rest = sys.stdin.read(2)
    return ch + rest


def main() -> int:
    path = current_path()
    if path is None or not is_image(path):
        sys.stdout.write("no image selected\n")
        sys.stdout.write("click a row in the IMAGES dock, or select a path and run View selected path as an image\n")
        sys.stdout.flush()
        return 0

    cam = {"zoom": 1.0, "pan_x": 0.5, "pan_y": 0.5, "tile": None}
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    redraw = {"flag": True}

    def on_winch(_signum, _frame):
        redraw["flag"] = True

    signal.signal(signal.SIGWINCH, on_winch)
    try:
        tty.setcbreak(fd)
        while True:
            if redraw["flag"]:
                paint(path, cam)
                redraw["flag"] = False
            key = read_key()
            if key in ("q", "Q", "\x03"):
                break
            if key in ("r", "R"):
                redraw["flag"] = True
                continue
            if key in ("+", "=", "]"):
                cam["zoom"] = min(16.0, cam["zoom"] * 1.5)
                redraw["flag"] = True
                continue
            if key in ("-", "["):
                cam["zoom"] = max(1.0, cam["zoom"] / 1.5)
                if cam["zoom"] <= 1.01:
                    cam["zoom"] = 1.0
                redraw["flag"] = True
                continue
            if key in ("f", "F", "0"):
                reset_cam(cam)
                redraw["flag"] = True
                continue
            if key in "1234":
                cam["tile"] = int(key)
                cam["zoom"] = 1.0
                cam["pan_x"] = 0.5
                cam["pan_y"] = 0.5
                redraw["flag"] = True
                continue
            step = 0.15 / cam["zoom"]
            if key in ("h", "H", "\x1b[D"):
                cam["pan_x"] = max(0.0, cam["pan_x"] - step)
                redraw["flag"] = True
                continue
            if key in ("l", "L", "\x1b[C"):
                cam["pan_x"] = min(1.0, cam["pan_x"] + step)
                redraw["flag"] = True
                continue
            if key in ("k", "K", "\x1b[A"):
                cam["pan_y"] = max(0.0, cam["pan_y"] - step)
                redraw["flag"] = True
                continue
            if key in ("j", "J", "\x1b[B"):
                cam["pan_y"] = min(1.0, cam["pan_y"] + step)
                redraw["flag"] = True
                continue
            sibs = siblings(path)
            if key in ("n", "N"):
                try:
                    i = sibs.index(path)
                except ValueError:
                    i = -1
                path = sibs[(i + 1) % len(sibs)]
                set_current(path)
                reset_cam(cam)
                redraw["flag"] = True
            elif key in ("p", "P"):
                try:
                    i = sibs.index(path)
                except ValueError:
                    i = 0
                path = sibs[(i - 1) % len(sibs)]
                set_current(path)
                reset_cam(cam)
                redraw["flag"] = True
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
        sys.stdout.write("\x1b[?25h\x1b[0m")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
