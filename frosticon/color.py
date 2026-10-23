"""Color space conversion and palette desaturation utilities for SVG icons."""

import colorsys
import re
from typing import Optional, Tuple
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
