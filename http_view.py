"""Loopback HTTP gallery. Luvus is not a graphics terminal; a browser is.

Binds 127.0.0.1 only. Serves only files listed in the gallery state, and only
if they still pass is_image(). A request for anything else is 404.
"""

from __future__ import annotations

import json
import os
import signal
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from render import EXTS, is_image
from state import dir as state_dir

TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
}

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Image Preview</title>
<style>
  html, body { margin: 0; height: 100%; background: #111; color: #eee;
               font: 14px/1.4 ui-sans-serif, system-ui, sans-serif; }
  #stage { height: calc(100% - 96px); display: flex; align-items: center;
           justify-content: center; }
  #stage img { max-width: 100%; max-height: 100%; object-fit: contain; }
  #bar { height: 96px; display: flex; gap: 8px; padding: 8px 12px;
         overflow-x: auto; background: #1a1a1a; align-items: center; }
  #bar img { height: 80px; cursor: pointer; opacity: .55; border: 2px solid transparent; }
  #bar img.on { opacity: 1; border-color: #eee; }
  #name { position: fixed; top: 8px; left: 12px; background: #000a;
          padding: 4px 8px; font-variant-numeric: tabular-nums; }
</style>
</head>
<body>
<div id="name"></div>
<div id="stage"><img id="main" alt=""></div>
<div id="bar"></div>
<script>
const files = FILES;
const params = new URLSearchParams(location.search);
const n = parseInt(params.get('n') || '', 10);
let i = (n >= 1) ? n - 1 : INDEX;
const main = document.getElementById('main');
const bar = document.getElementById('bar');
const name = document.getElementById('name');
files.forEach((f, n) => {
  const t = document.createElement('img');
  t.src = '/img/' + n;
  t.alt = f;
  t.onclick = () => show(n);
  bar.appendChild(t);
});
function show(n) {
  i = (n + files.length) % files.length;
  main.src = '/img/' + i + '?t=' + Date.now();
  name.textContent = (i+1) + '/' + files.length + '  ' + files[i];
  [...bar.children].forEach((el, k) => el.classList.toggle('on', k === i));
}
document.addEventListener('keydown', e => {
  if (e.key === 'ArrowRight' || e.key === 'n') show(i+1);
  if (e.key === 'ArrowLeft' || e.key === 'p') show(i-1);
  if (e.key >= '1' && e.key <= '9') show(parseInt(e.key, 10) - 1);
});
show(i);
</script>
</body>
</html>
"""


def gallery_path() -> Path:
    return state_dir() / "gallery.json"


def port_path() -> Path:
    return state_dir() / "httpd.port"


def pid_path() -> Path:
    return state_dir() / "httpd.pid"


def load_gallery() -> dict:
    try:
        data = json.loads(gallery_path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {"files": [], "labels": [], "index": 0}
    files: list[str] = []
    labels: list[str] = []
    raw_labels = list(data.get("labels") or [])
    for i, raw in enumerate(data.get("files") or []):
        p = Path(raw)
        if not is_image(p):
            continue
        files.append(str(p.resolve()))
        if i < len(raw_labels) and raw_labels[i]:
            labels.append(str(raw_labels[i]))
        else:
            labels.append(p.name)
    index = int(data.get("index") or 0)
    if files:
        index = max(0, min(index, len(files) - 1))
    else:
        index = 0
    return {"files": files, "labels": labels, "index": index}


def save_gallery(files: list[Path], index: int, labels: list[str] | None = None) -> None:
    resolved = [p.resolve() for p in files]
    if labels is None:
        labels = [p.name for p in resolved]
    if len(labels) != len(resolved):
        raise ValueError("labels must match files")
    payload = {
        "files": [str(p) for p in resolved],
        "labels": labels,
        "index": index,
    }
    gallery_path().write_text(json.dumps(payload), encoding="utf-8")


def siblings_of(path: Path) -> list[Path]:
    parent = path.parent
    try:
        names = sorted(
            p for p in parent.iterdir()
            if p.is_file() and p.suffix.lower() in EXTS
        )
    except OSError:
        names = [path]
    return names or [path]


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:  # noqa: ARG002
        return

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            self._page()
            return
        if parsed.path == "/health":
            self._send(200, b"ok", "text/plain")
            return
        if parsed.path.startswith("/img/"):
            self._image(parsed.path)
            return
        self._send(404, b"not found", "text/plain")

    def _page(self) -> None:
        gal = load_gallery()
        labels = gal.get("labels") or [Path(f).name for f in gal["files"]]
        html = (
            PAGE.replace("FILES", json.dumps(labels, ensure_ascii=False))
            .replace("INDEX", str(gal["index"]))
        )
        self._send(200, html.encode(), "text/html; charset=utf-8")

    def _image(self, path: str) -> None:
        gal = load_gallery()
        try:
            n = int(path.rsplit("/", 1)[-1])
            src = Path(gal["files"][n])
        except (ValueError, IndexError):
            self._send(404, b"no such image", "text/plain")
            return
        if not is_image(src):
            self._send(404, b"not an image", "text/plain")
            return
        try:
            body = src.read_bytes()
        except OSError:
            self._send(404, b"unreadable", "text/plain")
            return
        self._send(200, body, TYPES.get(src.suffix.lower(), "application/octet-stream"))

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def serve() -> None:
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = httpd.server_address[1]
    port_path().write_text(str(port) + "\n", encoding="utf-8")
    pid_path().write_text(str(os.getpid()) + "\n", encoding="utf-8")

    def stop(_signum, _frame):  # noqa: ARG001
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    httpd.serve_forever()


def running_port() -> int | None:
    try:
        port = int(port_path().read_text(encoding="utf-8").strip())
        pid = int(pid_path().read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None
    try:
        os.kill(pid, 0)
    except OSError:
        return None
    try:
        import urllib.request
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=0.4) as resp:
            if resp.status == 200:
                return port
    except OSError:
        return None
    return None


def ensure() -> int:
    port = running_port()
    if port is not None:
        return port
    log = open(state_dir() / "httpd.log", "ab", buffering=0)
    subprocess = __import__("subprocess")
    subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), "--serve"],
        cwd=str(Path(__file__).resolve().parent),
        stdin=subprocess.DEVNULL,
        stdout=log,
        stderr=log,
        start_new_session=True,
        env={**os.environ},
    )
    for _ in range(50):
        time.sleep(0.05)
        port = running_port()
        if port is not None:
            return port
    raise RuntimeError("image preview httpd did not start")


if __name__ == "__main__":
    if "--serve" in sys.argv:
        serve()
    else:
        print("usage: http_view.py --serve", file=sys.stderr)
        raise SystemExit(2)
