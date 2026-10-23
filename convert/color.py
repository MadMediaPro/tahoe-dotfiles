"""Color space conversion and palette desaturation utilities for SVG icons."""

import colorsys
import re
from typing import List, Optional, Tuple
from .constants import NAMED_COLORS


def hex_to_rgb(value: str) -> Optional[Tuple[int, int, int]]:
    """Convert hex string (#RGB, #RRGGBB) to (R, G, B) tuple in 0..255."""
    clean = value.lstrip("#")
    if len(clean) == 3:
        clean = "".join(ch * 2 for ch in clean)
    if len(clean) != 6:
        return None
    try:
        return tuple(int(clean[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]
    except ValueError:
        return None


def is_vivid_color(r: float, g: float, b: float) -> bool:
    """Check if color has non-trivial saturation and is not near black or white."""
    _, lightness, saturation = colorsys.rgb_to_hls(r, g, b)
    return saturation > 0.18 and 0.12 < lightness < 0.90


def is_hex_vivid(hex_val: str) -> bool:
    """Check if a hex color string is vivid."""
    rgb = hex_to_rgb(hex_val)
    if not rgb:
        return False
    return is_vivid_color(*(c / 255.0 for c in rgb))


def extract_gradient_stops(defs_text: str, gradient_id: str) -> List[str]:
    """Extract stop colors from a linearGradient in defs, following xlink:href references."""
    pattern = rf'<linearGradient\b[^>]*\bid=[\"\']{re.escape(gradient_id)}[\"\'][^>]*>(.*?)</linearGradient>'
    match = re.search(pattern, defs_text, re.S)
    if not match:
        m_self = re.search(rf'<linearGradient\b[^>]*\bid=[\"\']{re.escape(gradient_id)}[\"\'][^>]*/>', defs_text, re.S)
        if m_self:
            href_m = re.search(r'(?:xlink:)?href=[\"\']#([^\"\']+)[\"\']', m_self.group(0))
            if href_m:
                return extract_gradient_stops(defs_text, href_m.group(1))
        return []

    body = match.group(1)
    stop_tags = re.findall(r'<stop\b[^>]*?/?>', body)
    colors = []
    for tag in stop_tags:
        sm = re.search(r'stop-color\s*:\s*(#[0-9a-fA-F]{3,6})', tag)
        if sm:
            colors.append(sm.group(1))
            continue
        am = re.search(r'stop-color=[\"\'](#[0-9a-fA-F]{3,6})[\"\']', tag)
        if am:
            colors.append(am.group(1))

    if not colors:
        href_m = re.search(r'(?:xlink:)?href=[\"\']#([^\"\']+)[\"\']', match.group(0))
        if href_m:
            return extract_gradient_stops(defs_text, href_m.group(1))
    return colors


def extract_tile_colors(svg_text: str, tile_tag: str) -> List[str]:
    """Extract vivid colors from a squircle tile tag (either from gradient or fill attribute)."""
    defs_m = re.search(r'<defs\b[^>]*>(.*?)</defs>', svg_text, re.S)
    defs_text = defs_m.group(1) if defs_m else ""

    # Check for gradient fill url(#...)
    m = re.search(r'(?:fill=[\"\']url\(#([^\"\'\)]+)\)[\"\']|fill:url\(#([^\"\'\);]+)\))', tile_tag)
    if m:
        gid = m.group(1) or m.group(2)
        stops = extract_gradient_stops(defs_text, gid)
        vivid = [s for s in stops if is_hex_vivid(s)]
        if vivid:
            return vivid

    # Check for direct hex fill attribute
    hex_m = re.search(r'(?:fill=[\"\'](#[0-9a-fA-F]{3,6})[\"\']|fill:(#[0-9a-fA-F]{3,6}))', tile_tag)
    if hex_m:
        h = hex_m.group(1) or hex_m.group(2)
        if is_hex_vivid(h):
            return [h]

    return []


def foreground_has_vivid_colors(svg_text: str, tile_tag: str) -> bool:
    """Determine whether the visible foreground elements already contain vivid colors."""
    outside = re.sub(r'<defs\b.*?</defs>', '', svg_text, flags=re.S)
    outside = outside.replace(tile_tag, '', 1)
    # Strip common squircle rim overlays
    outside = re.sub(r'<path\b[^>]*\bd=\"M(?:9 2C5\.122|18 4C10\.244|17 4\.6)[^\"]*\"[^>]*?/>', '', outside)
    hexes = re.findall(r'#[0-9a-fA-F]{3,6}\b', outside)
    return any(is_hex_vivid(h) for h in hexes)


def lighten_color(r: float, g: float, b: float) -> str:
    """Calculate relative luminance and map to a pearl-white/silver tone."""
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    tone = 176 + round(min(1.0, max(0.0, (lum - 0.20) / 0.80)) * 79)
    return f"#{tone:02x}{tone:02x}{tone:02x}"


def recolor_svg(body: str) -> str:
    """Desaturate and lighten icon colors to create a monochrome 'clear' glass look.

    Dark outlines/shadows are preserved when appropriate unless the overall icon
    is predominantly dark, in which case dark values are inverted.
    """
    # Exclude defs from color frequency analysis
    visible = re.sub(r"<defs>.*?</defs>", "", body, flags=re.S)
    dark = 0
    light = 0

    for value in re.findall(r"#[0-9a-fA-F]{3,6}\b", visible):
        rgb = hex_to_rgb(value)
        if rgb is None:
            continue
        r, g, b = (v / 255.0 for v in rgb)
        _, lightness, saturation = colorsys.rgb_to_hls(r, g, b)
        if saturation <= 0.12:
            if lightness < 0.35:
                dark += 1
            elif lightness > 0.75:
                light += 1

    invert_dark = dark > 0 and dark > light

    # Replace named colors
    def named_repl(match: re.Match) -> str:
        attr, name = match.group(1), match.group(2)
        r, g, b = (val / 255.0 for val in NAMED_COLORS[name])
        return f'{attr}="{lighten_color(r, g, b)}"'

    body = re.sub(
        r'(stop-color|fill|stroke)="(' + "|".join(NAMED_COLORS) + r')"',
        named_repl,
        body,
    )

    # Replace hex colors
    def hex_repl(match: re.Match) -> str:
        value = match.group(0)
        rgb = hex_to_rgb(value)
        if rgb is None:
            return value

        r, g, b = (v / 255.0 for v in rgb)
        _, _, saturation = colorsys.rgb_to_hls(r, g, b)
        lum = 0.2126 * r + 0.7152 * g + 0.0722 * b

        context = body[max(0, match.start() - 24):match.start()]
        if 'stop-color="' in context or "stop-color:" in context:
            return lighten_color(r, g, b)

        # Preserve subtle dark accents if not in inverted mode
        if saturation <= 0.20 and lum < 0.35 and not invert_dark:
            return value

        return lighten_color(r, g, b)

    return re.sub(r"#[0-9a-fA-F]{3,6}\b", hex_repl, body)
