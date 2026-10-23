"""Core frosted glass SVG transformation engine."""

import colorsys
import re
from typing import Optional
from .color import (
    extract_tile_colors,
    foreground_has_vivid_colors,
    hex_to_rgb,
    recolor_svg,
)
from .constants import SEMANTIC_ICON_COLORS
from .defs import (
    apply_glyph_gradients,
    build_dark_glyph_gradient,
    build_frost_defs,
    ensure_fill,
    strip_dangling_uses,
)
from .tile import (
    find_tile,
    generate_tile_overlay,
    remove_extra_path_tiles,
    replace_tile,
    strip_dark_backgrounds,
    strip_tile_duplicates,
    sub_outside_defs,
    tile_scale_for,
)


class FrostEngine:
    """Configurable processor for transforming standard SVG icons into frosted glass."""

    def __init__(self, mode: str = "light", base_prefix: str = "mtf"):
        """Initialize engine with mode ('light', 'dark', 'frosted-dark', 'clear', or 'tint') and base filter ID prefix."""
        valid_modes = ("light", "clear", "dark", "frosted-dark", "dark-frosted", "tint")
        if mode not in valid_modes:
            raise ValueError(f"Invalid mode '{mode}'. Choose from {valid_modes}.")
        self.mode = "clear" if mode == "light" else mode
        self.base_prefix = base_prefix

    def _resolve_prefix(self, text: str) -> str:
        """Resolve a non-colliding ID prefix for SVG filters and gradients."""
        prefix = self.base_prefix
        while f'id="{prefix}-bg"' in text:
            prefix += "x"
        return prefix

    def transform_fallback(self, text: str, icon_name: str = "") -> str:
        """Fallback transformation when no existing tile squircle is identified."""
        prefix = self._resolve_prefix(text)

        viewbox = re.search(r'viewBox="[\d.\-]+ [\d.\-]+ ([\d.]+) ([\d.]+)"', text)
        if viewbox:
            width = float(viewbox.group(1))
        else:
            wm = re.search(r'\bwidth="([\d.]+)"', text)
            width = float(wm.group(1)) if wm else 64.0

        # Remove raster images and dangling use tags
        text = re.sub(r"<image\b[^>]*/>", "", text)
        text = strip_dangling_uses(text)

        # Remove background rects taking >= 85% of dimensions
        def rect_repl(match: re.Match) -> str:
            tag = match.group(0)
            if 'fill="none"' in tag:
                return tag
            values = dict(re.findall(r'(?<!-)\b(x|y|width|height)="([\d.]+)"', tag))
            if "width" not in values or "height" not in values:
                return tag
            w, h = float(values["width"]), float(values["height"])
            if w >= 0.85 * width and h >= 0.85 * width:
                return ""
            return tag

        text = sub_outside_defs(r"<rect\b[^>]*?/?>", rect_repl, text)

        # Remove transformed rect cards
        def transformed_repl(match: re.Match) -> str:
            tag = match.group(0)
            values = dict(re.findall(r'(?<!-)\b(width|height)="([\d.]+)"', tag))
            w = float(values.get("width", 0))
            h = float(values.get("height", 0))
            if 0.8 * width <= w <= 0.9 * width and 0.8 * width <= h <= 0.9 * width:
                return ""
            return tag

        text = sub_outside_defs(r'<rect\b[^>]*\btransform="[^"]*"[^>]*?/?>', transformed_repl, text)
        text = re.sub(r'<path\b[^>]*\bd="M1\.559 [\d.]+h60\.882[vV][\d.]+H1\.559z"[^>]*?/>', "", text)

        # Remove known MacTahoe path tiles
        def path_repl(match: re.Match) -> str:
            tag = match.group(0)
            d = re.search(r'\bd="([^"]+)"', tag)
            if not d:
                return tag
            val = d.group(1)
            starts = (
                val.startswith("M17")
                or val.startswith("M47")
                or val.startswith("m5.3604")
                or val.startswith("m5.3603")
            )
            markers = (
                "13.002", "12.973", "h29.996", "9.822", "3.999",
                "C54.174", "13 13", "12.974", "12.9",
            )
            if starts and any(m in val for m in markers):
                return ""
            return tag

        text = sub_outside_defs(r"<path\b[^>]*?/>", path_repl, text)

        scale = width / 64.0
        tile = (
            f'<rect x="{4 * scale:.3f}" y="{4 * scale:.3f}" width="{56 * scale:.3f}" '
            f'height="{56 * scale:.3f}" rx="{13 * scale:.3f}" fill="url(#{prefix}-bg)"/>'
        )
        text = strip_dark_backgrounds(text, tile)
        text = strip_tile_duplicates(text, tile, gradient_only=True)

        dark_glyph_gradient = None
        if self.mode in ("clear", "frosted-dark", "dark-frosted"):
            text = apply_glyph_gradients(recolor_svg(text), prefix)
            text = ensure_fill(text, prefix)
        elif self.mode == "dark":
            target_colors = None
            if icon_name:
                for pattern, cols in SEMANTIC_ICON_COLORS:
                    if pattern.search(icon_name):
                        target_colors = cols
                        break
            if target_colors and not foreground_has_vivid_colors(text, ""):
                glyph_grad_id = f"{prefix}-glyph"
                dark_glyph_gradient = build_dark_glyph_gradient(prefix, target_colors[0], target_colors[1])

                def recolor_fallback_glyph(match: re.Match) -> str:
                    tag = match.group(0)
                    tag = re.sub(
                        r'\bfill="(?:#fff|#ffffff|#fffff9|#fcfcfc|#f5f5f5|#f0f0f0|#dedede|#eee|#d0d0d0|#bebebe)"',
                        f'fill="url(#{glyph_grad_id})"',
                        tag,
                        flags=re.I,
                    )
                    tag = re.sub(
                        r'fill:(?:#fff|#ffffff|#fffff9|#fcfcfc|#f5f5f5|#f0f0f0|#dedede|#eee|#d0d0d0|#bebebe)',
                        f'fill:url(#{glyph_grad_id})',
                        tag,
                        flags=re.I,
                    )
                    if f'url(#{glyph_grad_id})' in tag and 'fill="#363636"' in tag:
                        tag = tag.replace('fill="#363636"', '')
                    tag = re.sub(
                        r'\bstroke="(?:#fff|#ffffff|#dedede)"',
                        f'stroke="url(#{glyph_grad_id})"',
                        tag,
                        flags=re.I,
                    )
                    return tag

                text = sub_outside_defs(r"<[^>]+>", recolor_fallback_glyph, text)

        overlay = generate_tile_overlay(tile, prefix, scale)
        defs = build_frost_defs(prefix, scale, mode=self.mode, dark_glyph_gradient=dark_glyph_gradient)

        svg_match = re.search(r"<svg\b[^>]*>", text)
        start = svg_match.end() if svg_match else 0
        draw = re.compile(
            r"<(?:defs\b.*?</defs>|path\b|rect\b|circle\b|ellipse\b|polygon\b|polyline\b|g\b|image\b|text\b)",
            re.S,
        )
        insert_at = start
        for match in draw.finditer(text, start):
            if match.group(0).startswith("<defs"):
                continue
            insert_at = match.start()
            break

        block = "<defs>" + defs + "</defs>" + tile + overlay
        return text[:insert_at] + block + text[insert_at:]

    def transform(self, text: str, fallback: bool = False, icon_name: str = "") -> Optional[str]:
        """Transform SVG text into frosted glass format.

        Returns the transformed SVG string, or None if no tile was found and
        fallback is False.
        """
        tile = find_tile(text)
        if tile is None:
            return self.transform_fallback(text, icon_name=icon_name) if fallback else None

        prefix = self._resolve_prefix(text)

        # Detect tile colors and semantic fallbacks for dark mode
        tile_colors = (
            extract_tile_colors(text, tile)
            if self.mode == "dark"
            else []
        )
        if self.mode == "dark" and not tile_colors and icon_name:
            for pattern, cols in SEMANTIC_ICON_COLORS:
                if pattern.search(icon_name):
                    tile_colors = list(cols)
                    break

        target_colors = None
        if tile_colors:
            if len(tile_colors) == 1:
                target_colors = (tile_colors[0], tile_colors[0])
            else:
                c1, c2 = tile_colors[0], tile_colors[-1]
                rgb1, rgb2 = hex_to_rgb(c1), hex_to_rgb(c2)
                if rgb1 and rgb2:
                    _, l1, _ = colorsys.rgb_to_hls(*(v / 255.0 for v in rgb1))
                    _, l2, _ = colorsys.rgb_to_hls(*(v / 255.0 for v in rgb2))
                    top = c1 if l1 >= l2 else c2
                    bottom = c2 if l1 >= l2 else c1
                else:
                    top, bottom = c1, c2
                target_colors = (top, bottom)

        new_tile = re.sub(r'fill="[^"]*"', f'fill="url(#{prefix}-bg)"', tile, count=1)
        new_tile = re.sub(r'fill:[^;"]+', f"fill:url(#{prefix}-bg)", new_tile)
        if "fill=" not in new_tile and "fill:" not in new_tile:
            new_tile = new_tile.replace("/>", f' fill="url(#{prefix}-bg)"/>')

        viewbox = re.search(r'viewBox="[\d.\-]+ [\d.\-]+ ([\d.]+) ', text)
        if viewbox:
            viewbox_width = float(viewbox.group(1))
        else:
            wm = re.search(r'<svg\b[^>]*\bwidth="([\d.]+)"', text)
            viewbox_width = float(wm.group(1)) if wm else 64.0
        scale = viewbox_width / 64.0

        if tile.startswith("<rect"):
            def rect_geom(tag: str) -> tuple:
                attrs = dict(re.findall(r'(?<!-)\b(x|y|width|height|rx|ry)="([\d.]+)"', tag))
                return tuple(
                    round(float(attrs.get(k, 0)), 3) for k in ("x", "y", "width", "height", "rx", "ry")
                )

            geom = rect_geom(tile)
            split = text.find(tile) + len(tile)
            head, tail = text[:split], text[split:]

            def drop_duplicate(match: re.Match) -> str:
                tag = match.group(0)
                if "filter=" in tag or "filter:" in tag or 'fill="none"' in tag:
                    return tag
                return "" if rect_geom(tag) == geom else tag

            text = head + re.sub(r"<rect\b[^>]*?/?>", drop_duplicate, tail)

        text = re.sub(r"<image\b[^>]*/>", "", text)
        text = strip_dangling_uses(text)
        text = re.sub(r'<path\b[^>]*\bd="M1\.559 [\d.]+h60\.882[vV][\d.]+H1\.559z"[^>]*?/>', "", text)

        if tile.startswith("<path"):
            text = remove_extra_path_tiles(text, tile)

        text = re.sub(r'<path\b[^>]*\bd="M18 4C10\.244[^"]*"[^>]*?/>', "", text)
        text = re.sub(r'<path\b[^>]*\bd="M17 4\.6h30[^"]*"[^>]*?/>', "", text)
        text = re.sub(r'<path\b[^>]*\bd="M9 2C5\.122[^"]*"[^>]*?/>', "", text)

        if re.search(r'width="14\.8', tile):
            text = re.sub(
                r"<(?:rect|path|circle|ellipse)\b[^>]*transform=\"scale\(\.0?2645[0-9]*\)\"[^>]*?/>",
                "",
                text,
            )

        text = replace_tile(text, tile, new_tile)
        text = strip_tile_duplicates(text, tile)

        dark_glyph_gradient = None
        if self.mode in ("clear", "frosted-dark", "dark-frosted"):
            text = strip_dark_backgrounds(text, tile, tile_scale_for(tile, viewbox_width))
            text = apply_glyph_gradients(recolor_svg(text), prefix)
            text = ensure_fill(text, prefix)
        elif self.mode == "dark":
            if target_colors and not foreground_has_vivid_colors(text, new_tile):
                glyph_grad_id = f"{prefix}-glyph"
                dark_glyph_gradient = build_dark_glyph_gradient(prefix, target_colors[0], target_colors[1])

                def recolor_glyph(match: re.Match) -> str:
                    tag = match.group(0)
                    if tag.startswith("<defs") or tag.startswith("</defs"):
                        return tag
                    tag = re.sub(
                        r'\bfill="(?:#fff|#ffffff|#fffff9|#fcfcfc|#f5f5f5|#f0f0f0|#dedede|#eee|#d0d0d0|#bebebe)"',
                        f'fill="url(#{glyph_grad_id})"',
                        tag,
                        flags=re.I,
                    )
                    tag = re.sub(
                        r'fill:(?:#fff|#ffffff|#fffff9|#fcfcfc|#f5f5f5|#f0f0f0|#dedede|#eee|#d0d0d0|#bebebe)',
                        f'fill:url(#{glyph_grad_id})',
                        tag,
                        flags=re.I,
                    )
                    if f'url(#{glyph_grad_id})' in tag and 'fill="#363636"' in tag:
                        tag = tag.replace('fill="#363636"', '')
                    tag = re.sub(
                        r'\bstroke="(?:#fff|#ffffff|#dedede)"',
                        f'stroke="url(#{glyph_grad_id})"',
                        tag,
                        flags=re.I,
                    )
                    return tag

                text = sub_outside_defs(r"<[^>]+>", recolor_glyph, text)

        defs = build_frost_defs(prefix, scale, mode=self.mode, dark_glyph_gradient=dark_glyph_gradient)
        defs_match = re.search(r"<defs>", text)
        if defs_match:
            text = text[:defs_match.end()] + defs + text[defs_match.end():]
        else:
            svg_match = re.search(r"<svg\b[^>]*>", text)
            if svg_match:
                text = text[:svg_match.end()] + "<defs>" + defs + "</defs>" + text[svg_match.end():]

        overlay = generate_tile_overlay(tile, prefix, scale)
        return text.replace(new_tile, new_tile + overlay, 1)


def frost_svg(
    text: str,
    mode: str = "clear",
    fallback: bool = False,
    icon_name: str = "",
) -> Optional[str]:
    """Convenience function to transform an SVG string into frosted glass."""
    engine = FrostEngine(mode=mode)
    return engine.transform(text, fallback=fallback, icon_name=icon_name)
