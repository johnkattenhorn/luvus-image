"""The loopback gallery must serve a PNG and refuse a missing index."""

from __future__ import annotations

import os
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class DockSkip(unittest.TestCase):
    def test_same_workspace_is_skipped_on_pane_focus(self) -> None:
        import dock

        os.environ.pop("LUVUS_MODULE_ACTION_ID", None)
        os.environ["LUVUS_MODULE_EVENT"] = "pane.focused"
        root = Path(tempfile.mkdtemp())
        orig = dock.last_root
        dock.last_root = lambda: str(root.resolve())  # type: ignore[method-assign]
        try:
            self.assertFalse(dock.should_scan(root))
            os.environ["LUVUS_MODULE_ACTION_ID"] = "refresh"
            self.assertTrue(dock.should_scan(root))
        finally:
            dock.last_root = orig  # type: ignore[method-assign]
            os.environ.pop("LUVUS_MODULE_ACTION_ID", None)

    def test_runs_dir_is_not_listed(self) -> None:
        from scan import labelled

        root = Path(tempfile.mkdtemp())
        (root / "looks").mkdir()
        (root / "runs").mkdir()
        from PIL import Image
        Image.new("RGB", (2, 2), (1, 2, 3)).save(root / "looks" / "sheet.png")
        Image.new("RGB", (2, 2), (1, 2, 3)).save(root / "runs" / "out.png")
        items = labelled(root, depth=4, limit=40)
        names = [p.name for p, _ in items]
        self.assertEqual(names, ["sheet.png"])

    def test_a_new_folder_is_scanned(self) -> None:
        import dock

        os.environ.pop("LUVUS_MODULE_ACTION_ID", None)
        os.environ["LUVUS_MODULE_EVENT"] = "pane.focused"
        a = Path(tempfile.mkdtemp())
        b = Path(tempfile.mkdtemp())
        orig = dock.last_root
        dock.last_root = lambda: str(a.resolve())  # type: ignore[method-assign]
        try:
            self.assertTrue(dock.should_scan(b))
        finally:
            dock.last_root = orig  # type: ignore[method-assign]


class Http(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        os.environ["LUVUS_MODULE_STATE_DIR"] = str(self.tmp / "state")
        (self.tmp / "state").mkdir()
        from http_view import Handler, save_gallery

        self.save_gallery = save_gallery
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()

    def test_gallery_drops_a_text_file(self) -> None:
        from http_view import load_gallery
        from render import is_image

        txt = self.tmp / "notes.txt"
        txt.write_text("nope")
        png = self._png(self.tmp / "a.png")
        self.save_gallery([txt, png], 0)
        gal = load_gallery()
        self.assertEqual(gal["files"], [str(png.resolve())])
        self.assertFalse(is_image(txt))

    def test_img_zero_is_the_png_bytes(self) -> None:
        png = self._png(self.tmp / "a.png")
        self.save_gallery([png], 0)
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/img/0") as resp:
            body = resp.read()
            self.assertEqual(resp.status, 200)
            self.assertEqual(resp.headers.get_content_type(), "image/png")
        self.assertEqual(body, png.read_bytes())
        self.assertTrue(body.startswith(b"\x89PNG"))

    def test_img_of_a_missing_index_is_404(self) -> None:
        png = self._png(self.tmp / "a.png")
        self.save_gallery([png], 0)
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(f"http://127.0.0.1:{self.port}/img/9")
        self.assertEqual(caught.exception.code, 404)

    def test_dock_row_n_is_browser_thumb_n(self) -> None:
        from scan import labelled

        a = self._png(self.tmp / "older.png")
        b = self._png(self.tmp / "newer.png")
        os.utime(a, (1, 1))
        os.utime(b, (2, 2))
        items = labelled(self.tmp, depth=1, limit=10)
        files = [p for p, _ in items]
        labels = [lab for _, lab in items]
        self.assertEqual(files[0], b.resolve())
        self.assertTrue(labels[0].startswith("1  "))
        self.assertTrue(labels[1].startswith("2  "))
        self.save_gallery(files, 1, labels)
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/?n=2") as resp:
            body = resp.read().decode()
        self.assertIn("let i = (n >= 1) ? n - 1 :", body)
        self.assertIn(labels[1], body)

    def test_page_names_the_file(self) -> None:
        png = self._png(self.tmp / "sheet.png")
        self.save_gallery([png], 0)
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/") as resp:
            body = resp.read().decode()
            self.assertEqual(resp.status, 200)
        self.assertIn("sheet.png", body)
        self.assertIn('<img id="main"', body)

    def _png(self, path: Path) -> Path:
        from PIL import Image
        Image.new("RGB", (4, 4), (255, 0, 0)).save(path)
        return path


if __name__ == "__main__":
    unittest.main()
