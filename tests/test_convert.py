"""Unit tests for the convert package."""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from convert.battery import is_battery_charging_icon, transform_battery_svg
from convert.color import hex_to_rgb, lighten_color, recolor_svg
from convert.engine import FrostEngine, frost_svg
from convert.geometry import compute_iou, element_bbox, path_bbox
from convert.overrides import IconOverrides
from convert.theme import ThemeGenerator, generate_theme
from convert.tile import find_tile, generate_tile_overlay


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


class TestBatteryModule(unittest.TestCase):
    def test_is_battery_charging_icon(self):
        self.assertTrue(is_battery_charging_icon(Path("status/22/battery-080-charging.svg")))
        self.assertTrue(is_battery_charging_icon(Path("status/symbolic/battery-good-charging-symbolic.svg")))
        self.assertTrue(is_battery_charging_icon(Path("status/22/battery_plugged.svg")))
        self.assertFalse(is_battery_charging_icon(Path("status/22/battery-080.svg")))
        self.assertFalse(is_battery_charging_icon(Path("apps/scalable/file-manager.svg")))

    def test_transform_battery_svg(self):
        sample_svg = (
            '<svg width="22" height="22" version="1.1" xmlns="http://www.w3.org/2000/svg">'
            '<path class="ColorScheme-Text" d="m3 7c-0.554 0-1 0.446-1 1v6c0 0.554 0.446 1 1 1h4.3906" fill="currentColor"/>'
            '<path class="ColorScheme-Text" d="m3 5c-1.662 0-3 1.338-3 3v6c0 1.662 1.338 3 3 3" fill="currentColor" opacity=".5"/>'
            '<path class="ColorScheme-Text" d="m6.1581 11.592c0 0.23467 0.19781 0.39805 0.43229 0.40752h2.9766l-1.5932 4.3047" fill="currentColor"/>'
            '</svg>'
        )
        transformed = transform_battery_svg(sample_svg)
        # Inside fill must be Apple green
        self.assertIn('fill="#30d158"', transformed)
        # Lightning bolt must be white and scaled slightly smaller (0.8x)
        self.assertIn('fill="#ffffff"', transformed)
        self.assertIn('scale(0.8)', transformed)
        # Shell must retain translucent ColorScheme-Text
        self.assertIn('class="ColorScheme-Text"', transformed)
        self.assertIn('opacity="0.5"', transformed)


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

    def test_rect_with_stroke_width(self):
        # Ensure stroke-width doesn't shadow width attribute
        svg = '<svg width="22" height="22"><rect width="22" height="22" rx="6" ry="6" fill="#123" stroke-width=".78571"/><circle cx="22" cy="10" r="8" fill="#ff5555"/></svg>'
        engine = FrostEngine(mode="clear")
        result = engine.transform(svg, fallback=False)
        self.assertIsNotNone(result)
        self.assertIn("mtf-rim", result)
        self.assertIn('width="21.759"', result)
        self.assertNotIn("#ff5555", result)

    def test_dark_mode_transform(self):
        svg = '<svg viewBox="0 0 64 64"><rect width="56" height="56" rx="13" fill="#123456"/><circle cx="32" cy="32" r="10" fill="#ff5555"/></svg>'
        engine = FrostEngine(mode="dark")
        result = engine.transform(svg, fallback=False)
        self.assertIsNotNone(result)
        self.assertIn("#242428", result)  # Dark glass background def
        self.assertIn("#ff5555", result)  # Preserves vivid colored glyph in dark mode

    def test_dark_mode_tile_recoloring(self):
        # Bluetooth icon with vivid blue gradient tile and white glyph
        svg = (
            '<svg width="32" height="32">'
            '<defs>'
            '<linearGradient id="a">'
            '<stop offset="0" stop-color="#3377f4"/>'
            '<stop offset="1" stop-color="#5194f5"/>'
            '</linearGradient>'
            '</defs>'
            '<rect width="28" height="28" x="2" y="2" rx="7" ry="7" fill="url(#a)"/>'
            '<path d="M9 2C5.122 2 2 5.122 2 9v14" opacity=".15" fill="#fff"/>'
            '<path fill="#fff" d="M15 9l4 4-4 4"/>'
            '</svg>'
        )
        engine = FrostEngine(mode="dark")
        result = engine.transform(svg, fallback=False)
        self.assertIsNotNone(result)
        self.assertIn("mtf-bg", result)
        self.assertIn("mtf-glyph", result)
        self.assertIn("#5194f5", result)
        self.assertIn("#3377f4", result)
        self.assertIn('fill="url(#mtf-glyph)"', result)
        self.assertNotIn('fill="#fff"', result)
        self.assertNotIn("M9 2C5.122", result)  # Old 32px rim stripped

    def test_dark_mode_semantic_fallback(self):
        # Display settings icon with dark gray tile and white glyph
        svg = (
            '<svg width="32" height="32">'
            '<defs>'
            '<linearGradient id="a">'
            '<stop offset="0" stop-color="#333333"/>'
            '<stop offset="1" stop-color="#424242"/>'
            '</linearGradient>'
            '</defs>'
            '<rect width="28" height="28" x="2" y="2" rx="7" ry="7" fill="url(#a)"/>'
            '<path fill="#fff" d="M10 10h12v12H10z"/>'
            '</svg>'
        )
        engine = FrostEngine(mode="dark")
        result = engine.transform(svg, fallback=False, icon_name="preferences-desktop-display")
        self.assertIsNotNone(result)
        self.assertIn("mtf-glyph", result)
        self.assertIn('fill="url(#mtf-glyph)"', result)
        # Should have Apple Displays Blue gradient stops
        self.assertIn("#5194f5", result)
        self.assertIn("#3377f4", result)

    def test_frosted_dark_mode_reduced_opacity(self):
        # Frosted dark mode has black frosted glass bg (.20 - .30) and etched glyph gradients like frosted light
        svg = (
            '<svg width="32" height="32">'
            '<defs>'
            '<linearGradient id="a">'
            '<stop offset="0" stop-color="#3377f4"/>'
            '<stop offset="1" stop-color="#5194f5"/>'
            '</linearGradient>'
            '</defs>'
            '<rect width="28" height="28" x="2" y="2" rx="7" ry="7" fill="url(#a)"/>'
            '<path fill="#fff" d="M15 9l4 4-4 4"/>'
            '</svg>'
        )
        engine = FrostEngine(mode="frosted-dark")
        result = engine.transform(svg, fallback=False)
        self.assertIsNotNone(result)
        self.assertIn('stop-color="#000000"', result)
        self.assertIn('stop-opacity=".20"', result)
        self.assertIn('stop-opacity=".25"', result)
        self.assertIn('stop-opacity=".30"', result)
        # Identical to frosted light: etched pearl glyph gradient, not colored mtf-glyph
        self.assertIn("mtf-g0", result)
        self.assertNotIn("mtf-glyph", result)

    def test_dark_mode_solid_tile(self):
        # MacTahoe-dark squircle tile bg must be 100% solid (no transparency)
        import re
        svg = (
            '<svg width="32" height="32">'
            '<rect width="28" height="28" x="2" y="2" rx="7" ry="7" fill="#123456"/>'
            '<path fill="#fff" d="M15 9l4 4-4 4"/>'
            '</svg>'
        )
        engine = FrostEngine(mode="dark")
        result = engine.transform(svg, fallback=False, icon_name="preferences-desktop-sound")
        self.assertIsNotNone(result)
        bg_match = re.search(r'<linearGradient id="mtf-bg"[^>]*>(.*?)</linearGradient>', result, re.S)
        self.assertIsNotNone(bg_match)
        bg_grad = bg_match.group(1)
        self.assertIn('stop-opacity="1"', bg_grad)
        self.assertNotIn('stop-opacity="0.', bg_grad)
        self.assertNotIn('stop-opacity=".', bg_grad)
        self.assertIn("#242428", bg_grad)

    def test_dark_mode_preserves_multicolor_glyph(self):
        # App icon with tile and multi-colored glyph (e.g. Chrome, Firefox)
        svg = (
            '<svg viewBox="0 0 64 64">'
            '<rect width="56" height="56" rx="13" fill="#3377f4"/>'
            '<path fill="#ea4335" d="M20 20h10v10H20z"/>'
            '<path fill="#34a853" d="M30 30h10v10H30z"/>'
            '</svg>'
        )
        engine = FrostEngine(mode="dark")
        result = engine.transform(svg, fallback=False)
        self.assertIsNotNone(result)
        self.assertIn("#ea4335", result)
        self.assertIn("#34a853", result)
        self.assertNotIn("mtf-glyph", result)

    def test_dark_mode_finder_override(self):
        override_dark = IconOverrides.get_override_content(Path("apps/scalable/file-manager.svg"), mode="dark")
        self.assertIsNotNone(override_dark)
        self.assertIn("#3ab3ff", override_dark)  # Blue right face
        self.assertIn("#242428", override_dark)  # Solid dark squircle
        self.assertIn('stop-opacity="1"', override_dark)

        override_frosted = IconOverrides.get_override_content(Path("apps/scalable/file-manager.svg"), mode="frosted-dark")
        self.assertIsNotNone(override_frosted)
        self.assertIn("#000000", override_frosted)  # Black glass left face
        self.assertIn('stop-opacity="0.2"', override_frosted)
        self.assertIn("#fff", override_frosted)  # Pearl/white right face


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
        (self.src / "status" / "24" / "battery-good-charging.svg").write_text(
            '<svg width="24" height="24">'
            '<path d="m4.5234 9c-0.29007 0-0.52344 0.24253-0.52344 0.54492v4.9102" fill="#f2f2f2"/>'
            '<path d="m10.834 8-3.334 5h3l-0.75 3h0.41602l3.334-5h-3l0.75-3z" fill="#f2f2f2"/>'
            '<path d="m4 7c-1.108 0-2 0.892-2 2v6" fill="#f2f2f2"/>'
            '</svg>',
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

        # Check that battery charging icon was transformed into green fill + white bolt
        battery_content = (self.dest / "status" / "24" / "battery-good-charging.svg").read_text()
        self.assertIn('fill="#30d158"', battery_content)
        self.assertIn('fill="#ffffff"', battery_content)


if __name__ == "__main__":
    unittest.main()
