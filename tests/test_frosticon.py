"""Unit tests for the frosticon package."""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from frosticon.color import hex_to_rgb, lighten_color, recolor_svg
from frosticon.engine import FrostEngine, frost_svg
from frosticon.geometry import compute_iou, element_bbox, path_bbox
from frosticon.overrides import IconOverrides
from frosticon.theme import ThemeGenerator, generate_theme
from frosticon.tile import find_tile, generate_tile_overlay


class TestColorModule(unittest.TestCase):
    def test_hex_to_rgb(self):
        self.assertEqual(hex_to_rgb("#ffffff"), (255, 255, 255))
        self.assertEqual(hex_to_rgb("#000"), (0, 0, 0))
        self.assertEqual(hex_to_rgb("ff0000"), (255, 0, 0))
        self.assertIsNone(hex_to_rgb("invalid"))

    def test_lighten_color(self):
        result = lighten_color(1.0, 1.0, 1.0)
        self.assertTrue(result.startswith("#"))
        self.assertEqual(len(result), 7)

    def test_recolor_svg(self):
        sample = '<svg><path fill="#ff0000" stroke="#0000ff"/></svg>'
        recolored = recolor_svg(sample)
        self.assertNotIn("#ff0000", recolored)


class TestGeometryModule(unittest.TestCase):
    def test_path_bbox(self):
        d = "M 10 10 L 20 20 Z"
        bbox = path_bbox(d)
        self.assertIsNotNone(bbox)
        self.assertEqual(bbox, (10.0, 10.0, 20.0, 20.0))

    def test_element_bbox(self):
        rect = '<rect x="5" y="10" width="50" height="40"/>'
        bbox = element_bbox(rect)
        self.assertEqual(bbox, (5.0, 10.0, 55.0, 50.0))

    def test_compute_iou(self):
        box1 = (0.0, 0.0, 10.0, 10.0)
        box2 = (0.0, 0.0, 10.0, 10.0)
        self.assertAlmostEqual(compute_iou(box1, box2), 1.0)

        box3 = (20.0, 20.0, 30.0, 30.0)
        self.assertAlmostEqual(compute_iou(box1, box3), 0.0)


class TestTileModule(unittest.TestCase):
    def test_find_tile_rect(self):
        svg = '<svg viewBox="0 0 64 64"><rect width="56" height="56" rx="13" fill="#ff0000"/></svg>'
        tile = find_tile(svg)
        self.assertIsNotNone(tile)
        self.assertIn('width="56"', tile)

    def test_generate_tile_overlay(self):
        tile = '<rect width="56" height="56" rx="13"/>'
        overlay = generate_tile_overlay(tile, "mtf", 1.0)
        self.assertIn("mtf-rim", overlay)
        self.assertIn("mtf-sheen", overlay)
        self.assertIn("mtf-shade", overlay)


class TestOverridesModule(unittest.TestCase):
    def test_finder_override(self):
        p = Path("scalable/apps/scalable/file-manager.svg")  # nested
        p2 = Path("/usr/share/icons/MacTahoe/apps/scalable/file-manager.svg")
        content = IconOverrides.get_override_content(p2, "clear")
        self.assertIsNotNone(content)
        self.assertIn("linearGradient", content)

        # In tint mode, Finder is not overridden
        self.assertIsNone(IconOverrides.get_override_content(p2, "tint"))


class TestEngineModule(unittest.TestCase):
    def test_transform_with_tile(self):
        svg = (
            '<svg viewBox="0 0 64 64">'
            '<rect width="56" height="56" rx="13" fill="#123456"/>'
            '<circle cx="32" cy="32" r="10" fill="#ffffff"/>'
            '</svg>'
        )
        engine = FrostEngine(mode="clear")
        result = engine.transform(svg)
        self.assertIsNotNone(result)
        self.assertIn("mtf-bg", result)
        self.assertIn("mtf-rim", result)

    def test_transform_32px_preferences_icon(self):
        # 32x32 SVG without viewBox (common in preferences and categories)
        svg = (
            '<svg width="32" height="32">'
            '<rect width="28" height="28" x="2" y="2" rx="7" ry="7" fill="url(#a)"/>'
            '<path fill="#fff" d="M10 10h12v12H10z"/>'
            '</svg>'
        )
        engine = FrostEngine(mode="clear")
        result = engine.transform(svg)
        self.assertIsNotNone(result)
        self.assertIn("mtf-bg", result)
        self.assertIn("mtf-rim", result)

    def test_transform_fallback(self):
        svg = (
            '<svg viewBox="0 0 64 64">'
            '<circle cx="32" cy="32" r="20" fill="#ff0000"/>'
            '</svg>'
        )
        engine = FrostEngine(mode="clear")
        result = engine.transform(svg, fallback=True)
        self.assertIsNotNone(result)
        self.assertIn("mtf-bg", result)

    def test_22px_rect_tile(self):
        svg = '<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22"><rect width="22" height="22" fill="url(#a)" rx="6" ry="6"/><path fill="#fff" d="M5 5h12v12H5z"/></svg>'
        engine = FrostEngine(mode="clear")
        result = engine.transform(svg, fallback=False)
        self.assertIsNotNone(result)
        self.assertIn("mtf-rim", result)
        self.assertIn("mtf-bg", result)

    def test_32px_path_tile(self):
        svg = '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32"><path fill="#fff" d="M30 8.501A6.486 6.486 0 0 0 23.5 2H8.501a6.486 6.486 0 0 0-6.5 6.5v15a6.486 6.486 0 0 0 6.5 6.5H23.5a6.486 6.486 0 0 0 6.5-6.5z"/><circle cx="16" cy="16" r="5" fill="#f00"/></svg>'
        engine = FrostEngine(mode="clear")
        result = engine.transform(svg, fallback=False)
        self.assertIsNotNone(result)
        self.assertIn("mtf-rim", result)
        self.assertIn("mtf-bg", result)


class TestThemeGenerator(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.src = Path(self.tmp_dir) / "source-theme"
        self.dest = Path(self.tmp_dir) / "dest-theme"

        # Create mock theme structure
        (self.src / "apps" / "scalable").mkdir(parents=True)
        (self.src / "apps" / "scalable" / "test-app.svg").write_text(
            '<svg viewBox="0 0 64 64">'
            '<rect width="56" height="56" rx="13" fill="#123456"/>'
            '</svg>',
            encoding="utf-8",
        )
        (self.src / "apps" / "scalable" / "file-manager.svg").write_text(
            '<svg viewBox="0 0 64 64"><rect width="56" height="56"/></svg>',
            encoding="utf-8",
        )
        (self.src / "preferences" / "32").mkdir(parents=True)
        (self.src / "preferences" / "32" / "preferences-desktop-display.svg").write_text(
            '<svg width="32" height="32">'
            '<rect width="28" height="28" x="2" y="2" rx="7" ry="7" fill="url(#a)"/>'
            '</svg>',
            encoding="utf-8",
        )
        (self.src / "status" / "24").mkdir(parents=True)
        (self.src / "status" / "24" / "network-wireless-100.svg").write_text(
            '<svg width="24" height="24"><path d="M0 0h24v24H0z"/></svg>',
            encoding="utf-8",
        )
        (self.src / "index.theme").write_text("[Icon Theme]\nName=MockTheme\n", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    def test_theme_generation(self):
        generator = ThemeGenerator(
            src=self.src,
            dest=self.dest,
            mode="clear",
            cache=False,
            use_overrides=True,
        )
        stats = generator.generate()
        self.assertGreaterEqual(stats.converted, 1)
        self.assertEqual(stats.overridden, 1)  # Finder file-manager.svg was overridden!
        self.assertTrue((self.dest / "apps" / "scalable" / "test-app.svg").is_file())
        self.assertTrue((self.dest / "apps" / "scalable" / "file-manager.svg").is_file())
        self.assertTrue((self.dest / "preferences" / "32" / "preferences-desktop-display.svg").is_file())
        self.assertTrue((self.dest / "status" / "24" / "network-wireless-100.svg").is_file())
        self.assertTrue((self.dest / "index.theme").is_file())

        # Check that preferences icon was converted into frosted glass
        pref_content = (self.dest / "preferences" / "32" / "preferences-desktop-display.svg").read_text()
        self.assertIn("mtf-bg", pref_content)

        # Check that status tray icon was preserved untouched
        status_content = (self.dest / "status" / "24" / "network-wireless-100.svg").read_text()
        self.assertNotIn("mtf-bg", status_content)


if __name__ == "__main__":
    unittest.main()
