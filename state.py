"""Where the viewer remembers the file it should show."""

from __future__ import annotations

import os
from pathlib import Path


def dir() -> Path:
    raw = os.environ.get("LUVUS_MODULE_STATE_DIR") or "/tmp/luvus-image"
    p = Path(raw)
    p.mkdir(parents=True, exist_ok=True)
    return p


def current_path() -> Path | None:
    mark = dir() / "current"
    try:
        text = mark.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not text:
        return None
    p = Path(text)
    return p if p.is_file() else None


def set_current(path: Path) -> None:
    (dir() / "current").write_text(str(path.resolve()) + "\n", encoding="utf-8")
