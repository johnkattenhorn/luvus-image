"""The renderer must refuse a text file, paint a PNG, and zoom into a half."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from render import halfblocks, is_image, quadrant_box, window  # noqa: E402


class Render(unittest.TestCase):
    def test_a_text_file_is_not_an_image(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            p = Path(raw) / "notes.txt"
            p.write_text("not an image\n")
            self.assertFalse(is_image(p))

    def test_a_png_is_an_image(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            p = self._red_png(Path(raw))
            self.assertTrue(is_image(p))

    def test_halfblocks_of_a_red_png_contain_truecolour(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            p = self._red_png(Path(raw))
            text = halfblocks(p, cols=8, rows=4)
            self.assertIn("\x1b[38;2;", text)
            self.assertIn("▀", text)
            self.assertIn("38;2;255;0;0", text)

    def test_halfblocks_of_a_text_file_fail(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            p = Path(raw) / "notes.txt"
            p.write_text("hello")
            with self.assertRaises(Exception):
                halfblocks(p, cols=8, rows=4)

    def test_fit_stays_inside_the_box(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            p = self._red_png(Path(raw), size=32)
            w, h, pix = window(p, max_w=8, max_h=8)
            self.assertLessEqual(w, 8)
            self.assertLessEqual(h, 8)
            self.assertEqual(len(pix), w * h)

    def test_zoom_into_the_red_half_is_red_not_blue(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            p = self._split_png(Path(raw))
            _, _, left = window(p, 16, 16, zoom=2.0, pan_x=0.0, pan_y=0.5)
            _, _, right = window(p, 16, 16, zoom=2.0, pan_x=1.0, pan_y=0.5)
            self.assertGreater(self._mean_r(left), 200)
            self.assertLess(self._mean_b(left), 40)
            self.assertGreater(self._mean_b(right), 200)
            self.assertLess(self._mean_r(right), 40)

    def test_quadrant_1_is_the_top_left(self) -> None:
        self.assertEqual(quadrant_box((100, 80), 1), (0, 0, 50, 40))
        self.assertEqual(quadrant_box((100, 80), 4), (50, 40, 100, 80))

    def _red_png(self, tmp: Path, size: int = 4) -> Path:
        from PIL import Image

        p = tmp / "red.png"
        Image.new("RGB", (size, size), (255, 0, 0)).save(p)
        return p

    def _split_png(self, tmp: Path) -> Path:
        from PIL import Image

        p = tmp / "split.png"
        im = Image.new("RGB", (32, 16), (0, 0, 255))
        for x in range(16):
            for y in range(16):
                im.putpixel((x, y), (255, 0, 0))
        im.save(p)
        return p

    def _mean_r(self, pix) -> float:
        return sum(p[0] for p in pix) / len(pix)

    def _mean_b(self, pix) -> float:
        return sum(p[2] for p in pix) / len(pix)


if __name__ == "__main__":
    unittest.main()
