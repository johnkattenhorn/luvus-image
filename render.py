"""Turn a raster file into terminal rows. No Luvus imports.

Half-blocks, truecolour. Each terminal column is one sample; each row is two.
Luvus is not a sixel/kitty terminal (probed 2026-09-13: img2sixel exits 0 and
the pane stays blank), so this is the densest thing a module pane can paint.
Fit-to-pane of an 800px sheet is ~10 image pixels per cell, which is unreadable.
Callers pass zoom/pan (or a quadrant crop) so a region can be 1:1.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff"}


def is_image(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in EXTS


def image_size(path: Path) -> tuple[int, int]:
    try:
        from PIL import Image
        with Image.open(path) as im:
            return im.size
    except Exception:
        magick = shutil.which("magick") or shutil.which("convert")
        if not magick:
            raise
        ident = subprocess.run(
            [magick, "identify", "-format", "%w %h", str(path)],
            check=True, capture_output=True, text=True, timeout=20,
        )
        w, h = (int(x) for x in ident.stdout.split())
        return w, h


def quadrant_box(size: tuple[int, int], n: int) -> tuple[int, int, int, int]:
    """1=top-left, 2=top-right, 3=bottom-left, 4=bottom-right, in image pixels."""
    if n not in (1, 2, 3, 4):
        raise ValueError("quadrant is 1..4")
    w, h = size
    qw, qh = w // 2, h // 2
    col = 0 if n in (1, 3) else qw
    row = 0 if n in (1, 2) else qh
    return col, row, col + qw, row + qh


def halfblocks(
    path: Path,
    cols: int,
    rows: int,
    *,
    zoom: float = 1.0,
    pan_x: float = 0.5,
    pan_y: float = 0.5,
    crop: tuple[int, int, int, int] | None = None,
) -> str:
    """Paint a window of the image into a cols x rows cell box.

    zoom=1 fits the (cropped) image. zoom=2 shows half as much, panned
    by pan_x/pan_y in 0..1. crop is (left, top, right, bottom) in source
    pixels, or None for the whole file.
    """
    if cols < 2 or rows < 1:
        return ""
    w, h, pix = window(path, cols, rows * 2, zoom=zoom, pan_x=pan_x, pan_y=pan_y, crop=crop)
    out: list[str] = []
    reset = "\x1b[0m"
    for y in range(0, h, 2):
        line: list[str] = []
        for x in range(w):
            top = pix[y * w + x]
            bot = pix[(y + 1) * w + x] if y + 1 < h else (0, 0, 0)
            line.append(
                "\x1b[38;2;{};{};{}m\x1b[48;2;{};{};{}m▀".format(*top, *bot)
            )
        line.append(reset)
        out.append("".join(line))
    return "\n".join(out)


def window(
    path: Path,
    max_w: int,
    max_h: int,
    *,
    zoom: float = 1.0,
    pan_x: float = 0.5,
    pan_y: float = 0.5,
    crop: tuple[int, int, int, int] | None = None,
) -> tuple[int, int, list[tuple[int, int, int]]]:
    """RGB pixels for the current camera, LANCZOS-scaled, letterboxed."""
    try:
        return _window_pil(path, max_w, max_h, zoom, pan_x, pan_y, crop)
    except Exception:
        return _window_magick(path, max_w, max_h, zoom, pan_x, pan_y, crop)


def terminal_size() -> tuple[int, int]:
    sz = shutil.get_terminal_size(fallback=(80, 24))
    return max(8, sz.columns), max(4, sz.lines)


def _window_pil(
    path: Path,
    max_w: int,
    max_h: int,
    zoom: float,
    pan_x: float,
    pan_y: float,
    crop: tuple[int, int, int, int] | None,
) -> tuple[int, int, list[tuple[int, int, int]]]:
    from PIL import Image

    with Image.open(path) as im:
        im = im.convert("RGB")
        if crop:
            im = im.crop(crop)
        return _sample(im, max_w, max_h, zoom, pan_x, pan_y)


def _sample(im, max_w: int, max_h: int, zoom: float, pan_x: float, pan_y: float):
    from PIL import Image

    iw, ih = im.size
    if iw < 1 or ih < 1:
        raise RuntimeError("image has no size")
    zoom = max(1.0, float(zoom))
    pan_x = min(1.0, max(0.0, float(pan_x)))
    pan_y = min(1.0, max(0.0, float(pan_y)))
    fit = min(max_w / iw, max_h / ih)
    scale = fit * zoom
    src_w = min(iw, max_w / scale)
    src_h = min(ih, max_h / scale)
    extra_x = max(0.0, iw - src_w)
    extra_y = max(0.0, ih - src_h)
    x0 = extra_x * pan_x
    y0 = extra_y * pan_y
    box = (int(x0), int(y0), int(x0 + src_w), int(y0 + src_h))
    if box[2] <= box[0]:
        box = (box[0], box[1], box[0] + 1, box[3])
    if box[3] <= box[1]:
        box = (box[0], box[1], box[2], box[1] + 1)
    tile = im.crop(box)
    dest_w = max(1, min(max_w, round(tile.size[0] * scale)))
    dest_h = max(2, min(max_h, round(tile.size[1] * scale)))
    dest_h -= dest_h % 2
    tile = tile.resize((dest_w, dest_h), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (dest_w, dest_h), (0, 0, 0))
    canvas.paste(tile, (0, 0))
    px = canvas.load()
    return dest_w, dest_h, [px[x, y][:3] for y in range(dest_h) for x in range(dest_w)]


def _window_magick(
    path: Path,
    max_w: int,
    max_h: int,
    zoom: float,
    pan_x: float,
    pan_y: float,
    crop: tuple[int, int, int, int] | None,
) -> tuple[int, int, list[tuple[int, int, int]]]:
    magick = shutil.which("magick") or shutil.which("convert")
    if not magick:
        raise RuntimeError("need Pillow or ImageMagick to decode images")
    ident = subprocess.run(
        [magick, "identify", "-format", "%w %h", str(path)],
        check=True, capture_output=True, text=True, timeout=20,
    )
    iw, ih = (int(x) for x in ident.stdout.split())
    if crop:
        l, t, r, b = crop
        iw, ih = r - l, b - t
        crop_arg = f"{iw}x{ih}+{l}+{t}"
    else:
        crop_arg = None
    zoom = max(1.0, float(zoom))
    fit = min(max_w / iw, max_h / ih)
    scale = fit * zoom
    src_w = min(iw, max_w / scale)
    src_h = min(ih, max_h / scale)
    x0 = int(max(0.0, iw - src_w) * min(1.0, max(0.0, pan_x)))
    y0 = int(max(0.0, ih - src_h) * min(1.0, max(0.0, pan_y)))
    dest_w = max(1, min(max_w, round(src_w * scale)))
    dest_h = max(2, min(max_h, round(src_h * scale)))
    dest_h -= dest_h % 2
    cmd = [magick, str(path)]
    if crop_arg:
        cmd += ["-crop", crop_arg, "+repage"]
    cmd += [
        "-crop", f"{int(src_w)}x{int(src_h)}+{x0}+{y0}", "+repage",
        "-resize", f"{dest_w}x{dest_h}!",
        "-depth", "8", "rgb:-",
    ]
    raw = subprocess.run(cmd, check=True, capture_output=True, timeout=30).stdout
    pix = [(raw[i], raw[i + 1], raw[i + 2]) for i in range(0, len(raw) - 2, 3)]
    if len(pix) != dest_w * dest_h:
        raise RuntimeError("imagemagick returned the wrong number of pixels")
    return dest_w, dest_h, pix
