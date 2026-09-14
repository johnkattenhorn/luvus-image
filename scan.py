"""Find image files under a workspace. Depth and cap come from settings."""

from __future__ import annotations

from pathlib import Path

from render import EXTS, is_image

SKIP_DIRS = {
    ".git", ".hg", ".svn", "node_modules", ".venv", "venv", "__pycache__",
    ".tox", ".mypy_cache", ".pytest_cache", "dist", "build", ".next",
    "runs",
}


def labelled(root: Path, depth: int, limit: int) -> list[tuple[Path, str]]:
    """Same order as the IMAGES dock: newest first, 1-based labels."""
    files = scan(root, depth, limit)
    out: list[tuple[Path, str]] = []
    for i, path in enumerate(files, start=1):
        try:
            rel = path.relative_to(root.resolve())
        except ValueError:
            rel = path
        out.append((path, f"{i}  {rel}"))
    return out


def scan(root: Path, depth: int, limit: int) -> list[Path]:
    root = root.resolve()
    if not root.is_dir():
        return []
    found: list[tuple[float, Path]] = []
    _walk(root, root, depth, found)
    found.sort(key=lambda item: -item[0])
    return [p for _, p in found[:limit]]


def _walk(root: Path, here: Path, left: int, found: list[tuple[float, Path]]) -> None:
    try:
        entries = list(here.iterdir())
    except OSError:
        return
    for ent in entries:
        name = ent.name
        if ent.is_dir():
            if name.startswith(".") or name in SKIP_DIRS or left <= 0:
                continue
            _walk(root, ent, left - 1, found)
            continue
        if is_image(ent):
            try:
                mtime = ent.stat().st_mtime
            except OSError:
                continue
            found.append((mtime, ent))
